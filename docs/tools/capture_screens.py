"""발표자료용 서비스 화면 캡처 (Playwright).

    .venv/Scripts/python docs/tools/capture_screens.py [BASE_URL] [SHOWTIME_ID]

- BASE_URL 기본값: http://127.0.0.1:5175 (VITE_API_URL=https://movpick-api.onrender.com 로 띄운 dev 서버)
- 감시 등록 토스트 / 취소표 팝업은 API·WebSocket 응답을 브라우저에서 모킹하여 운영 DB 에 쓰기를 하지 않는다.
- 결과: docs/tools/screens/*.png
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5175").rstrip("/")
SHOWTIME = int(sys.argv[2]) if len(sys.argv) > 2 else 114
API = "https://movpick-api.onrender.com"
OUT = Path(__file__).resolve().parent / "screens"
OUT.mkdir(exist_ok=True)


def shot(target, name: str, **kw) -> None:
    target.screenshot(path=str(OUT / f"{name}.png"), **kw)
    print("saved", name)


def desktop(b) -> None:
    sockets = []
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, locale="ko-KR")
    pg = ctx.new_page()

    def on_ws(ws):
        sockets.append(ws)
        ws.on_message(lambda m: ws.send(json.dumps({"type": "pong"})) if '"ping"' in str(m) else None)
        ws.send(json.dumps({"type": "hello", "user_id": 1, "crawler_running": False}))

    pg.route_web_socket("**/ws**", on_ws)

    pg.goto(f"{BASE}/login", wait_until="networkidle")
    pg.locator("h2.title-ko").wait_for(timeout=90000)
    pg.wait_for_timeout(1800)
    shot(pg, "login")

    pg.get_by_role("tab", name="회원가입").click()
    pg.get_by_placeholder("비밀번호", exact=True).fill("Movpick2026")
    pg.wait_for_timeout(400)
    shot(pg.locator("section").nth(1), "signup_rules")
    pg.get_by_role("tab", name="로그인").click()

    pg.get_by_role("button", name="일반 회원 테스트 로그인").click()
    pg.wait_for_url(f"{BASE}/", timeout=30000)
    pg.locator("article").first.wait_for(timeout=60000)
    pg.wait_for_timeout(1800)
    shot(pg, "home")

    pg.goto(f"{BASE}/showtimes/{SHOWTIME}", wait_until="networkidle")
    pg.get_by_text("SCREEN").wait_for(timeout=60000)
    pg.wait_for_timeout(1200)
    shot(pg, "seat", full_page=True)
    pg.get_by_role("button", name="명당 히트맵").click()
    pg.wait_for_timeout(500)
    shot(pg.locator("section.card").first, "heatmap")
    pg.get_by_role("button", name="명당 히트맵").click()

    pg.route("**/api/watches", lambda r: r.fulfill(json={"watch": {}, "available_now": []})
             if r.request.method == "POST" else r.continue_())
    pg.get_by_role("button", name="명당 자리 전체 감시").click()
    pg.get_by_text("명당 자리 잔여석 감시를 시작했습니다.").wait_for(timeout=10000)
    pg.wait_for_timeout(500)
    shot(pg, "watch")

    info = pg.evaluate("async ([api, id]) => (await fetch(`${api}/api/showtimes/${id}/seats`)).json()", [API, SHOWTIME])
    st = info["showtime"]
    alert = {"type": "seat_alert", "watch_id": 1, "showtime_id": SHOWTIME, "movie_title": st["movie_title"],
             "theater": st["theater"], "screen": st["screen"], "start_at": st["start_at"],
             "seats": (info.get("recommended") or ["G10", "G11"])[:3], "booking_url": st["booking_url"]}
    pg.wait_for_timeout(4500)
    for ws in sockets:
        ws.send(json.dumps(alert))
    pg.get_by_text("명당 자리가 비었어요!").wait_for(timeout=10000)
    pg.wait_for_timeout(700)
    shot(pg, "popup")
    pg.get_by_role("alertdialog").get_by_label("닫기").click()

    pg.goto(f"{BASE}/", wait_until="networkidle")
    pg.locator("article").first.wait_for(timeout=60000)
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    pg.wait_for_timeout(900)
    shot(pg, "footer")

    pg.evaluate("localStorage.clear()")
    pg.goto(f"{BASE}/login", wait_until="networkidle")
    pg.get_by_role("button", name="시스템 관리자 테스트 로그인").click()
    pg.wait_for_url("**/admin", timeout=30000)
    pg.locator("iframe[title='crawl report']").wait_for(timeout=60000)
    pg.wait_for_timeout(3500)
    shot(pg, "admin")
    pg.get_by_role("tab", name="회원 권한").click()
    pg.wait_for_timeout(1500)
    shot(pg, "admin_users")
    ctx.close()


def mobile(b) -> None:
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                        has_touch=True, locale="ko-KR")
    pg = ctx.new_page()
    pg.goto(f"{BASE}/login", wait_until="networkidle")
    pg.locator("h2.title-ko").wait_for(timeout=90000)
    pg.wait_for_timeout(1500)
    shot(pg, "m_login")
    pg.goto(f"{BASE}/", wait_until="networkidle")
    pg.locator("article").first.wait_for(timeout=60000)
    pg.wait_for_timeout(800)
    shot(pg, "m_home")
    pg.get_by_label("메뉴 열기").click()
    pg.wait_for_timeout(600)
    shot(pg, "m_drawer")
    pg.get_by_label("메뉴 닫기").click()
    pg.goto(f"{BASE}/showtimes/{SHOWTIME}", wait_until="networkidle")
    pg.get_by_text("SCREEN").wait_for(timeout=60000)
    pg.evaluate("window.scrollTo(0, 180)")
    pg.wait_for_timeout(800)
    shot(pg, "m_seat")
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    desktop(browser)
    mobile(browser)
    browser.close()
