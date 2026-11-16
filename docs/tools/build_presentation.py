"""movpick 프로젝트 발표자료(16장) 생성기.

    .venv/Scripts/python -m pip install python-pptx==1.0.2 qrcode==8.0
    .venv/Scripts/python docs/tools/capture_screens.py      # 화면 캡처 (선택, docs/tools/screens)
    .venv/Scripts/python docs/tools/build_presentation.py   # → docs/프로젝트_발표자료.pptx

슬라이드 본문은 개조식, 발표자 스크립트와 면접관 어필 포인트는 각 슬라이드 '노트'에 들어간다.
"""

import tempfile
from pathlib import Path

import qrcode
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
SCREENS = Path(__file__).resolve().parent / "screens"
OUT = ROOT / "docs" / "프로젝트_발표자료.pptx"
TMP = Path(tempfile.mkdtemp())

INK, SURFACE, SURFACE2, LINE = "07070C", "11111A", "1A1A28", "2A2A3E"
FG, MUTED, ACCENT, GOLD, MINT, SKY = "ECEBF5", "9A98B0", "FF3D57", "F5C518", "34D399", "60A5FA"
FONT, MONO = "맑은 고딕", "Consolas"
TOTAL = 16

LINKS = {
    "service": "https://movpick.onrender.com",
    "github": "https://github.com/fsclass-n/movpick",
    "docs": "https://movpick-api.onrender.com/docs",
}


def rgb(h: str) -> RGBColor:
    return RGBColor.from_string(h)


# ----------------------------------------------------------------------------- primitives
def _font(run, size, color, bold=False, font=FONT, italic=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = rgb(color)
    run.font.name = font
    rpr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set("typeface", font)


def text(slide, x, y, w, h, paras, size=14, color=FG, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         font=FONT, spacing=1.15, gap=4):
    """paras: str | list[str | list[(text, {style})]]"""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    paras = [paras] if isinstance(paras, str) else paras
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(gap)
        runs = [(para, {})] if isinstance(para, str) else para
        for t, st in runs:
            r = p.add_run()
            r.text = t
            _font(r, st.get("size", size), st.get("color", color), st.get("bold", bold), st.get("font", font),
                  st.get("italic", False))
    return tb


def bullets(slide, x, y, w, h, items, size=14, marker_color=ACCENT, gap=7, color=FG):
    """items: str | (key, desc) | ("-", sub)"""
    paras = []
    for it in items:
        if isinstance(it, tuple) and it[0] == "-":
            paras.append([("    · ", {"color": MUTED, "size": size - 2}), (it[1], {"color": MUTED, "size": size - 2})])
        elif isinstance(it, tuple):
            paras.append([("▪ ", {"color": marker_color}), (it[0], {"bold": True}), ("  " + it[1], {"color": MUTED})])
        else:
            paras.append([("▪ ", {"color": marker_color}), (it, {})])
    return text(slide, x, y, w, h, paras, size=size, gap=gap, color=color)


def rect(slide, x, y, w, h, fill=SURFACE, line=LINE, radius=0.08, dash=False, width=1.0):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                 Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shp.adjustments[0] = radius
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(width)
        if dash:
            shp.line.dash_style = 7  # dash
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    shp.text_frame.text = ""
    return shp


def node(slide, x, y, w, h, title, sub="", fill=SURFACE2, line=LINE, tcolor=FG, size=13, dash=False, align=PP_ALIGN.CENTER):
    rect(slide, x, y, w, h, fill=fill, line=line, dash=dash)
    paras = [[(title, {"bold": True, "color": tcolor, "size": size})]]
    if sub:
        paras += [[(s, {"color": MUTED, "size": size - 3})] for s in sub.split("\n")]
    text(slide, x + 0.08, y + 0.05, w - 0.16, h - 0.1, paras, align=align, anchor=MSO_ANCHOR.MIDDLE, gap=1, spacing=1.05)


def arrow(slide, x1, y1, x2, y2, color=MUTED, dash=False, width=1.5, both=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(width)
    if dash:
        c.line.dash_style = 7
    ln = c.line._get_or_add_ln()
    for tag in (["a:headEnd"] if both else []) + ["a:tailEnd"]:
        el = ln.makeelement(qn(tag), {"type": "triangle", "w": "med", "len": "med"})
        ln.append(el)
    return c


def label(slide, x, y, w, t, color=MUTED, size=10, align=PP_ALIGN.CENTER):
    text(slide, x, y, w, 0.3, t, size=size, color=color, align=align)


def image(slide, name, x, y, w=None, h=None, border=LINE, crop=None):
    path = SCREENS / f"{name}.png"
    if not path.exists():
        rect(slide, x, y, w or 4, h or 2.5, fill=SURFACE2, line=LINE)
        label(slide, x, y + (h or 2.5) / 2 - 0.15, w or 4, f"[캡처: {name}]")
        return None
    kw = {"width": Inches(w)} if w else {"height": Inches(h)}
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)
    if crop:
        l, t, r, b = crop
        pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = l, t, r, b
        iw, ih = Image.open(path).size
        vis_w, vis_h = iw * (1 - l - r), ih * (1 - t - b)
        if w:
            pic.width, pic.height = Inches(w), Inches(w * vis_h / vis_w)
        else:
            pic.height, pic.width = Inches(h), Inches(h * vis_w / vis_h)
    if border:
        pic.line.color.rgb = rgb(border)
        pic.line.width = Pt(0.75)
    return pic


def image_fit(slide, name, x, y, w, h, focus=(0.5, 0.0), border=LINE):
    """w×h 프레임에 맞춰 잘라 넣기 (focus: 잘라낼 때 유지할 기준점, 0~1)."""
    path = SCREENS / f"{name}.png"
    if not path.exists():
        return image(slide, name, x, y, w=w, h=h)
    iw, ih = Image.open(path).size
    target, actual = w / h, iw / ih
    l = t = r = b = 0.0
    if actual > target:
        cut = 1 - target / actual
        l, r = cut * focus[0], cut * (1 - focus[0])
    else:
        cut = 1 - actual / target
        t, b = cut * focus[1], cut * (1 - focus[1])
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = l, t, r, b
    if border:
        pic.line.color.rgb = rgb(border)
        pic.line.width = Pt(0.75)
    return pic


def table(slide, x, y, w, rows, widths, size=11, row_h=0.42, header_color=GOLD, first_col_bold=True):
    shp = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tbl = shp.table
    tblpr = shp._element.graphic.graphicData.tbl.tblPr
    for attr in ("bandRow", "firstRow"):
        tblpr.set(attr, "0")
    style = tblpr.find(qn("a:tableStyleId"))
    if style is not None:
        style.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # No Style, No Grid
    for i, wd in enumerate(widths):
        tbl.columns[i].width = Inches(wd)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(SURFACE2 if r == 0 else (SURFACE if r % 2 else "0D0D15"))
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            tf.text = ""
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = str(val)
            if r == 0:
                _font(run, size, header_color, True)
            else:
                _font(run, size, FG if (c == 0 and first_col_bold) else "C9C7DA", c == 0 and first_col_bold)
    return tbl


def qr_tile(slide, x, y, size, data, caption):
    path = TMP / f"qr_{abs(hash(data))}.png"
    qrcode.make(data, box_size=10, border=2).save(path)
    rect(slide, x - 0.06, y - 0.06, size + 0.12, size + 0.12, fill="FFFFFF", line=None, radius=0.06)
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(size), Inches(size))
    text(slide, x - 0.4, y + size + 0.1, size + 0.8, 0.5,
         [[(caption, {"bold": True, "size": 11})], [(data.replace("https://", ""), {"color": MUTED, "size": 8})]],
         align=PP_ALIGN.CENTER, gap=0)


# ----------------------------------------------------------------------------- slide chrome
def new_slide(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(INK)
    return s


def header(s, n, kicker, title, sub=""):
    rect(s, 0, 0, 13.333, 0.06, fill=ACCENT, line=None, radius=0)
    text(s, 0.55, 0.32, 9, 0.3, [[(f"{n:02d}  ", {"color": ACCENT, "bold": True}), (kicker, {"color": ACCENT})]], size=11)
    text(s, 0.55, 0.58, 12.2, 0.6, title, size=28, bold=True)
    if sub:
        text(s, 0.55, 1.14, 12.2, 0.35, sub, size=13, color=MUTED)


def footer(s, n):
    s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(0.55), Inches(7.05), Inches(12.78), Inches(7.05)).line.color.rgb = rgb(LINE)
    text(s, 0.55, 7.1, 8, 0.3, [[("MOV", {"bold": True}), ("PICK", {"bold": True, "color": ACCENT}),
                                  ("   RPA 기반 영화 상영 시간표 동기화 · 명당 자리 실시간 예매 추천", {"color": MUTED})]], size=9)
    text(s, 11.3, 7.1, 1.48, 0.3, f"{n} / {TOTAL}", size=9, color=MUTED, align=PP_ALIGN.RIGHT)


def notes(s, script, point):
    tf = s.notes_slide.notes_text_frame
    tf.text = f"[발표 스크립트]\n{script}\n\n[면접관 어필 포인트]\n{point}"


def callout(s, x, y, w, h, title, body, color=GOLD):
    rect(s, x, y, w, h, fill="15140F" if color == GOLD else SURFACE, line=color)
    text(s, x + 0.2, y + 0.1, w - 0.4, h - 0.2, [[(title + "  ", {"bold": True, "color": color}), (body, {})]],
         size=13, anchor=MSO_ANCHOR.MIDDLE)


# ----------------------------------------------------------------------------- slides
def s01_title(prs):
    s = new_slide(prs)
    image(s, "login", 6.55, 0, h=7.5, border=None, crop=(0.0, 0.0, 0.47, 0.0))
    shade = rect(s, 6.55, 0, 6.8, 7.5, fill=INK, line=None, radius=0)
    shade.fill.fore_color.brightness = 0
    _transparency(shade, 38)
    rect(s, 0, 0, 0.12, 7.5, fill=ACCENT, line=None, radius=0)
    text(s, 0.8, 0.9, 6, 0.3, "SEMI-PROJECT  ·  TEAM MOVPICK", size=12, color=ACCENT, bold=True)
    text(s, 0.8, 1.3, 7, 1.3, [[("MOV", {"bold": True, "size": 80}), ("PICK", {"bold": True, "size": 80, "color": ACCENT})]],
         font="Segoe UI Black")
    text(s, 0.8, 2.7, 5.6, 1.0, [[("명당 자리가 비는 순간,", {})], [("가장 먼저 ", {"color": GOLD}), ("알려드려요", {})]],
         size=26, bold=True, gap=0, spacing=1.05)
    text(s, 0.8, 3.75, 5.6, 0.7, ["RPA 기반 영화 상영 시간표 자동 동기화 및", "명당 자리 실시간 예매 추천 플랫폼"],
         size=14, color=MUTED, gap=0)
    text(s, 0.8, 4.5, 5.6, 0.9, [
        [("발표자  ", {"color": MUTED}), ("이오리", {"bold": True})],
        [("팀 movpick  ", {"color": MUTED}), ("박미금(조장) · 김모란 · 이오리 · 홍기흥", {})],
        [("기간  ", {"color": MUTED}), ("2026. 11", {})],
    ], size=14, gap=3)
    qr_tile(s, 0.95, 5.6, 0.85, LINKS["service"], "서비스")
    qr_tile(s, 2.6, 5.6, 0.85, LINKS["github"], "GitHub")
    qr_tile(s, 4.25, 5.6, 0.85, LINKS["docs"], "API 문서")
    notes(s, "안녕하세요, 팀 movpick의 이오리입니다. 저희는 영화 예매에서 가장 아쉬운 순간, 원하는 명당 자리가 매진이라 "
             "취소표가 나올 때까지 앱을 새로고침해야 하는 문제를 RPA와 실시간 알림으로 풀었습니다. "
             "오늘은 기능 소개보다 어떤 판단으로 이렇게 설계했고, 실제 배포 환경에서 어떤 문제를 어떻게 해결했는지에 집중해 말씀드리겠습니다.",
          "첫 문장에서 '문제 → 해결 방식(RPA·실시간)'을 제시하고, 발표 방향을 의사결정·트러블슈팅으로 예고해 기대치를 설정")


def _transparency(shape, pct):
    sf = shape.fill._xPr.find(qn("a:solidFill"))
    clr = sf[0]
    a = clr.makeelement(qn("a:alpha"), {"val": str((100 - pct) * 1000)})
    clr.append(a)


def s02_problem(prs):
    s = new_slide(prs)
    header(s, 2, "BACKGROUND & PROBLEM", "명당 자리는 '새로고침'으로 잡는다?", "기존 예매 환경의 세 가지 한계")
    cards = [
        ("01", "반복 새로고침", ["취소표는 예고 없이 발생", "원하는 자리가 비는지 사람이 계속 확인", "놓치면 다시 매진"]),
        ("02", "파편화된 상영 정보", ["CGV · 메가박스 · 롯데시네마", "체인마다 다른 앱/웹과 조회 방식", "같은 영화도 3번 검색"]),
        ("03", "잔여석은 '숫자'뿐", ["목록에서는 '97/192석' 같은 수치만 노출", "어느 자리가 비었는지는 예매 단계에서야 확인", "명당 여부 판단 불가"]),
    ]
    for i, (no, title, lines) in enumerate(cards):
        x = 0.55 + i * 4.13
        rect(s, x, 1.75, 3.93, 3.55, fill=SURFACE, line=LINE)
        text(s, x + 0.3, 1.95, 2, 0.6, no, size=34, bold=True, color=ACCENT, font="Segoe UI Black")
        text(s, x + 0.3, 2.7, 3.4, 0.5, title, size=20, bold=True)
        bullets(s, x + 0.3, 3.3, 3.45, 1.9, lines, size=13, marker_color=MUTED)
    callout(s, 0.55, 5.6, 12.23, 1.1, "기획 의도",
            "수집은 RPA가, 감시는 서버가 — 사용자는 '명당 자리가 비었다'는 알림만 받는다. "
            "흩어진 3사 데이터를 한 화면으로 모으고, 잔여석 숫자를 좌석 배치와 명당 점수로 바꾼다.")
    footer(s, 2)
    notes(s, "명당 자리를 원하는 관객은 보통 매진 이후 취소표를 기다립니다. 그런데 취소표는 예고 없이 나오고, 체인이 세 곳이라 앱도 세 개를 오가야 하죠. "
             "게다가 목록 화면은 '97석 남음'처럼 숫자만 보여줘서, 그 자리가 명당인지는 예매 단계까지 들어가 봐야 압니다. "
             "그래서 저희는 '확인하는 일'을 사람이 아니라 시스템이 하도록, 수집은 RPA, 감시는 서버, 사용자는 알림만 받는 구조를 목표로 잡았습니다.",
          "사용자 페인포인트를 데이터 문제(수집 자동화·파편화·정보 부족)로 재정의해 엔지니어링 과제로 연결")


def s03_solution(prs):
    s = new_slide(prs)
    header(s, 3, "SOLUTION", "movpick의 3대 핵심 기능", "자동 수집 → 명당 판단 → 실시간 알림의 하나의 파이프라인")
    feats = [
        ("①", "RPA 자동 동기화", ACCENT, ["3사 6개 지점 상영 시간표·잔여석", "30분 주기 · 오늘+내일 · 하루 약 450회차", "HTTP 우선 → Playwright 폴백"]),
        ("②", "명당 자리 추천", GOLD, ["NumPy 좌석 점수 모델", "상위 18% 명당 하이라이트 · 히트맵", "잔여석 수 기반 좌석 배치 재구성"]),
        ("③", "취소표 실시간 알림", MINT, ["좌석 모니터가 변동 diff 감지", "WebSocket 팝업 · 토스트 · OS 알림", "텔레그램 · 디스코드 · 이메일 웹훅"]),
    ]
    for i, (no, title, color, lines) in enumerate(feats):
        x = 0.55 + i * 4.13
        rect(s, x, 1.7, 3.93, 2.2, fill=SURFACE, line=color, width=1.25)
        text(s, x + 0.25, 1.82, 3.5, 0.5, [[(no + "  ", {"color": color, "bold": True}), (title, {"bold": True})]], size=19)
        bullets(s, x + 0.25, 2.4, 3.55, 1.5, lines, size=12.5, marker_color=color, gap=4)
    shots = [("home", "상영작 · 3사 통합 시간표", (0.5, 0.15)), ("heatmap", "명당 하이라이트 · 히트맵", (0.5, 0.35)),
             ("popup", "취소표 실시간 팝업", (0.5, 0.4))]
    for i, (name, cap, focus) in enumerate(shots):
        x = 0.55 + i * 4.13
        image_fit(s, name, x, 4.1, 3.93, 2.4, focus=focus)
        label(s, x, 6.58, 3.93, cap, size=11)
    footer(s, 3)
    notes(s, "해결 방식은 세 단계입니다. 첫째, 3사 상영 시간표와 잔여석을 30분마다 자동으로 수집합니다. 둘째, 수집한 잔여석을 좌석 배치와 명당 점수로 바꿔 어디가 좋은 자리인지 보여줍니다. "
             "셋째, 사용자가 감시를 걸어두면 좌석 모니터가 변화를 감지해 WebSocket과 웹훅으로 즉시 알립니다. 이 세 기능이 따로 노는 게 아니라 하나의 데이터 파이프라인으로 이어져 있다는 점이 핵심입니다.",
          "기능을 '수집→판단→알림' 데이터 흐름으로 묶어 설명 — 단순 기능 나열이 아닌 파이프라인 사고를 보여줌")


def s04_architecture(prs):
    s = new_slide(prs)
    header(s, 4, "ARCHITECTURE", "전체 시스템 아키텍처", "프런트 정적 CDN · API 컨테이너 · 클라우드 DB 분리 + 수집·감시 백그라운드 루프")
    # client side
    node(s, 0.5, 1.75, 2.7, 1.05, "사용자 브라우저", "React 19 · Vite · Tailwind v4\nREST + WebSocket 클라이언트", line=SKY)
    node(s, 0.5, 3.3, 1.3, 0.8, "Netlify", "Staging", size=12)
    node(s, 1.9, 3.3, 1.3, 0.8, "Render Static", "Production", size=12)
    arrow(s, 1.85, 3.3, 1.85, 2.82)
    label(s, 1.9, 2.92, 1.4, "정적 배포", size=9, align=PP_ALIGN.LEFT)
    node(s, 0.5, 4.7, 2.7, 1.05, "국내 원격 수집기 (선택)", "rpa.runner --push · Docker\n국외 IP 차단 체인 대응", line=GOLD, dash=True)
    # server container
    rect(s, 3.75, 1.65, 4.95, 4.2, fill=SURFACE, line=ACCENT, width=1.5)
    text(s, 3.95, 1.72, 4.6, 0.35, [[("FastAPI ", {"bold": True}), ("· Render Docker · 단일 워커", {"color": MUTED})]], size=12.5)
    subs = [("REST API", "/api/* · JWT · RBAC"), ("WebSocket Hub", "/ws · 사용자별 푸시"),
            ("Crawler Loop", "asyncio · 30분 주기"), ("Seat Monitor", "20초 · 변동 diff"),
            ("Ingest API", "/api/rpa/ingest · 토큰"), ("Notifier", "웹훅 멀티 채널")]
    for i, (t, d) in enumerate(subs):
        node(s, 3.95 + (i % 2) * 2.35, 2.15 + (i // 2) * 0.92, 2.2, 0.78, t, d, size=12)
    text(s, 3.95, 5.0, 4.6, 0.7, "SQLAlchemy 2 · Pydantic · PyJWT · bcrypt · httpx\nPlaywright Chromium (빌드 타임 설치)", size=10, color=MUTED,
         align=PP_ALIGN.CENTER)
    # right side
    node(s, 9.3, 1.75, 2.0, 1.55, "RPA 어댑터", "CGV · 메가박스\n롯데시네마 · Mock\nRequests / Playwright", line=ACCENT, size=12)
    node(s, 11.55, 1.75, 1.3, 1.55, "영화관 3사", "스케줄 API\n(WAF)", size=12)
    node(s, 9.3, 3.6, 3.55, 0.9, "TiDB Cloud", "MySQL 호환 · TLS · 로컬/운영 동일 DB", line=MINT)
    node(s, 9.3, 4.8, 3.55, 0.9, "알림 채널", "Telegram · Discord · Email(SMTP)", line=GOLD)
    # arrows
    arrow(s, 3.2, 2.15, 3.95, 2.45, color=SKY)
    arrow(s, 3.95, 2.75, 3.2, 2.5, color=MINT)
    label(s, 2.9, 1.5, 1.4, "HTTPS REST", size=9)
    label(s, 2.95, 2.75, 1.2, "WSS 푸시", size=9, color=MINT)
    arrow(s, 8.7, 2.45, 9.3, 2.45, color=ACCENT)
    label(s, 8.45, 2.12, 1.1, "수집 요청", size=9)
    arrow(s, 11.3, 2.5, 11.55, 2.5, color=ACCENT)
    arrow(s, 8.7, 4.05, 9.3, 4.05, color=MINT, both=True)
    arrow(s, 8.5, 4.35, 9.3, 5.2, color=GOLD)
    arrow(s, 3.2, 5.2, 3.95, 4.45, color=GOLD, dash=True)
    # design points
    pts = [("독립 배포", "프런트(CDN)와 API(컨테이너) 분리 → 장애·배포 영향 격리"),
           ("단일 워커", "수집·감시 루프가 프로세스 내 동작 → 중복 실행 방지 (확장은 Redis로)"),
           ("확장 경로", "차단 사이트는 원격 수집기 → 토큰 인증 수신 API")]
    for i, (k, v) in enumerate(pts):
        x = 0.5 + i * 4.13
        rect(s, x, 6.05, 3.98, 0.82, fill=SURFACE2, line=None)
        text(s, x + 0.15, 6.1, 3.7, 0.72, [[(k, {"bold": True, "color": GOLD, "size": 12})], [(v, {"size": 10.5, "color": "C9C7DA"})]],
             gap=1, anchor=MSO_ANCHOR.MIDDLE)
    footer(s, 4)
    notes(s, "아키텍처는 세 덩어리로 나눴습니다. React 프런트는 Netlify와 Render Static에 정적 배포하고, FastAPI 백엔드는 Playwright 크로미움이 들어간 Docker 이미지로 Render에 올렸습니다. DB는 TiDB Cloud입니다. "
             "특징은 크롤러와 좌석 모니터가 별도 서버가 아니라 API 프로세스 안의 asyncio 백그라운드 루프라는 점입니다. 비용과 운영 단순성을 위해 택했고, 대신 워커를 하나로 제한했습니다. "
             "또 CGV처럼 해외 서버를 막는 사이트는 국내 원격 수집기가 토큰 인증 수신 API로 데이터를 넣을 수 있게 확장 경로를 열어 두었습니다.",
          "구성요소 나열보다 '왜 분리했고, 무엇을 포기했는가(단일 워커)'를 스스로 말해 트레이드오프 인식을 보여줌")


def s05_stack(prs):
    s = new_slide(prs)
    header(s, 5, "TECH STACK & WHY", "기술 스택 선정 이유", "'가볍게 시도하고, 막히면 무거운 수단으로' — 모든 계층에 폴백을 설계")
    rows = [
        ["영역", "선택", "선택 근거 (Why)"],
        ["Frontend", "React 19 · Vite 6 · Tailwind v4", "좌석 맵·실시간 상태를 컴포넌트로 관리, @theme 토큰으로 디자인 시스템 일원화"],
        ["Backend", "FastAPI (Python 3.11)", "async + WebSocket 기본 지원, Pydantic 입력 검증, Swagger 자동 문서로 협업 비용 절감"],
        ["Database", "TiDB Cloud (MySQL 호환)", "서버리스 + TLS, 로컬과 운영이 같은 DB → 환경 차이 제거 / 테스트는 임시 SQLite로 격리"],
        ["RPA", "Requests → Playwright", "가벼운 HTTP 우선, Cloudflare WAF로 막히면 실제 브라우저 컨텍스트에서 API 호출"],
        ["Data", "NumPy · pandas · Plotly", "좌석 점수 벡터 연산, 영화·체인별 집계, 관리자 리포트를 HTML로 즉시 렌더"],
        ["Infra", "Docker · Render · Netlify · GH Actions", "Chromium을 빌드 타임에 설치, 프런트/백 독립 배포, CI로 테스트·이미지 빌드 게이트"],
    ]
    table(s, 0.55, 1.7, 12.23, rows, [1.45, 3.4, 7.38], size=12, row_h=0.6)
    callout(s, 0.55, 6.05, 12.23, 0.8, "폴백 원칙",
            "HTTP → Playwright  ·  TiDB → SQLite(테스트)  ·  실데이터 → 모의 데이터(장애 시)  ·  WebSocket 끊김 → 지수 백오프 재연결")
    footer(s, 5)
    notes(s, "스택을 고를 때 기준은 '가볍게 시도하고 막히면 무거운 수단으로'였습니다. 예를 들어 크롤링은 처음부터 브라우저를 띄우지 않고 HTTP 요청을 먼저 시도하고, 방화벽에 막힐 때만 Playwright를 씁니다. "
             "DB는 TiDB Cloud를 로컬과 운영 모두에 직접 연결해서 'SQLite에서는 됐는데 운영 MySQL에서는 안 되는' 차이를 없앴고, 대신 테스트만은 임시 SQLite로 격리해 운영 데이터를 건드리지 않게 했습니다. "
             "FastAPI는 WebSocket과 비동기가 기본이라 실시간 알림 요구사항에 가장 잘 맞았습니다.",
          "각 기술을 요구사항(실시간·WAF·환경 일치)과 연결하고, 일관된 설계 원칙(폴백)으로 묶어 설명")


def s06_rpa(prs):
    s = new_slide(prs)
    header(s, 6, "CORE TECH ①  RPA PIPELINE", "RPA 자동화 파이프라인", "체인별 어댑터 · 2단계 수집 · 정합성 정책 · 실패 격리")
    steps = [("스케줄러", "30분 주기\n오늘 + 내일", SKY), ("체인 어댑터", "CGV · 메가박스\n롯데 · Mock", FG),
             ("수집", "HTTP(XHR 헤더) 우선\n→ Playwright 폴백", ACCENT), ("정제", "BS4 텍스트 정제\n중복 회차 제거", FG),
             ("정합성 정책", "실데이터 보호(TTL)\n모의 폴백 · 데모 모드", GOLD), ("적재 · 전파", "TiDB upsert\ncrawl_logs · WS 전파", MINT)]
    for i, (t, d, c) in enumerate(steps):
        x = 0.55 + i * 2.07
        node(s, x, 1.75, 1.82, 1.25, t, d, line=c, size=13)
        if i < len(steps) - 1:
            arrow(s, x + 1.82, 2.37, x + 2.07, 2.37, color=c)
    rows = [["체인", "지점", "수집 방식", "운영 상태"],
            ["메가박스", "코엑스 · 강남", "JSON 엔드포인트 (Requests)", "실데이터"],
            ["롯데시네마", "월드타워 · 가산디지털", "JSON 엔드포인트 (Requests)", "실데이터"],
            ["CGV", "강남 · 용산아이파크몰", "XHR 헤더 HTTP → Playwright 폴백", "국외 IP 차단 → 데모 모드"]]
    table(s, 0.55, 3.3, 7.3, rows, [1.25, 1.85, 2.6, 1.6], size=11.5, row_h=0.5)
    bullets(s, 8.2, 3.3, 4.6, 3.5, [
        ("실패 격리", "체인·일자 단위 try → 한 곳 장애가 전체를 멈추지 않음"),
        ("멱등 적재", "(chain, external_id) UNIQUE + upsert"),
        ("실데이터 보호", "수집 실패 시 기존 실데이터 유지, 모의 데이터와 혼재 금지"),
        ("관측성", "crawl_logs(성공/실패·출처·소요ms) + 관리자 '수집 진단'"),
    ], size=12.5, gap=8)
    text(s, 0.55, 5.45, 7.3, 1.4, [
        [("데이터 정합성 정책", {"bold": True, "color": GOLD})],
        [("실데이터 有 → 실패해도 유지 (TTL 180분 초과 시 '갱신 지연' 경고)", {})],
        [("실데이터 無 → 모의 데이터로 대체  ·  RPA_MOCK_CHAINS → 데모 모드 고정", {})],
    ], size=12, gap=3)
    footer(s, 6)
    notes(s, "수집 파이프라인은 체인마다 어댑터를 두고 공통 인터페이스로 묶었습니다. 메가박스와 롯데시네마는 웹이 쓰는 JSON 엔드포인트를 쓰고, CGV는 Cloudflare 방화벽 때문에 브라우저 XHR 헤더를 갖춘 HTTP를 먼저 시도하고 실패하면 Playwright로 넘어갑니다. "
             "제가 특히 신경 쓴 건 장애 상황입니다. 체인 하나가 실패해도 나머지는 계속 돌고, 수집이 실패하면 멀쩡한 실데이터를 모의 데이터로 덮지 않습니다. 실데이터와 모의 데이터가 한 화면에 섞이지 않게 하는 정책까지 코드와 테스트로 고정했습니다.",
          "'잘 돌 때'보다 '실패할 때'의 동작(격리·멱등·정합성·관측성)을 설계했다는 점이 데이터 엔지니어링 역량으로 어필")


def s07_algorithm(prs):
    s = new_slide(prs)
    header(s, 7, "CORE TECH ②  PRIME SEAT & ANALYTICS", "명당 자리 알고리즘 & 데이터 분석", "잔여석 '숫자'를 좌석 배치와 점수로 바꾸는 로직")
    rect(s, 0.55, 1.7, 6.3, 2.0, fill="0B0B12", line=GOLD)
    text(s, 0.8, 1.8, 5.9, 1.85, [
        [("명당 점수 (NumPy 벡터 연산)", {"bold": True, "color": GOLD, "font": FONT, "size": 13})],
        [("r0 = 0.62·(R−1),  c0 = (C−1)/2", {})],
        [("dr = |r−r0|/(R−1),  dc = |c−c0|/(C−1)", {})],
        [("score = clip(1 − (1.6·dr + 1.4·dc)^1.2, 0, 1)", {"bold": True, "color": FG})],
        [("명당 = score 상위 18%  ·  추천 = 빈 명당 상위 4석", {})],
    ], size=13, font=MONO, color="C9C7DA", gap=3)
    bullets(s, 0.55, 3.95, 6.3, 1.6, [
        ("좌석 배치 재구성", "정원 = 총 좌석 수가 되도록 뒷줄 양끝 제거"),
        ("현실적 점유 분포", "가중 샘플링 (0.35 + score)³ → 명당부터 팔림"),
        ("실수치 보정", "재수집 시 잔여석 수에 맞춰 최소 변경(reconcile)"),
    ], size=12.5, gap=6)
    rect(s, 0.55, 5.6, 6.3, 1.25, fill=SURFACE, line=LINE)
    text(s, 0.75, 5.65, 5.95, 1.15, [
        [("pandas 인기 순위 = '판매 좌석 수' 합계", {"bold": True, "color": MINT})],
        [("예매율만 쓰면 1회차짜리 영화가 1위가 되는 왜곡 → 판매 좌석 기준 + 실데이터 우선", {"size": 11.5})],
        [("Plotly: 크롤링 소요시간·출처 리포트를 HTML로 관리자 화면에 임베드", {"size": 11.5, "color": MUTED})],
    ], size=13, gap=2)
    image(s, "heatmap", 7.15, 1.7, w=5.63)
    label(s, 7.15, 6.25, 5.63, "히트맵: 노랑(명당) → 빨강(외곽) · 어두운 칸 = 예매됨", size=10.5)
    footer(s, 7)
    notes(s, "영화관은 잔여석을 숫자로만 줍니다. 그래서 저희는 총 좌석 수에 맞는 배치도를 만들고, 스크린에서 약 3분의 2 지점이면서 중앙에 가까울수록 점수가 높은 거리 함수로 명당을 계산했습니다. 상위 18%를 명당으로 표시합니다. "
             "점유 좌석은 명당부터 팔리는 실제 분포를 흉내 내도록 가중 샘플링했고, 다시 수집하면 실제 잔여석 수에 맞춰 최소한으로만 보정합니다. 이 배치가 '추정'이라는 점은 화면에도 명시했습니다. "
             "인기 순위도 예매율 대신 판매 좌석 수 합계를 써서, 회차가 하나뿐인 영화가 1위로 튀는 왜곡을 막았습니다.",
          "수식·가정·한계를 투명하게 설명하고, 지표 선택(예매율 vs 판매 좌석)의 통계적 왜곡까지 고려한 판단을 강조")


def s08_auth(prs):
    s = new_slide(prs)
    header(s, 8, "DEMO ①  AUTH & SECURITY UX", "사용자 인증 및 보안", "상용 서비스 수준의 로그인 경험 + 서버 측 보안 강제")
    image(s, "login", 0.55, 1.7, w=7.2)
    bullets(s, 8.05, 1.7, 4.75, 5.2, [
        ("풀블리드 Split 로그인", "오늘 인기 1위 포스터 · 실시간 예매율"),
        ("비밀번호 규칙", "대·소문자+숫자+특수문자 8자↑, 공백 금지"),
        ("-", "서버 정규식 + 클라이언트 실시간 체크리스트 이중 검증"),
        ("OAuth 3사", "Google · Naver · Kakao"),
        ("-", "state = JWT 서명(10분 만료), 복귀 Origin 화이트리스트"),
        ("-", "redirect_uri는 프록시 반영 요청 주소로 생성"),
        ("원클릭 테스트 로그인", "면접관이 가입 없이 30초 안에 체험"),
        ("-", "입력 애니메이션으로 계정 정보 노출, 관리자는 읽기 전용"),
        ("토큰", "JWT(HS256) · bcrypt 해시 · 401/403 일관 처리"),
    ], size=12.5, gap=5)
    footer(s, 8)
    notes(s, "로그인은 왼쪽에 오늘 판매 좌석 1위 영화를, 오른쪽에 폼을 두는 분할 레이아웃입니다. 비밀번호 규칙은 서버 정규식으로 강제하고, 화면에서는 조건별 체크리스트로 바로 보여줍니다. "
             "소셜 로그인은 구글·네이버·카카오 3사를 붙였고, state 값을 JWT로 서명해 위조를 막고, 로그인 후 돌아갈 주소도 화이트리스트로 검증합니다. "
             "또 면접관이나 테스트 사용자가 가입 없이 바로 체험할 수 있도록 원클릭 테스트 로그인을 만들었는데, 테스트 관리자는 일부러 읽기 전용으로 막아서 공개 계정이 데이터를 바꿀 수 없게 했습니다.",
          "UX 편의(원클릭 체험)와 보안(읽기 전용·state 서명·Origin 검증)을 동시에 고려한 균형 감각")


def s09_flow(prs):
    s = new_slide(prs)
    header(s, 9, "DEMO ②  CORE USER FLOW", "핵심 유저 플로우: 상영작 조회 → 취소표 알림", "사용자는 감시만 걸어두고, 알림은 서버가 보낸다")
    shots = [("home", "① 3사 통합 상영작 · 잔여석", (0.0, 0.0, 0.0, 0.1)), ("watch", "② 좌석 맵 · 명당 감시 등록", None),
             ("popup", "③ 취소표 실시간 팝업 · 토스트", None)]
    for i, (name, cap, crop) in enumerate(shots):
        x = 0.55 + i * 4.13
        image(s, name, x, 1.7, w=3.93, crop=crop)
        label(s, x, 4.25, 3.93, cap, size=11.5, color=FG)
        if i < 2:
            arrow(s, x + 3.95, 2.9, x + 4.11, 2.9, color=ACCENT, width=2)
    flow = [("Seat Monitor", "20초 주기"), ("변동 diff", "빈 좌석 ∩ 감시 대상\n− 이미 알린 좌석"), ("send_user", "사용자별 WebSocket"),
            ("브라우저", "팝업 · 토스트\nOS Notification"), ("웹훅", "Telegram · Discord\nEmail")]
    for i, (t, d) in enumerate(flow):
        x = 0.55 + i * 2.2
        node(s, x, 4.8, 1.95, 1.15, t, d, line=MINT if i < 4 else GOLD, size=12)
        if i < len(flow) - 1:
            arrow(s, x + 1.95, 5.37, x + 2.2, 5.37, color=MINT)
    rect(s, 11.6, 4.8, 1.18, 1.15, fill="0F1F19", line=MINT)
    text(s, 11.6, 4.85, 1.18, 1.05, [[("4.7s", {"bold": True, "color": MINT, "size": 22, "font": "Segoe UI Black"})],
                                       [("E2E 실측", {"color": MUTED, "size": 10})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, gap=0)
    text(s, 0.55, 6.15, 12.2, 0.7, "중복 알림 방지: 마지막으로 알린 좌석 집합(last_notified)을 저장해 '새로 비워진 좌석'만 전송  ·  "
                                    "연결 끊김 시 지수 백오프 재연결 + 25초 ping", size=11.5, color=MUTED)
    footer(s, 9)
    notes(s, "실제 흐름입니다. 사용자는 상영작 목록에서 회차를 고르고, 좌석 맵에서 명당을 확인한 뒤 '명당 자리 전체 감시'를 누릅니다. 그다음은 서버 몫입니다. "
             "좌석 모니터가 20초마다 감시 중인 회차를 보고, 지금 비어 있는 감시 대상 좌석에서 이미 알린 좌석을 뺀 '새로 비워진 좌석'만 골라 해당 사용자에게만 WebSocket으로 보냅니다. "
             "브라우저에서는 팝업과 토스트, 탭이 백그라운드면 OS 알림까지 뜹니다. 좌석이 빈 순간부터 팝업까지 E2E로 재보니 4.7초였습니다.",
          "실시간 시스템의 핵심(변동 감지·중복 방지·사용자 단위 전송·재연결)을 수치(4.7초)로 증명")


def s10_ui(prs):
    s = new_slide(prs)
    header(s, 10, "DEMO ③  RESPONSIVE UI & DESIGN SYSTEM", "반응형 UI/UX 및 디자인 시스템", "시네마틱 다크 톤앤매너 · 모바일 우선 상호작용")
    bullets(s, 0.55, 1.75, 5.6, 5.1, [
        ("모바일 GNB", "햄버거 ↔ X 3-bar transform 애니메이션"),
        ("우측 Drawer", "슬라이드 인 · 검색 · 알림 설정 바로가기"),
        ("-", "ESC / 오버레이 닫기, 열림 시 body 스크롤 잠금, 접근성 aria"),
        ("서체 이원화", "타이틀 Bebas Neue · Black Han Sans / 본문 Pretendard"),
        ("컬러 토큰", "Tailwind v4 @theme: ink · accent · gold · mint"),
        ("일관된 골격", "전 페이지 동일 헤더·상용형 다단 푸터·원형 To-Top"),
        ("반응형 좌석 맵", "1fr 그리드 + clamp()로 기기 폭에 맞춰 스케일"),
        ("검증", "Playwright로 390 / 900 / 1440 / 1920px 캡처 확인"),
    ], size=12.5, gap=6)
    for i, name in enumerate(["m_login", "m_drawer", "m_seat"]):
        x = 6.45 + i * 2.15
        image(s, name, x, 1.7, h=4.55)
        label(s, x, 6.3, 2.05, ["로그인", "Drawer 메뉴", "좌석 맵"][i], size=11)
    footer(s, 10)
    notes(s, "UI는 영화관 특유의 어두운 분위기를 살린 다크 테마로 통일했습니다. 색과 서체는 Tailwind v4의 테마 토큰으로 한 곳에서 관리하고, 타이틀용 서체와 본문용 서체를 분리해 가독성을 챙겼습니다. "
             "모바일에서는 햄버거 아이콘이 X로 바뀌면서 오른쪽에서 Drawer가 열리고, ESC나 바깥 영역으로 닫히며 뒤쪽 스크롤은 잠급니다. "
             "좌석 맵은 화면 폭에 따라 좌석 크기가 자동으로 줄어들게 했고, 이런 반응형 결과는 Playwright로 여러 해상도를 캡처해서 확인했습니다.",
          "디자인을 '토큰·일관성·접근성·자동 검증'이라는 엔지니어링 관점으로 설명")


def s11_admin(prs):
    s = new_slide(prs)
    header(s, 11, "DEMO ④  ADMIN BACK-OFFICE", "관리자 백오피스 & 접근 제어(RBAC)", "크롤러 운영 대시보드 + 서버 측에서 강제하는 3단계 권한")
    image(s, "admin", 0.55, 1.7, w=6.6)
    rows = [["역할", "권한", "부여 방식"],
            ["일반 회원", "조회 · 감시 등록", "가입 · 소셜 로그인"],
            ["테스트 관리자", "조회만 (쓰기 API 403)", "원클릭 로그인"],
            ["실제 관리자", "크롤러 · 권한 변경", ".env 관리자 키"]]
    table(s, 7.4, 1.7, 5.38, rows, [1.5, 2.13, 1.75], size=11, row_h=0.5)
    bullets(s, 7.4, 3.9, 5.38, 3.0, [
        ("크롤러 대시보드", "주기 설정 · 수동 실행 · 성공/실패 로그 · Plotly"),
        ("수집 진단", "서버 환경에서 실제 사이트 접속을 저장 없이 테스트"),
        ("실시간 권한 변경", "WebSocket role_changed → 대상 화면 즉시 반영"),
        ("보호 규칙", "본인·환경 변수 관리자 강등 불가"),
    ], size=12, gap=6)
    footer(s, 11)
    notes(s, "관리자 화면에서는 크롤러가 언제 돌았고, 어느 체인이 성공·실패했고, 몇 건을 몇 밀리초에 가져왔는지를 봅니다. '수집 진단' 버튼은 지금 서버 위치에서 실제 사이트에 접속되는지를 저장 없이 확인하는 기능인데, 뒤에서 말씀드릴 CGV 문제를 진단할 때 직접 만든 도구입니다. "
             "권한은 세 단계입니다. 테스트 관리자는 화면은 다 보지만 쓰기 API는 서버에서 403으로 막고, 실제 관리자는 환경 변수로만 만들어지며 강등할 수 없습니다. 프런트에서 버튼을 숨기는 것만으로는 보안이 아니기 때문에 서버에서 강제했습니다.",
          "RBAC를 UI 숨김이 아닌 서버 강제로 구현, 운영 도구(수집 진단)를 직접 만들어 문제 해결에 사용한 경험")


def s12_devops(prs):
    s = new_slide(prs)
    header(s, 12, "DEVOPS & CI/CD", "배포 자동화와 환경 변수 관리", "git push 한 번으로 테스트 → 이미지 검증 → 3개 환경 배포")
    node(s, 0.55, 2.0, 1.6, 1.0, "git push", "main", line=FG)
    stages = [("backend", "pytest 24개\nRPA 비활성·임시 DB"), ("frontend", "npm ci\nvite build"),
              ("docker", "API 이미지 빌드\n+ 경량 수집기 이미지\n+ /health 기동 점검"), ("deploy", "배포 훅\n(시크릿 설정 시)")]
    rect(s, 2.45, 1.7, 7.0, 1.6, fill=SURFACE, line=SKY)
    text(s, 2.6, 1.74, 4, 0.3, "GitHub Actions · ci.yml", size=11, color=SKY, bold=True)
    for i, (t, d) in enumerate(stages):
        node(s, 2.6 + i * 1.72, 2.1, 1.55, 1.1, t, d, size=11.5)
        if i < 3:
            arrow(s, 2.6 + i * 1.72 + 1.55, 2.65, 2.6 + (i + 1) * 1.72, 2.65, color=SKY)
    arrow(s, 2.15, 2.5, 2.6, 2.5, color=FG)
    for i, (t, d) in enumerate([("Netlify", "Staging 프런트"), ("Render Static", "운영 프런트"), ("Render Docker", "API · /health 커밋")]):
        node(s, 9.85, 1.7 + i * 0.58, 2.93, 0.5, f"{t}  ·  {d}", size=11, line=MINT)
    text(s, 9.85, 3.48, 2.93, 0.3, "Git 연동 자동 배포", size=10, color=MUTED, align=PP_ALIGN.CENTER)
    rows = [["워크플로", "역할"], ["ci.yml", "테스트 · 빌드 · Docker 스모크 · 배포 훅"],
            ["pages.yml", "pages/ 변경 시 GitHub Pages 안내 페이지 배포"],
            ["cgv-collector.yml", "국내 self-hosted 러너 지정 시 30분 수집"]]
    table(s, 0.55, 3.95, 6.0, rows, [1.9, 4.1], size=11, row_h=0.5)
    bullets(s, 6.9, 3.95, 5.9, 3.0, [
        ("단일 .env", "로컬·서버 동일 키, Render 대시보드에 직접 등록"),
        (".env.example", "Render 필수 변수 표기 · 실제 값은 커밋 금지"),
        ("배포 검증", "/health 응답의 commit 해시로 배포 버전 확인"),
        ("재현성", "베이스 이미지·러너 OS 버전 고정, .gitattributes LF"),
        ("공급망", "의존성 버전 고정 + 최근 7일 이내 패키지 배제"),
    ], size=12, gap=6)
    footer(s, 12)
    notes(s, "main에 푸시하면 GitHub Actions가 백엔드 테스트, 프런트 빌드, 그리고 Playwright가 들어간 Docker 이미지 빌드와 컨테이너 기동 점검까지 합니다. 플랫폼은 Git 연동으로 자동 배포되고, 배포 훅은 시크릿이 있을 때만 호출합니다. "
             "배포가 실제로 반영됐는지는 /health가 돌려주는 커밋 해시로 확인합니다. '배포됐겠지'가 아니라 '이 커밋이 올라갔다'를 확인하는 거죠. "
             "환경 변수는 .env 하나로 관리하고, 필수 키는 .env.example에 문서화하되 실제 값은 저장소에 절대 올리지 않습니다.",
          "CI를 품질 게이트로 쓰고, 배포 결과를 커밋 해시로 검증하는 운영 습관 — 재현성·공급망 보안까지 언급")


def s13_trouble(prs):
    s = new_slide(prs)
    header(s, 13, "TROUBLESHOOTING", "트러블슈팅: 가설 → 검증 → 구조 전환", "실제 배포 환경에서 마주친 문제 3가지")
    text(s, 0.55, 1.6, 12, 0.35, [[("①  CGV 수집 차단 (HTTP 403)", {"bold": True, "color": ACCENT})]], size=15)
    steps = [("curl 403", "단순 요청 차단"), ("Playwright", "로컬 성공"), ("Render 403", "배포 환경 재발"),
             ("헤더 가설 검증", "XHR 헤더 HTTP\n로컬 200 / 서버 403"), ("cf-ray 비교", "ICN 통과\nPDX 차단 → 국외 IP"), ("구조 전환", "원격 수집기 +\n토큰 인증 Ingest API")]
    for i, (t, d) in enumerate(steps):
        x = 0.55 + i * 2.07
        node(s, x, 2.0, 1.82, 1.05, t, d, line=MINT if i == 5 else (ACCENT if "403" in t else LINE), size=12)
        if i < 5:
            arrow(s, x + 1.82, 2.52, x + 2.07, 2.52, color=MUTED)
    text(s, 0.55, 3.15, 12.2, 0.4, "→ 서버 직접 수집을 포기하고 '수집 위치'와 '수신 서버'를 분리. 관리자 수집 진단 · 국내 VM 원클릭 설치 스크립트 · 운영은 체인별 데모 모드로 안정화",
         size=11.5, color=MUTED)
    cards = [
        ("②  OAuth · 배포 환경", [("redirect_uri_mismatch", "운영 BACKEND_URL=localhost → 프록시 반영 요청 주소로 생성"),
                                 ("SPA 404", "Render Static 리라이트 부재 → 로그인 결과를 루트 /#oauth_token 으로"),
                                 ("Docker/CI 실패", "slim=Debian 13 · ubuntu-latest=26 → bookworm · 24.04 고정")]),
        ("③  크롤링 데이터 정합성", [("UNIQUE 위반", "롯데 응답 중복 회차 → 루프 전체 중단 → 중복 제거 + 체인 격리"),
                                   ("실데이터·모의 혼재", "출처별 정리(purge) 정책 + 실데이터 보호 TTL"),
                                   ("UTC/KST 9시간", "DB now() 기본값 → 앱 로컬 시간 + 컨테이너 TZ 고정")]),
    ]
    for i, (title, items) in enumerate(cards):
        x = 0.55 + i * 6.17
        rect(s, x, 3.7, 6.06, 3.15, fill=SURFACE, line=LINE)
        text(s, x + 0.2, 3.8, 5.6, 0.4, title, size=15, bold=True, color=GOLD)
        bullets(s, x + 0.2, 4.35, 5.7, 2.45, items, size=13, gap=12, marker_color=GOLD)
    footer(s, 13)
    notes(s, "가장 오래 붙잡은 문제는 CGV였습니다. 처음엔 단순 요청이 403이라 Playwright로 해결했는데, Render에 올리니 다시 403이었습니다. 헤더 문제라는 가설을 세워 브라우저 헤더를 그대로 붙여 보니 로컬은 통과하고 서버는 여전히 막혔습니다. "
             "Cloudflare 응답의 cf-ray에 찍힌 접속 거점을 비교해 보니 서울(ICN)은 통과, 미국(PDX)은 차단이었고, 그래서 원인이 코드가 아니라 국외 IP 차단이라고 결론 냈습니다. 이후 수집 위치와 수신 서버를 분리하는 구조로 바꿨습니다. "
             "그 밖에도 운영 환경 변수 때문에 생긴 OAuth redirect_uri 불일치, 정적 호스팅의 SPA 404, 중복 데이터로 크롤링 전체가 멈춘 문제를 원인부터 고쳤습니다.",
          "추측이 아닌 가설-검증(cf-ray 근거)으로 원인을 좁히고, 코드 패치가 아니라 아키텍처를 바꾼 문제 해결 방식")


def s14_docs(prs):
    s = new_slide(prs)
    header(s, 14, "DELIVERABLES & QUALITY", "산출물 · 문서화 · 품질 관리", "기록이 남는 프로젝트, 테스트로 보증하는 품질")
    rect(s, 0.55, 1.7, 4.1, 5.15, fill="0B0B12", line=LINE)
    text(s, 0.75, 1.8, 3.8, 5.0, [
        [("docs/", {"bold": True, "color": GOLD})],
        [("├ 산출물/", {})],
        [("│  ├ 01_기획분석 · 02_설계", {"color": MUTED})],
        [("│  └ 03_구현 · 04_배포", {"color": MUTED})],
        [("├ 진행일지_1~4단계", {})],
        [("├ 프로젝트_발표자료.pptx", {})],
        [("└ tools/ (캡처·발표자료 생성)", {})],
        [("", {})],
        [("README.md", {"bold": True, "color": GOLD})],
        [("AGENTS.md  개발 규칙·명령어", {})],
        [(".env.example  필수 변수", {})],
    ], size=12, font=MONO, gap=2)
    rect(s, 4.85, 1.7, 3.9, 5.15, fill=SURFACE, line=LINE)
    text(s, 5.05, 1.8, 3.5, 0.4, [[("pytest ", {"bold": True}), ("24", {"bold": True, "color": MINT, "size": 22}), (" 개 통과", {"bold": True})]], size=15)
    bullets(s, 5.05, 2.4, 3.6, 3.0, [
        "인증 · 비밀번호 규칙 · OAuth redirect_uri",
        "RBAC · 읽기 전용 관리자 · .env 관리자",
        "좌석 모델 · 수신 API 토큰 · 데모 모드",
        "실데이터 보호 · 중복 제거 · WebSocket",
    ], size=11.5, gap=5, marker_color=MINT)
    text(s, 5.05, 5.0, 3.6, 1.75, [[("E2E · 화면 검증", {"bold": True, "color": MINT})],
                                    [("Playwright 실시간 알림 E2E (4.7s)", {"size": 11})],
                                    [("4개 해상도 캡처로 반응형 확인", {"size": 11})],
                                    [("테스트는 임시 SQLite → 운영 DB 무영향", {"size": 11})]], size=13, gap=2)
    rows = [["팀원", "담당 영역"], ["박미금 (조장)", "[담당 영역]"], ["김모란", "[담당 영역]"],
            ["이오리", "[담당 영역]"], ["홍기흥", "[담당 영역]"]]
    table(s, 8.95, 1.7, 3.83, rows, [1.45, 2.38], size=11.5, row_h=0.55)
    text(s, 8.95, 4.65, 3.83, 2.2, [[("협업 방식", {"bold": True, "color": GOLD})],
                                    [("단계별 진행일지로 일정·결정 기록", {"size": 11.5})],
                                    [("커밋 메시지에 '왜'를 남기는 규칙", {"size": 11.5})],
                                    [("AGENTS.md로 환경·명령 표준화", {"size": 11.5})]], size=13, gap=3)
    footer(s, 14)
    notes(s, "문서와 품질 관리입니다. docs 폴더에 기획·설계·구현·배포 단계별 산출물과 진행일지를 쌓았고, README와 AGENTS.md에 실행 방법과 개발 규칙을 정리해서 누가 와도 같은 명령으로 돌릴 수 있게 했습니다. "
             "품질은 pytest 24개로 보증합니다. 인증과 권한, 좌석 모델, 수신 API, 데이터 정합성 정책처럼 깨지면 안 되는 규칙을 테스트로 고정했고, 테스트는 임시 SQLite로 돌아서 운영 DB에는 영향이 없습니다. "
             "팀원별 역할은 표와 같이 나눠 진행했습니다.",
          "문서화·테스트를 '사후 정리'가 아니라 협업과 회귀 방지 수단으로 운영 — 팀 역할은 실제 내용으로 채워 발표")


def s15_retro(prs):
    s = new_slide(prs)
    header(s, 15, "RETROSPECTIVE & NEXT STEP", "회고 및 향후 고도화 계획", "외부 데이터에 기대는 서비스를 만들며 배운 것")
    insights = [("외부 의존은 반드시 실패한다", "수집 실패를 정상 시나리오로 보고 격리·폴백·관측성을 먼저 설계"),
                ("한계는 숨기지 않고 UI에 쓴다", "좌석 배치 '추정', CGV '데모'를 명시 → 사용자·면접관 신뢰"),
                ("배포 환경이 진짜 테스트", "로컬 성공 ≠ 운영 성공 — 지역·OS·환경 변수 차이를 근거로 검증")]
    for i, (k, v) in enumerate(insights):
        y = 1.75 + i * 1.65
        rect(s, 0.55, y, 5.9, 1.45, fill=SURFACE, line=LINE)
        text(s, 0.8, y + 0.15, 5.5, 1.2, [[(k, {"bold": True, "size": 15})], [(v, {"color": MUTED, "size": 12})]], gap=4)
    text(s, 6.85, 1.7, 5.9, 0.4, "Next Step", size=17, bold=True, color=GOLD)
    rows = [["우선순위", "고도화 항목"],
            ["단기", "국내 원격 수집기 상시 운영 → CGV 실데이터 전환"],
            ["단기", "데이터 갱신 지연 시 관리자 웹훅 알림"],
            ["중기", "Redis Pub/Sub로 다중 워커 WebSocket 확장"],
            ["중기", "Alembic 마이그레이션 도입 (스키마 변경 관리)"],
            ["장기", "좌석 선호 이력 기반 개인화 명당 추천"]]
    table(s, 6.85, 2.2, 5.93, rows, [1.2, 4.73], size=12, row_h=0.62)
    footer(s, 15)
    notes(s, "가장 크게 배운 건 외부 사이트에 기대는 서비스는 언젠가 반드시 실패한다는 점입니다. 그래서 실패를 예외가 아니라 정상 시나리오로 놓고 설계했습니다. "
             "또 좌석 배치가 추정이라는 점, CGV가 지금은 데모 데이터라는 점을 숨기지 않고 화면에 표시했는데, 이게 오히려 신뢰를 준다고 생각합니다. "
             "다음 단계로는 국내 수집기를 상시 운영해 CGV를 실데이터로 되돌리고, 사용자가 늘면 Redis Pub/Sub으로 WebSocket을 여러 워커로 확장하고, 스키마 변경은 Alembic으로 관리할 계획입니다.",
          "현재 구조의 한계(단일 워커·스키마 관리)를 스스로 짚고 구체적 확장 경로를 제시 — 시니어 관점의 회고")


def s16_qa(prs):
    s = new_slide(prs)
    rect(s, 0, 0, 13.333, 0.06, fill=ACCENT, line=None, radius=0)
    text(s, 0.55, 0.45, 6, 1.2, [[("Q", {"bold": True, "size": 60}), (" & ", {"size": 60, "color": MUTED}), ("A", {"bold": True, "size": 60, "color": ACCENT})]],
         font="Segoe UI Black")
    text(s, 0.55, 1.65, 6, 0.4, "감사합니다 · 라이브 데모로 직접 확인해 보세요", size=15, color=MUTED)
    qr_tile(s, 0.75, 2.4, 1.15, LINKS["service"], "서비스")
    qr_tile(s, 2.65, 2.4, 1.15, LINKS["github"], "GitHub")
    qr_tile(s, 4.55, 2.4, 1.15, LINKS["docs"], "API 문서")
    rect(s, 0.55, 4.75, 5.6, 2.1, fill=SURFACE, line=LINE)
    text(s, 0.75, 4.85, 5.2, 1.95, [
        [("테스트 계정", {"bold": True, "color": GOLD})],
        [("일반 회원  ", {"color": MUTED}), ("user@movpick.app / Movpick!2026", {"font": MONO})],
        [("관리자(읽기 전용)  ", {"color": MUTED}), ("로그인 화면 원클릭 버튼", {})],
        [("스테이징  ", {"color": MUTED}), ("movpick.netlify.app", {"font": MONO})],
    ], size=12.5, gap=5)
    rows = [["예상 질문", "30초 답변 요지"],
            ["좌석 배치가 추정인데 신뢰할 수 있나?", "잔여석 '수'는 실측, 배치는 추정임을 UI에 명시. 재수집 시 실수치로 보정"],
            ["크롤링의 법적·윤리적 리스크는?", "공개 화면 수준 데이터, 30분 주기 저빈도, 인증 우회 미시도(서명 API 제외)"],
            ["사용자가 늘면 단일 워커는?", "루프 분리 + Redis Pub/Sub 브로드캐스트로 수평 확장"],
            ["수신(Ingest) API 보안은?", "토큰 상수 시간 비교, 데모 모드 체인 거부(409), 입력 스키마 검증"],
            ["왜 실패 시 모의 데이터인가?", "빈 화면 대신 시연 가능 상태 유지, 단 실데이터와 혼재 금지·DEMO 표기"]]
    table(s, 6.45, 0.6, 6.33, rows, [2.45, 3.88], size=10.5, row_h=0.98)
    footer(s, 16)
    notes(s, "발표는 여기까지입니다. QR로 서비스와 저장소, API 문서에 바로 들어가실 수 있고, 로그인 화면의 원클릭 버튼으로 가입 없이 체험하실 수 있습니다. 관리자 계정은 읽기 전용이라 안심하고 둘러보셔도 됩니다. "
             "자주 받을 만한 질문은 오른쪽에 정리해 두었습니다. 좌석 추정의 신뢰성, 크롤링 리스크, 확장성, 수신 API 보안, 모의 데이터 정책에 대해 편하게 질문해 주세요. 감사합니다.",
          "예상 질문을 먼저 제시해 질의응답을 주도하고, 데모 접근성을 극대화(QR·원클릭·읽기 전용)")


def main() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    for fn in (s01_title, s02_problem, s03_solution, s04_architecture, s05_stack, s06_rpa, s07_algorithm, s08_auth,
               s09_flow, s10_ui, s11_admin, s12_devops, s13_trouble, s14_docs, s15_retro, s16_qa):
        fn(prs)
    prs.core_properties.title = "movpick 프로젝트 발표자료"
    prs.core_properties.author = "팀 movpick"
    prs.save(OUT)
    print("saved", OUT, len(prs.slides._sldIdLst), "slides")


if __name__ == "__main__":
    main()
