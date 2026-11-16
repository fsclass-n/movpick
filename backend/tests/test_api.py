import random
from dataclasses import replace
from datetime import date, timedelta

import pytest

from backend.app.db import SessionLocal
from backend.app.models import Showtime
from backend.app.security import validate_password
from backend.app.services import monitor
from backend.app.services.crawler import persist
from rpa import seatmap
from rpa.service import crawl_chain

from .conftest import auth


@pytest.mark.parametrize("pw,ok", [
    ("Movpick!2026", True), ("short1!A", True), ("alllower1!", False), ("NoSpecial12", False),
    ("NoDigits!!a", False), ("Ab1!", False), ("ALLUPPER1!", False), ("Has Space1!", False),
])
def test_password_rule(pw, ok):
    assert validate_password(pw) is ok


@pytest.mark.parametrize("total,avail", [(36, 36), (172, 152), (306, 4), (96, 0)])
def test_seat_layout_matches_counts(total, avail):
    layout = seatmap.build_layout(total, avail, "seed")
    assert seatmap.capacity(layout) == total
    assert seatmap.available_count(layout) == avail
    assert set(layout["prime"]) <= set(layout["scores"])
    fixed = seatmap.reconcile(layout, max(0, avail - 3), "seed2")
    assert seatmap.available_count(fixed) == max(0, avail - 3)


def test_signup_login_flow(client):
    weak = client.post("/api/auth/signup", json={"email": "a@b.co", "name": "A", "password": "weakpass"})
    assert weak.status_code == 422
    body = {"email": "Tester@movpick.app", "name": "테스터", "password": "Strong!234"}
    assert client.post("/api/auth/signup", json=body).status_code == 201
    assert client.post("/api/auth/signup", json=body).status_code == 409
    bad = client.post("/api/auth/login", json={"email": body["email"], "password": "Wrong!2345"})
    assert bad.status_code == 401
    res = client.post("/api/auth/login", json={"email": "tester@movpick.app", "password": body["password"]})
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {res.json()['access_token']}"})
    assert me.json()["email"] == "tester@movpick.app" and me.json()["role"] == "user"


def test_demo_login_and_admin_guard(client):
    user_h, admin_h = auth(client, "user"), auth(client, "admin")
    assert client.get("/api/auth/me", headers=admin_h).json()["role"] == "admin"
    assert client.get("/api/admin/users", headers=user_h).status_code == 403
    assert client.get("/api/admin/users").status_code == 401
    assert client.get("/api/admin/users", headers=admin_h).status_code == 200


def test_demo_admin_is_read_only(client):
    demo_h, root_h = auth(client, "admin"), auth(client, "root")
    assert client.get("/api/auth/me", headers=demo_h).json()["read_only"] is True
    assert client.get("/api/auth/me", headers=root_h).json()["read_only"] is False
    for path in ("/api/admin/users", "/api/admin/crawler", "/api/admin/crawler/logs", "/api/admin/summary"):
        assert client.get(path, headers=demo_h).status_code == 200, path
    users = client.get("/api/admin/users", headers=demo_h).json()
    target = next(u for u in users if u["email"] == "user@movpick.app")
    writes = [
        client.patch(f"/api/admin/users/{target['id']}/role", json={"role": "admin"}, headers=demo_h),
        client.put("/api/admin/crawler/config", json={"interval_minutes": 15, "enabled": True}, headers=demo_h),
        client.post("/api/admin/crawler/run", headers=demo_h),
    ]
    assert all(r.status_code == 403 and "읽기 전용" in r.json()["detail"] for r in writes)
    root = next(u for u in users if u["email"] == "root@movpick.app")
    assert root["role"] == "admin"
    res = client.patch(f"/api/admin/users/{root['id']}/role", json={"role": "user"}, headers=root_h)
    assert res.status_code == 400  # 본인 + 환경 변수 관리자 보호


def test_env_admin_rejects_weak_password(monkeypatch):
    from backend.app.routers import auth as auth_mod
    monkeypatch.setattr(auth_mod, "settings", replace(auth_mod.settings, admin_email="weak@movpick.app", admin_password="weak"))
    with SessionLocal() as db:
        assert auth_mod.ensure_env_admin(db) is None
    monkeypatch.setattr(auth_mod, "settings", replace(auth_mod.settings, admin_email="user@movpick.app", admin_password="Strong!2345"))
    with SessionLocal() as db:
        assert auth_mod.ensure_env_admin(db) is None  # 테스트 계정 이메일 사용 불가


def test_role_change(client):
    admin_h = auth(client, "root")
    users = client.get("/api/admin/users", headers=admin_h).json()
    target = next(u for u in users if u["email"] == "tester@movpick.app")
    res = client.patch(f"/api/admin/users/{target['id']}/role", json={"role": "admin"}, headers=admin_h)
    assert res.json()["role"] == "admin"
    res = client.patch(f"/api/admin/users/{target['id']}/role", json={"role": "user"}, headers=admin_h)
    assert res.json()["role"] == "user"
    demo = next(u for u in users if u["email"] == "admin@movpick.app")
    res = client.patch(f"/api/admin/users/{demo['id']}/role", json={"role": "user"}, headers=admin_h)
    assert res.json()["role"] == "user"
    client.patch(f"/api/admin/users/{demo['id']}/role", json={"role": "admin"}, headers=admin_h)


def test_showtimes_seats_watch_and_alert(client, monkeypatch):
    day = date.today() + timedelta(days=1)
    persist(crawl_chain("megabox", day, "mock"), "test")
    shows = client.get("/api/showtimes", params={"date": day.isoformat()}).json()
    assert shows and all(s["source"] == "mock" for s in shows)
    assert client.get("/api/movies", params={"date": day.isoformat()}).json()[0]["booking_rate"] >= 0

    sid = shows[0]["id"]
    seats = client.get(f"/api/showtimes/{sid}/seats").json()
    assert set(seats["prime_free"]) <= set(seats["prime"])

    with SessionLocal() as db:  # 명당 자리를 전부 점유 상태로 만든 뒤 감시 등록
        st = db.get(Showtime, sid)
        st.seat_layout = {**st.seat_layout, "taken": sorted(set(st.seat_layout["taken"]) | set(st.seat_layout["prime"]))}
        db.commit()
        prime = st.seat_layout["prime"]

    h = auth(client, "user")
    res = client.post("/api/watches", json={"showtime_id": sid, "mode": "prime"}, headers=h)
    assert res.status_code == 201 and res.json()["available_now"] == []

    with SessionLocal() as db:  # 취소표 발생
        st = db.get(Showtime, sid)
        st.seat_layout = {**st.seat_layout, "taken": [s for s in st.seat_layout["taken"] if s != prime[0]]}
        db.commit()

    monkeypatch.setattr(monitor, "settings", replace(monitor.settings, seat_simulation=False))
    _, alerts = monitor._tick(random.Random(0))
    mine = [a for a in alerts if a[2].id == sid]
    assert mine and prime[0] in mine[0][3]
    assert any(w["showtime_id"] == sid for w in client.get("/api/watches", headers=h).json())


def test_stats_and_ws(client):
    stats = client.get("/api/stats/booking-rates").json()
    assert "movies" in stats and "top" in stats
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "hello"
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_persist_dedupes_duplicate_items():
    r = crawl_chain("lotte", date.today() + timedelta(days=2), "mock")
    unique = len(r.items)
    r.items = r.items + r.items[:3]
    assert persist(r, "test") == unique


def _count(chain, day, source):
    from sqlalchemy import func, select
    from backend.app.services.crawler import day_window
    start, end = day_window(day)
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(Showtime).where(
            Showtime.chain == chain, Showtime.source == source, Showtime.start_at >= start, Showtime.start_at < end))


def test_remote_ingest_replaces_mock(client, monkeypatch):
    from backend.app.routers import rpa as rpa_router
    day = date.today() + timedelta(days=3)
    persist(crawl_chain("cgv", day, "mock"), "test")
    assert _count("cgv", day, "mock") > 0

    item = {"external_id": "0056-x-1", "theater": "CGV 강남", "screen": "1관", "movie_title": "원격 수집 테스트",
            "start_at": f"{day.isoformat()}T20:00:00", "total_seats": 120, "available_seats": 30}
    body = {"chain": "cgv", "date": day.isoformat(), "items": [item], "collector": "pytest"}
    assert client.post("/api/rpa/ingest", json=body).status_code == 404  # 토큰 미설정 → 비활성

    monkeypatch.setattr(rpa_router, "settings", replace(rpa_router.settings, rpa_ingest_token="secret-token"))
    assert client.post("/api/rpa/ingest", json=body, headers={"X-RPA-Token": "wrong"}).status_code == 401
    res = client.post("/api/rpa/ingest", json=body, headers={"X-RPA-Token": "secret-token"})
    assert res.status_code == 200 and res.json()["saved"] == 1
    assert _count("cgv", day, "real") == 1 and _count("cgv", day, "mock") == 0


def test_crawler_keeps_fresh_real_data(monkeypatch):
    import asyncio
    from backend.app.services import crawler as crawler_mod
    day = date.today() + timedelta(days=4)
    real = crawl_chain("lotte", day, "mock")
    real.source, real.day = "real", day
    persist(real, "test")
    n_real = _count("lotte", day, "real")

    def failing(chain, d, *a, **kw):  # 실제 수집 실패 → 모의 데이터 폴백 상황 재현
        r = crawl_chain(chain, d, "mock")
        r.error, r.ok = "CrawlError: HTTP 403", False
        return r
    monkeypatch.setattr(crawler_mod, "crawl_chain", failing)
    out = asyncio.run(crawler_mod.crawler._crawl_one("lotte", day, "test"))
    assert out["ok"] is False and "기존 실데이터 유지" in out["message"]
    assert _count("lotte", day, "real") == n_real and _count("lotte", day, "mock") == 0

    monkeypatch.setattr(crawler_mod, "settings", replace(crawler_mod.settings, rpa_real_ttl_minutes=0))
    out = asyncio.run(crawler_mod.crawler._crawl_one("lotte", day, "test"))  # TTL 초과(stale)여도 섞지 않음
    assert "갱신 지연" in out["message"] and _count("lotte", day, "mock") == 0

    monkeypatch.setattr(crawler_mod, "settings", replace(crawler_mod.settings, rpa_remote_chains=["lotte"]))
    assert asyncio.run(crawler_mod.crawler._crawl_one("lotte", day, "test"))["source"] == "remote"
    other = day + timedelta(days=1)  # 원격 데이터가 없는 날짜 → 모의 데이터로 대체
    out = asyncio.run(crawler_mod.crawler._crawl_one("lotte", other, "test"))
    assert out["source"] == "mock" and out["ok"] is False and _count("lotte", other, "mock") > 0
