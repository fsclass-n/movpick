"""movpick.onrender.com 시연 자동 녹화 (Playwright, 1920x1080).

    .venv/Scripts/python docs/video/tools/record_demo.py [main|ext|compare|all]

- 화면은 Chrome DevTools 스크린캐스트(CDP)로 프레임마다 타임스탬프와 함께 저장 → 장면 표시와 같은 시계로 정확히 자름
  (Playwright 기본 녹화는 실제 시간과 영상 시간이 어긋나 장면 경계가 밀림)
- 일반 회원 → 관리자(읽기 전용) 흐름을 한 페이지에서 앱 내부 이동으로 녹화 (전체 새로고침 없음 → 흰 화면 번쩍임 없음)
- 외부 페이지(/docs, /health, GitHub Actions)는 따로 녹화하고, 로딩이 끝난 뒤를 장면 시작으로 기록
- 네트워크 대기(수집 진단, 실시간 알림 대기)는 marks 의 cuts 로 기록해 편집에서 잘라 냄
- 노란 원형 커서·클릭 링·시안 테두리 강조는 페이지 위에 덧씌운 요소 (화면 전체 딤 없음)
- 시연 중 데이터 변경: 일반 회원 감시 1건 등록 → 시연 후 삭제. 관리자 쓰기는 읽기 전용 계정이라 서버가 403 으로 거부
"""

import base64
import json
import shutil
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

from common import BUILD, save_json
from video_scenes import SCENES, SHOWTIME_ID

SITE = "https://movpick.onrender.com"
API = "https://movpick-api.onrender.com"
DUR = {s["id"]: s["dur"] for s in SCENES}
REC = BUILD / "rec"

OVERLAY_JS = r"""
(() => {
  const css = `
    #__cur{position:fixed;left:-100px;top:-100px;width:38px;height:38px;margin:-19px 0 0 -19px;border-radius:50%;
      background:rgba(245,197,24,.28);border:2px solid rgba(245,197,24,.95);box-shadow:0 0 10px rgba(245,197,24,.35);
      pointer-events:none;z-index:2147483647}
    .__ring{position:fixed;width:38px;height:38px;margin:-19px 0 0 -19px;border-radius:50%;border:3px solid #F5C518;
      pointer-events:none;z-index:2147483647;animation:__ring .6s ease-out forwards}
    @keyframes __ring{from{transform:scale(.6);opacity:1}to{transform:scale(2.3);opacity:0}}
    .__hl{position:fixed;border:3px solid #22d3ee;border-radius:14px;box-shadow:0 0 16px rgba(34,211,238,.45);
      pointer-events:none;z-index:2147483646;opacity:0;transition:opacity .3s ease}
    main{min-height:100vh}
    ::-webkit-scrollbar{width:0;height:0}`;
  const boot = () => {
    if (document.getElementById('__cur')) return;
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    const cur = document.createElement('div'); cur.id = '__cur'; document.body.appendChild(cur);
    addEventListener('mousemove', e => { cur.style.left = e.clientX + 'px'; cur.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', e => {
      const r = document.createElement('div'); r.className = '__ring';
      r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
      document.body.appendChild(r); setTimeout(() => r.remove(), 700);
    }, true);
    window.__hl = (x, y, w, h, ms) => {
      const d = document.createElement('div'); d.className = '__hl';
      Object.assign(d.style, {left: x + 'px', top: y + 'px', width: w + 'px', height: h + 'px'});
      document.body.appendChild(d); requestAnimationFrame(() => d.style.opacity = 1);
      setTimeout(() => { d.style.opacity = 0; setTimeout(() => d.remove(), 350); }, ms);
    };
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', boot); else boot();
})();
"""


class Recorder:
    def __init__(self, page, ctx, name):
        self.page, self.name = page, name
        self.dir = REC / name
        shutil.rmtree(self.dir, ignore_errors=True)
        (self.dir / "frames").mkdir(parents=True)
        self.frames = []
        self.t0 = time.time()
        self.marks, self.cur = {}, None
        self.mx, self.my = 960, 700
        self.cdp = ctx.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._on_frame)
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 88, "maxWidth": 1920, "maxHeight": 1080})

    def _on_frame(self, params) -> None:
        self.cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        name = f"frames/{len(self.frames):06d}.jpg"
        (self.dir / name).write_bytes(base64.b64decode(params["data"]))
        self.frames.append([round(params["metadata"]["timestamp"] - self.t0, 4), name])

    def stop(self) -> None:
        self.wait(0.5)
        self.cdp.send("Page.stopScreencast")

    def now(self) -> float:
        return time.time() - self.t0

    def wait(self, sec: float) -> None:
        self.page.wait_for_timeout(int(sec * 1000))

    # ---------------------------------------------------------- scene timing
    def begin(self, sid: str) -> None:
        self.cur = sid
        self.marks[sid] = {"start": round(self.now(), 3), "cuts": []}
        print(f"  ▶ {sid} @ {self.marks[sid]['start']:.1f}s")

    def effective(self) -> float:
        m = self.marks[self.cur]
        return self.now() - m["start"] - sum(b - a for a, b in m["cuts"])

    def end(self) -> None:
        remain = DUR[self.cur] + 0.25 - self.effective()
        if remain > 0:
            self.wait(remain)
        self.marks[self.cur]["end"] = round(self.now(), 3)

    def cut_wait(self, fn, keep_before=0.7, keep_after=0.5):
        """fn 이 끝날 때까지 기다리고, 그 사이 대기 구간은 편집에서 잘라 내도록 기록."""
        a = self.now() + keep_before
        result = fn()
        b = self.now() - keep_after
        if b > a:
            self.marks[self.cur]["cuts"].append([round(a, 3), round(b, 3)])
        return result

    # ---------------------------------------------------------- cursor / emphasis
    def glide(self, x: float, y: float, ms: int = 700) -> None:
        """시간 기준 이동: 호출 오버헤드와 무관하게 항상 ms 동안 부드럽게 이동."""
        sx, sy, t0 = self.mx, self.my, time.monotonic()
        while True:
            t = min(1.0, (time.monotonic() - t0) * 1000 / ms)
            e = t * t * (3 - 2 * t)
            self.page.mouse.move(sx + (x - sx) * e, sy + (y - sy) * e)
            if t >= 1.0:
                break
        self.mx, self.my = x, y

    def center(self, loc):
        loc.scroll_into_view_if_needed()
        b = loc.bounding_box()
        return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

    def point(self, loc, pause: float = 0.8, rest_offset=None) -> None:
        x, y = self.center(loc)
        self.glide(x, y)
        self.wait(pause)
        if rest_offset:  # 말하는 동안 글자를 가리지 않도록 오른쪽 아래 여백으로 이동
            self.glide(x + rest_offset[0], y + rest_offset[1], 450)

    def click(self, loc, pause: float = 0.9) -> None:
        x, y = self.center(loc)
        self.glide(x, y)
        self.wait(pause)
        self.page.mouse.click(x, y)
        self.wait(0.5)

    def type(self, loc, text: str, delay: int = 120) -> None:
        self.click(loc, 0.5)
        loc.press_sequentially(text, delay=delay)

    def hl(self, loc, ms: int = 2600, pad: int = 8) -> None:
        loc.scroll_into_view_if_needed()
        b = loc.bounding_box()
        self.page.evaluate("([x,y,w,h,ms]) => window.__hl(x,y,w,h,ms)",
                           [b["x"] - pad, b["y"] - pad, b["width"] + pad * 2, b["height"] + pad * 2, ms])

    def soft(self, fn, *args, **kw) -> None:
        """보조 연출(토스트 강조 등)은 요소가 이미 사라졌으면 건너뛴다."""
        try:
            args[0].wait_for(state="visible", timeout=2500)
            fn(*args, **kw)
        except Exception:  # noqa: BLE001
            print("    (skip optional emphasis)")

    def scroll(self, dy: int) -> None:
        self.page.evaluate("dy => window.scrollBy({top: dy, behavior: 'smooth'})", dy)
        self.wait(0.9)


def new_context(browser, name):
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ko-KR",
                              permissions=["notifications"], color_scheme="dark")
    ctx.add_init_script(OVERLAY_JS)
    return ctx


def finish(ctx, page, rec, name):
    rec.stop()
    ctx.close()
    save_json(REC / f"{name}.json", {"dir": str(rec.dir), "frames": rec.frames, "scenes": rec.marks})
    print(f"  saved {name}: {len(rec.frames)} frames")


def clear_demo_watches():
    """테스트 일반 회원의 남은 감시를 정리 (이전 녹화 중단 시 잔여분)."""
    req = urllib.request.Request(f"{API}/api/auth/demo/user", method="POST")
    token = json.load(urllib.request.urlopen(req, timeout=90))["access_token"]
    hdr = {"Authorization": f"Bearer {token}"}
    watches = json.load(urllib.request.urlopen(urllib.request.Request(f"{API}/api/watches", headers=hdr), timeout=60))
    for w in watches:
        urllib.request.urlopen(urllib.request.Request(f"{API}/api/watches/{w['id']}", headers=hdr, method="DELETE"), timeout=60)
    print(f"  cleared {len(watches)} leftover watch(es)")


def warm_up():
    for url in (f"{API}/health", f"{SITE}/", f"{API}/api/stats/booking-rates"):
        for _ in range(3):
            try:
                urllib.request.urlopen(url, timeout=90).read()
                break
            except Exception:  # noqa: BLE001
                time.sleep(5)


# ====================================================================== main flow (일반 회원 → 관리자)
def record_main(browser):
    clear_demo_watches()
    st = json.load(urllib.request.urlopen(f"{API}/api/showtimes/{SHOWTIME_ID}"))
    chain_label = {"megabox": "메가박스", "lotte": "롯데시네마", "cgv": "CGV"}[st["chain"]]
    keyword = st["movie_title"].split()[0]
    ctx = new_context(browser, "main")
    page = ctx.new_page()
    state = {"suppress": False, "alerts": 0}

    def proxy(ws):  # 실제 서버 WebSocket 을 그대로 중계. 첫 알림을 보여 준 뒤 이어지는 중복 팝업만 화면에서 생략
        server = ws.connect_to_server()

        def from_server(msg):
            if '"seat_alert"' in str(msg):
                state["alerts"] += 1
                if state["suppress"]:
                    return
            ws.send(msg)
        server.on_message(from_server)
        ws.on_message(lambda m: server.send(m))

    page.route_web_socket("**/ws**", proxy)
    r = Recorder(page, ctx, "main")
    page.goto(f"{SITE}/", wait_until="load", timeout=120000)
    page.locator("article").first.wait_for(timeout=90000)
    r.wait(1.5)

    # d00 홈(비로그인)
    r.begin("d00")
    r.glide(700, 260, 600)
    r.hl(page.locator("main section").first, 4200)
    r.wait(4.5)
    r.point(page.locator("article").first, 1.0, rest_offset=(260, 120))
    r.end()

    # d01 로그인 화면 → 회원가입 비밀번호 규칙
    r.begin("d01")
    r.click(page.locator("header").get_by_role("link", name="로그인"))
    r.cut_wait(lambda: page.locator("h2.title-ko").wait_for(timeout=90000))
    r.wait(0.8)
    r.hl(page.locator("main section").first, 3800)
    r.point(page.locator("h2.title-ko"), 2.6)
    r.click(page.get_by_role("tab", name="회원가입"))
    pw = page.get_by_placeholder("비밀번호", exact=True)
    r.type(pw, "Movpick", 150)
    r.wait(0.6)
    pw.press_sequentially("2026!", delay=260)
    r.hl(page.get_by_label("비밀번호 규칙"), 3200)
    r.wait(2.4)
    r.click(page.get_by_role("tab", name="로그인"), 0.6)
    r.end()

    # d02 일반 회원 테스트 로그인
    r.begin("d02")
    r.click(page.get_by_role("button", name="일반 회원 테스트 로그인"), 1.2)
    page.wait_for_url(f"{SITE}/", timeout=30000)
    r.cut_wait(lambda: page.locator("article").first.wait_for(timeout=90000))
    r.wait(1.0)
    r.soft(r.hl, page.locator("[role=status]").first, 2600)
    r.end()

    # d03 일반 회원 메뉴 → 영화관 필터 → 검색
    r.begin("d03")
    nav = page.locator("header nav").first
    r.hl(nav, 3000)
    r.point(nav, 2.6)
    filters = page.locator("main section").nth(1)
    r.click(filters.get_by_role("button", name=chain_label))
    r.wait(0.8)
    r.type(filters.get_by_placeholder("영화 · 극장 검색"), keyword, 160)
    r.wait(1.2)
    toggle = page.locator("article").first.locator("button[aria-expanded]")
    if toggle.get_attribute("aria-expanded") == "false":  # 카드 펼침 상태는 영화별로 유지되므로 필요 시 펼침
        r.click(toggle, 0.6)
        r.wait(0.6)
    r.hl(page.locator("article").first, 3200)
    r.point(page.locator("article").first, 1.5, rest_offset=(320, 160))
    r.end()

    # d04 좌석 맵 · 명당 · 히트맵 · 추천 · 추정 안내
    r.begin("d04")
    r.click(page.locator(f"a[href='/showtimes/{SHOWTIME_ID}']").first)
    r.cut_wait(lambda: page.get_by_text("SCREEN").wait_for(timeout=90000))
    r.wait(1.0)
    seat_card = page.locator("section.card").first
    r.hl(seat_card, 3000)
    r.point(page.locator("button[aria-label*='명당 자리']").first, 2.2)
    heat = page.get_by_role("button", name="명당 히트맵")
    r.click(heat)
    r.wait(3.2)
    r.click(heat, 0.5)
    rec_card = page.locator("aside .card").first
    r.hl(rec_card, 3200)
    r.point(rec_card.locator("button").first, 2.6)
    note = page.get_by_text("좌석 단위 배치는", exact=False)
    r.scroll(260)
    r.hl(note, 3000)
    r.wait(2.0)
    r.end()

    # d05 명당 자리 전체 감시 등록
    r.begin("d05")
    r.scroll(-260)
    r.click(page.get_by_role("button", name="명당 자리 전체 감시"), 1.0)
    page.get_by_text("명당 자리 잔여석 감시를 시작했습니다.").wait_for(timeout=30000)
    r.wait(0.4)
    r.soft(r.hl, page.locator("[role=status]").last, 3000)
    r.glide(1300, 760, 600)
    r.end()

    # d06 실시간 취소표 알림 (실제 WebSocket 알림, 대기 구간은 편집에서 제거)
    r.begin("d06")
    popup = page.get_by_text("명당 자리가 비었어요!")
    waited = r.now()
    popup.wait_for(timeout=420000)
    appeared = r.now()
    state["suppress"] = True
    r.marks["d06"]["start"] = round(max(waited, appeared - 2.5), 3)
    print(f"    real seat_alert after {appeared - waited:.0f}s")
    r.wait(1.0)
    dialog = page.get_by_role("alertdialog")
    r.hl(dialog, 4200)
    r.point(dialog.locator("span.font-mono").first, 3.0)
    r.soft(r.hl, page.locator("[role=status]").last, 3000)
    r.soft(r.point, page.locator("[role=status]").last, 3.0)
    r.wait(6.0)
    r.click(dialog.get_by_role("button", name="좌석 배치도"), 0.8)
    r.end()

    # d07 알림 설정 → 감시 삭제(정리)
    r.begin("d07")
    r.click(page.locator("header nav").get_by_role("link", name="알림 설정"))
    r.cut_wait(lambda: page.locator("main li.card").first.wait_for(timeout=60000))
    r.wait(0.8)
    item = page.locator("main li.card").first
    r.hl(item, 3000)
    r.point(item, 2.4)
    history = page.get_by_text("이번 세션 수신 알림")
    r.hl(page.locator("main section").last, 2600)
    r.point(history, 1.8)
    r.click(item.get_by_label("삭제"), 0.8)
    page.get_by_text("알림 설정을 삭제했습니다.").wait_for(timeout=15000)
    r.end()

    # d08 일반 회원 → /admin 직접 접근 차단
    r.begin("d08")
    r.hl(page.locator("header nav").first, 2600)
    r.point(page.locator("header nav").first, 2.6)
    r.wait(0.6)
    page.evaluate("() => { history.pushState({}, '', '/admin'); dispatchEvent(new PopStateEvent('popstate')); }")
    page.get_by_text("관리자 전용 화면입니다").wait_for(timeout=15000)
    r.wait(0.8)
    r.hl(page.get_by_role("alert"), 4200)
    r.point(page.get_by_text("관리자 전용 화면입니다"), 3.0, rest_offset=(240, 140))
    r.end()

    # d09 로그아웃
    r.begin("d09")
    r.click(page.locator("header").get_by_role("button", name="로그아웃"))
    r.cut_wait(lambda: page.locator("h2.title-ko").wait_for(timeout=90000))
    r.end()

    # d10 시스템 관리자(읽기 전용) 테스트 로그인
    r.begin("d10")
    r.click(page.get_by_role("button", name="시스템 관리자 테스트 로그인"), 1.0)
    page.wait_for_url("**/admin", timeout=30000)
    r.cut_wait(lambda: page.locator("main .grid").first.wait_for(timeout=90000))
    r.wait(1.0)
    r.hl(page.locator("header nav").first, 2600)
    r.point(page.locator("header nav").get_by_role("link", name="관리자"), 2.0)
    r.hl(page.get_by_role("note"), 3600)
    r.point(page.get_by_role("note"), 2.0, rest_offset=(300, 90))
    r.end()

    # d11 크롤러 대시보드
    r.begin("d11")
    cards = page.locator("main .grid").first
    r.hl(cards, 3200)
    r.point(cards, 2.8)
    status = page.locator("main .card", has_text="Playwright 크롤러 상태")
    r.hl(status.locator("dl"), 3600)
    r.point(status.locator("dl"), 3.4)
    r.cut_wait(lambda: page.locator("iframe[title='crawl report']").wait_for(timeout=90000))
    report = page.locator("main .card", has_text="크롤링 성능 리포트")
    r.hl(report, 4000)
    r.point(report, 3.4, rest_offset=(200, 160))
    r.end()

    # d12 수집 진단 (CGV 차단 / 메가박스 성공)
    r.begin("d12")
    probe = page.locator("div[class*='bg-surface-2/60']")
    r.scroll(120)
    r.hl(probe, 2600)
    r.click(probe.get_by_role("button", name="CGV"))
    r.cut_wait(lambda: page.get_by_text("CGV:", exact=False).wait_for(timeout=120000), 1.2, 0.6)
    r.wait(0.6)
    r.hl(probe, 3200)
    r.wait(2.6)
    r.click(probe.get_by_role("button", name="메가박스"))
    r.cut_wait(lambda: page.get_by_text("메가박스: 성공", exact=False).wait_for(timeout=120000), 1.2, 0.6)
    r.wait(0.4)
    r.hl(probe, 3200)
    r.end()

    # d13 읽기 전용: 실행 버튼 → 서버 403
    r.begin("d13")
    run_all = page.locator("button.btn-primary", has_text="전체")
    r.click(run_all, 1.2)
    page.get_by_text("읽기 전용입니다", exact=False).first.wait_for(timeout=15000)
    r.wait(0.4)
    r.soft(r.hl, page.locator("[role=status]").last, 3600)
    r.soft(r.point, page.locator("[role=status]").last, 3.0)
    r.end()

    # d14 회원 권한 탭: 권한 변경 시도 → 서버 403
    r.begin("d14")
    r.scroll(-400)
    r.click(page.get_by_role("tab", name="회원 권한"))
    page.get_by_placeholder("이름 · 이메일 검색").wait_for(timeout=15000)
    r.type(page.get_by_placeholder("이름 · 이메일 검색"), "movpick", 140)
    row = page.locator("main li", has_text="user@movpick.app").first
    r.cut_wait(lambda: (page.wait_for_timeout(600), row.wait_for(timeout=60000)))
    r.wait(0.8)
    r.hl(row, 3000)
    r.point(row, 1.6)
    r.click(row.get_by_role("radio", name="관리자"), 1.2)
    page.get_by_text("읽기 전용입니다", exact=False).first.wait_for(timeout=15000)
    r.wait(0.4)
    r.soft(r.hl, page.locator("[role=status]").last, 3600)
    r.soft(r.point, page.locator("[role=status]").last, 2.5)
    r.end()
    print(f"  seat_alert messages received: {state['alerts']}")
    finish(ctx, page, r, "main")


# ====================================================================== 외부 페이지
def record_external(browser):
    # d15 API 문서
    ctx = new_context(browser, "docs")
    page = ctx.new_page()
    r = Recorder(page, ctx, "docs")
    page.goto(f"{API}/docs", wait_until="load", timeout=120000)
    page.locator(".opblock-tag").first.wait_for(timeout=60000)
    r.wait(1.5)
    r.begin("d15")
    r.hl(page.locator(".info"), 2600)
    r.glide(900, 300, 600)
    r.wait(1.5)
    for tag in ("auth", "showtimes", "admin", "rpa"):
        loc = page.locator(f".opblock-tag[data-tag='{tag}']")
        loc.scroll_into_view_if_needed()
        r.page.evaluate("el => el.scrollIntoView({behavior:'smooth', block:'start'})", loc.element_handle())
        r.wait(1.0)
        r.hl(loc, 2400)
        r.point(loc, 1.2)
    r.end()
    finish(ctx, page, r, "docs")

    # d16 /health (JSON 을 읽기 좋게 들여쓰기만 적용, 값은 그대로)
    ctx = new_context(browser, "health")
    page = ctx.new_page()
    r = Recorder(page, ctx, "health")
    page.goto(f"{API}/health", wait_until="load", timeout=120000)
    page.evaluate("""() => {
      const data = JSON.parse(document.body.innerText);
      document.body.innerHTML = '';
      Object.assign(document.body.style, {margin: 0, background: '#0b0b12', color: '#ecebf5',
        font: '34px/1.5 Consolas, monospace', padding: '120px 160px'});
      const h = document.createElement('div'); h.textContent = 'GET https://movpick-api.onrender.com/health';
      Object.assign(h.style, {color: '#9a98b0', fontSize: '26px', marginBottom: '28px'});
      const pre = document.createElement('pre'); pre.id = 'json'; pre.textContent = JSON.stringify(data, null, 2);
      pre.style.margin = 0; document.body.append(h, pre);
    }""")
    page.evaluate(OVERLAY_JS)
    r.wait(1.0)
    r.begin("d16")
    r.glide(700, 330, 600)
    r.hl(page.locator("#json"), 3600)
    r.wait(4.0)
    r.end()
    finish(ctx, page, r, "health")

    # d17 GitHub Actions
    ctx = new_context(browser, "actions")
    page = ctx.new_page()
    r = Recorder(page, ctx, "actions")
    page.goto("https://github.com/fsclass-n/movpick/actions", wait_until="load", timeout=120000)
    page.get_by_text("CI / Deploy", exact=False).first.wait_for(timeout=60000)
    r.wait(1.5)
    r.begin("d17")
    runs = page.locator("[id^='check_suite_']").first
    target = runs if runs.count() else page.get_by_text("CI / Deploy", exact=False).nth(1)
    r.hl(target, 3600)
    r.point(target, 3.0, rest_offset=(360, 60))
    r.end()
    finish(ctx, page, r, "actions")


# ====================================================================== 계정 비교 카드 (정지 이미지)
COMPARE_HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
body{margin:0;width:1920px;height:1080px;background:radial-gradient(1200px 600px at 10% -10%,#ff3d5726,transparent 60%),#07070c;
 color:#ecebf5;font-family:'Malgun Gothic',sans-serif;display:flex;flex-direction:column;justify-content:center;padding:0 150px;box-sizing:border-box}
.k{color:#ff3d57;font-weight:700;letter-spacing:.3em;font-size:22px}
h1{font-size:60px;margin:14px 0 46px}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:30px;border:1px solid #2a2a3e;border-radius:22px;overflow:hidden}
th,td{padding:26px 30px;text-align:left;border-bottom:1px solid #2a2a3e}
th{background:#1a1a28;color:#f5c518;font-size:26px}
tr:last-child td{border-bottom:0} td:first-child{font-weight:700;width:300px}
.y{color:#34d399;font-weight:700}.n{color:#ff3d57;font-weight:700}.m{color:#9a98b0;font-size:24px}
</style></head><body>
<div class="k">ACCOUNT COMPARISON</div><h1>하나의 로그인, 역할에 따른 화면 · API 분리</h1>
<table><tr><th>기능</th><th>일반 회원</th><th>테스트 관리자</th><th>실제 관리자</th></tr>
<tr><td>상영작 · 좌석 맵 조회</td><td class="y">가능</td><td class="y">가능</td><td class="y">가능</td></tr>
<tr><td>명당 감시 · 실시간 알림</td><td class="y">가능</td><td class="y">가능</td><td class="y">가능</td></tr>
<tr><td>관리자 화면 접근</td><td class="n">차단 (관리자 전용 화면)</td><td class="y">조회만</td><td class="y">가능</td></tr>
<tr><td>크롤러 실행 · 설정 변경</td><td class="n">—</td><td class="n">서버 403 거부</td><td class="y">가능</td></tr>
<tr><td>회원 권한 변경</td><td class="n">—</td><td class="n">서버 403 거부</td><td class="y">가능 (본인·.env 관리자 보호)</td></tr>
<tr><td>계정 생성 방식</td><td class="m">가입 · 소셜 · 원클릭 테스트</td><td class="m">원클릭 테스트 로그인</td><td class="m">.env ADMIN_EMAIL / PASSWORD</td></tr>
</table></body></html>"""


def render_compare(browser):
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.set_content(COMPARE_HTML)
    page.wait_for_timeout(500)
    page.screenshot(path=str(BUILD / "overlays" / "compare.png"))
    page.close()
    print("  saved compare.png")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    warm_up()
    with sync_playwright() as p:
        b = p.chromium.launch()
        if what in ("compare", "all"):
            render_compare(b)
        if what in ("ext", "all"):
            record_external(b)
        if what in ("main", "all"):
            record_main(b)
        b.close()
