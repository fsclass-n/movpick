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


def test_role_change(client):
    admin_h = auth(client, "admin")
    users = client.get("/api/admin/users", headers=admin_h).json()
    target = next(u for u in users if u["email"] == "tester@movpick.app")
    res = client.patch(f"/api/admin/users/{target['id']}/role", json={"role": "admin"}, headers=admin_h)
    assert res.json()["role"] == "admin"
    res = client.patch(f"/api/admin/users/{target['id']}/role", json={"role": "user"}, headers=admin_h)
    assert res.json()["role"] == "user"
    me = client.get("/api/auth/me", headers=admin_h).json()
    assert client.patch(f"/api/admin/users/{me['id']}/role", json={"role": "user"}, headers=admin_h).status_code == 400


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
    assert "movies" in client.get("/api/stats/booking-rates").json()
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "hello"
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_persist_dedupes_duplicate_items():
    r = crawl_chain("lotte", date.today() + timedelta(days=2), "mock")
    unique = len(r.items)
    r.items = r.items + r.items[:3]
    assert persist(r, "test") == unique
