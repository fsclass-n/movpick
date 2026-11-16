"""진행일지(양식 유지·빈 칸 채움) + 산출물(단계별 상세) 작성 → 한글(HWP COM)로 HWPX 재저장 · PDF 변환

    .venv/Scripts/python docs/tools/build_docs.py

- 진행일지: 기존 표 양식·기간·조·보고자 등 메타데이터는 그대로 두고, 빈 셀에만 같은 문단/글자 스타일로 내용 삽입
- 산출물: 단계별 HTML 원고 → 한글로 열어 HWPX 로 저장(기존 빈 파일 교체)
- PDF: docs/pdf/ 에 같은 이름으로 저장 (한글 PDF 내보내기)
- 한글 자동화 보안 모듈(FilePathCheckerModule) 필요: pyhwpx 패키지에 포함된 DLL 을 레지스트리에 등록해 사용
"""

import html
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import win32com.client as win32

DOCS = Path(__file__).resolve().parents[1]
OUT_PDF = DOCS / "pdf"
TEAM = "박미금(조장) · 김모란 · 이오리 · 홍기흥"
TOPIC = "movpick — RPA 기반 영화 상영 시간표 자동 동기화 및 명당 자리 실시간 예매 추천 플랫폼"

# ============================================================================ 진행일지 내용 (행 번호 → 줄 목록)
COMMON = {1: [TOPIC], 2: [TEAM]}
JOURNAL = {
    "프로젝트_진행일지_1단계_기획분석.hwpx": {
        3: ["서비스 주제 선정 및 문제 정의, 요구사항 도출, 수집 대상(CGV·메가박스·롯데시네마) 조사, 기술 스택 선정, 일정·역할 분담"],
        4: ["- 핵심 가치 확정: \"명당 자리가 비는 순간, 가장 먼저 알려드린다\"",
            "- 핵심 기능 3가지(RPA 자동 동기화 · 명당 자리 추천 · 실시간 취소표 알림) 및 기능/비기능 요구사항 명세",
            "- 3사 상영 시간표·잔여석 수집 가능성 검증, 개발 환경·배포 계정(GitHub·Netlify·Render·TiDB) 준비"],
        5: ["- RPA(Playwright·BeautifulSoup4) 기반 데이터 수집 자동화를 핵심 기술로 적용",
            "- React(Vite)·FastAPI·TiDB·Render/Netlify 구성, 환경 변수는 단일 .env 로 관리",
            "- 반응형 Split 로그인, 테스트 계정 간편 로그인, OAuth(구글·네이버·카카오), 관리자 페이지 요구사항 반영"],
        6: ["- 문제 정의: 명당 자리는 매진 후 취소표로 풀리지만 시점을 알 수 없어 3사 앱을 반복 새로고침해야 함, 상영 정보 파편화, 목록은 잔여석 '숫자'만 제공",
            "- 기능 목록 작성(회원·상영작·좌석 맵·감시/알림·관리자) 및 우선순위 결정, 화면 흐름 초안 작성",
            "- 수집 대상 조사: 메가박스 schedulePage(JSON)·롯데시네마 TicketingData(JSON) 응답 구조 확인, CGV 는 일반 요청 시 403(WAF) 확인",
            "- 기술 스택 선정 근거 정리(비동기·WebSocket=FastAPI, 로컬/운영 동일 DB=TiDB, 동적 페이지=Playwright)",
            "- GitHub 저장소·Pages, Netlify·Render·TiDB 클러스터 연동 확인"],
        7: ["- CGV 수집 방식 확정(WAF 차단 원인 분석 필요로 설계 단계로 이월)", "- OAuth 3사 클라이언트 키 발급·등록(배포 주소 확정 후 진행)"],
        8: ["- 요구사항 정의서, 기능 목록, 수집 대상 조사표, 기술 스택 선정서 작성(산출물 01)",
            "- 범위 확정: 3사 6개 지점, 오늘·내일 상영분, 30분 주기 동기화, 좌석 감시 20초 주기"],
        9: ["- 서비스 콘셉트와 MVP 범위 합의, 명당 자리 기준(스크린 대비 위치·중앙 근접도)을 점수 모델로 정의하기로 결정",
            "- 실패 상황(사이트 구조 변경·차단)을 정상 시나리오로 보고 모의 데이터 폴백을 기본 설계에 포함하기로 합의"],
        10: ["- 영화관이 좌석 단위 정보가 아닌 잔여석 수만 공개 → 좌석 배치를 수치 기반으로 추정해야 함",
             "- CGV 는 일반 HTTP 요청을 403 으로 차단 → 브라우저 기반 수집 또는 우회 경로 검토 필요"],
        11: ["- 좌석 배치 추정 방식과 명당 점수 산식 설계", "- CGV 수집 방식(헤더/브라우저 컨텍스트) 검증 및 실패 시 폴백 정책 수립"],
        12: ["설계 단계 — 시스템 아키텍처, DB·API 설계, RPA 파이프라인과 정합성 정책, 명당 점수 모델, 실시간 알림 흐름, 화면 설계"],
    },
    "프로젝트_진행일지_2단계_설계.hwpx": {
        3: ["시스템 아키텍처, DB 스키마, API 명세, RPA 수집 파이프라인·정합성 정책, 명당 점수·좌석 추정 알고리즘, 실시간 알림 흐름, 권한·화면 설계"],
        4: ["- 프런트(정적 CDN)·API(Docker)·DB(TiDB) 분리 배포 구조 확정",
            "- 테이블 4종(users·showtimes·seat_watches·crawl_logs)과 API 그룹(auth·showtimes·watches·admin·ws) 명세 완료",
            "- 명당 점수 산식과 좌석 감시 diff 알림 로직 확정"],
        5: ["- 설계 근거(Why)와 트레이드오프를 문서에 함께 기록", "- 보안(JWT·bcrypt·OAuth state·CORS)과 관리자 접근 제어(RBAC)를 설계 단계에서 반영"],
        6: ["- 아키텍처: 수집 루프(30분)·좌석 모니터(20초)를 API 프로세스 내 asyncio 백그라운드 작업으로 설계(단일 워커), 동기 크롤러는 asyncio.to_thread 로 실행",
            "- RPA: 체인별 어댑터 + 공통 인터페이스, HTTP 우선 → Playwright 폴백, (chain, external_id) UNIQUE upsert, 체인 단위 실패 격리, crawl_logs 기록",
            "- 정합성 정책: 실데이터가 있으면 수집 실패 시에도 유지, 없으면 모의 데이터로 대체, 실데이터·모의 데이터 혼재 금지",
            "- 명당 모델: score = clip(1 − (1.6·dr + 1.4·dc)^1.2, 0, 1), 기준점 스크린 대비 62% 깊이·중앙 열, 상위 18% 명당, 잔여석 수에 맞춘 배치 재구성",
            "- 알림: 현재 빈 좌석 ∩ 감시 대상 − 이미 알린 좌석 → 사용자별 WebSocket 전송 + 웹훅(텔레그램·디스코드·이메일)",
            "- 화면: Split 로그인, 햄버거↔X 모바일 GNB·우측 Drawer, 반응형 좌석 맵, 관리자 대시보드·회원 권한"],
        7: ["- 국외 IP 차단 사이트용 원격 수집 구조 상세(구현 단계에서 차단 원인 확인 후 설계)", "- 다중 워커 확장(메시지 브로커) 설계는 범위 외로 보류"],
        8: ["- 아키텍처 설계서, ERD·테이블 명세, API 명세서, 파이프라인·알고리즘 설계서, 화면 설계서 작성(산출물 02)"],
        9: ["- 설계 리뷰: 실데이터 보호 정책과 데모 표기 원칙(추정값·모의 데이터는 화면에 명시) 합의",
            "- 무료 서버 제약(메모리 512MB·슬립)을 고려해 브라우저 기동을 최소화하는 방향으로 결정"],
        10: ["- 단일 워커 구조는 확장 시 병목 가능", "- 추정 좌석 배치와 실제 배치의 차이를 사용자에게 어떻게 알릴지 기준 필요"],
        11: ["- 운영(해외 리전) 환경에서 CGV 접근 가능 여부 검증", "- 테스트 전략(임시 DB 격리, RPA 비활성) 구체화"],
        12: ["구현 단계 — 백엔드 API·인증, RPA 어댑터·좌석 모델, 실시간 알림, 프런트엔드 화면, 자동 테스트"],
    },
    "프로젝트_진행일지_3단계_구현.hwpx": {
        3: ["백엔드(FastAPI) 기능 구현, RPA 수집기·좌석 모델 구현, WebSocket 실시간 알림, 프런트엔드(React) 화면, 관리자 백오피스, 자동 테스트 작성"],
        4: ["- 3사 실데이터 수집·동기화(하루 약 450회차)와 명당 추천·감시·알림 전 과정 동작",
            "- 회원/관리자 권한 분리와 테스트 계정 원클릭 로그인 제공", "- pytest 로 핵심 규칙 회귀 방지"],
        5: ["- 설계서의 API·데이터 정책을 그대로 구현하고 변경 시 문서 갱신", "- 비밀 값은 코드·저장소에 넣지 않고 .env 로만 관리"],
        6: ["- 백엔드: JWT·bcrypt 인증, 비밀번호 정규식 검증, 테스트 계정, OAuth 3사(state JWT 서명·Origin 화이트리스트), 상영작·좌석·감시·관리자·통계 API, /ws·/health",
            "- RPA: 메가박스·롯데시네마 JSON 어댑터, CGV XHR 헤더 HTTP → Playwright 폴백, 모의 데이터 생성기, CLI(rpa.runner)",
            "- 좌석 모델(NumPy): 배치 재구성·명당 점수·재수집 보정, 좌석 모니터의 변동 감지·사용자별 알림",
            "- 프런트엔드: 시네마틱 다크 디자인, Split 로그인(인기 1위 포스터), GNB·Drawer, 상영작·좌석 맵·히트맵·알림 설정·관리자 화면, 토스트·팝업",
            "- 관리자: 크롤러 주기·실행·로그·수집 진단·Plotly 리포트, 회원 권한 실시간 변경, 테스트 관리자 읽기 전용(쓰기 403)·.env 실제 관리자",
            "- 트러블슈팅: 롯데 중복 회차 UNIQUE 위반 → 중복 제거·체인 격리, UTC/KST 9시간 차이 → 앱 로컬 시각, 로그인 리다이렉트 경합·StrictMode 중복 실행 수정"],
        7: ["- 운영 서버에서 CGV 실데이터 상시 수집(국외 IP 차단으로 국내 원격 수집기 필요 — 배포 단계로 이월)"],
        8: ["- 기능 구현 완료, pytest 24개 통과, 실시간 알림 E2E 실측 4.7초(좌석 비움 → 브라우저 팝업)",
            "- 구현 산출물(디렉터리 구조·모듈 설명·테스트 결과·트러블슈팅 기록) 작성(산출물 03)"],
        9: ["- 기능 시연 리뷰: 일반 회원/관리자 흐름 점검, 데모·추정 표기 확인",
            "- CGV 는 헤더 조건을 갖춘 HTTP 요청으로 브라우저 없이 수집 가능함을 확인(로컬)"],
        10: ["- 배포 서버(해외 리전)에서는 CGV 가 동일 요청을 403 으로 차단할 가능성",
             "- 좌석 단위 변동은 실측이 불가하여 수집 주기 사이를 시뮬레이션"],
        11: ["- 배포 환경에서 수집 진단 및 원격 수집 경로 구현", "- 운영 환경 변수(OAuth 콜백·CORS) 정리"],
        12: ["배포 단계 — Docker 이미지·Render/Netlify 배포, CI/CD, 운영 검증(CORS·WebSocket·OAuth), 원격 수집기, 발표자료·영상"],
    },
    "프로젝트_진행일지_4단계_배포.hwpx": {
        3: ["Docker 기반 백엔드 배포, 프런트엔드 이중 배포, GitHub Actions CI/CD, 운영 검증, CGV 원격 수집 구조, 발표자료·시연 영상·포트폴리오 제작"],
        4: ["- 운영 서비스 movpick.onrender.com · API movpick-api.onrender.com · 스테이징 movpick.netlify.app 정상 동작",
            "- CI(테스트 → 빌드 → Docker 기동 점검) 통과 후 자동 배포", "- 10분 발표·시연 영상과 GitHub Pages 포트폴리오 공개"],
        5: ["- Render 무료 티어 Docker 빌드 시 Playwright Chromium 을 빌드 타임에 설치", "- Render 필수 환경 변수를 .env.example 에 명시하고 대시보드에 직접 등록"],
        6: ["- Dockerfile(python:3.11-slim-bookworm + Chromium) · docker-compose(backend·frontend·수집기 profile) · render.yaml · netlify.toml 작성",
            "- GitHub Actions: backend(pytest)·frontend(build)·docker(이미지 빌드·/health 기동 점검)·deploy 훅, Pages 워크플로",
            "- 운영 검증: TiDB 연결, CORS(2개 프런트 Origin), wss WebSocket ping/pong, /health 배포 커밋 해시 확인",
            "- 운영 이슈 해결: Docker 베이스 이미지 Debian 13 변경 → bookworm 고정, Render Dockerfile 경로, OAuth redirect_uri_mismatch → 요청 기준 콜백, SPA 404 → 루트 경로 복귀, SPA 리라이트 규칙",
            "- CGV: cf-ray 접속 거점 비교로 국외 IP 차단 규명 → 토큰 인증 수신 API(/api/rpa/ingest)·원격 수집기·국내 VM 설치 스크립트, 운영은 체인별 데모 모드 지원",
            "- 발표자료 16장(발표자 노트 포함), 10분 발표·시연 영상(자막·내레이션), GitHub Pages 포트폴리오, README 정비"],
        7: ["- 국내 수집 서버 상시 운영(서버 확보 필요)", "- 영상 파일 Git LFS 또는 Release 이관"],
        8: ["- 배포 구성도·환경 변수 명세·CI/CD 설계·운영 검증 결과·결과물 목록 작성(산출물 04)",
            "- 영상 movpick_final.mp4(10:00, 1080p30, 약 67MB), 하이라이트 60초, 자막(SRT) 공개"],
        9: ["- 최종 점검: 테스트 계정 2종(일반 회원·읽기 전용 관리자) 비교 시연 흐름 확정",
            "- 한계(좌석 추정값, CGV 국내 수집기 필요, 단일 워커)를 발표와 문서에 명시하기로 합의"],
        10: ["- Render 무료 티어의 유휴 슬립(첫 요청 지연)과 메모리 제약", "- CGV 실데이터는 국내 수집 환경이 있어야 상시 갱신 가능"],
        11: ["- 국내 원격 수집기 상시 운영(국내 클라우드/서버리스)", "- 다중 워커 확장(Redis Pub/Sub), Alembic 마이그레이션, 데이터 갱신 지연 알림"],
        12: ["고도화 — 국내 수집기 상시 운영으로 CGV 실데이터 전환, 실시간 알림 수평 확장, 좌석 선호 기반 개인화 추천"],
    },
}


def para_xml(text: str, para_pr: str, char_pr: str) -> str:
    return (f'<hp:p id="0" paraPrIDRef="{para_pr}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{char_pr}"><hp:t>{html.escape(text, quote=False)}</hp:t></hp:run></hp:p>')


def fill_journal(path: Path, rows: dict) -> None:
    rows = {**COMMON, **rows}
    with zipfile.ZipFile(path) as z:
        items = {n: z.read(n) for n in z.namelist()}
        infos = {i.filename: i for i in z.infolist()}
    xml = items["Contents/section0.xml"].decode("utf-8")

    def repl(m):
        tc = m.group(0)
        a = re.search(r'<hp:cellAddr colAddr="(\d+)" rowAddr="(\d+)"', tc)
        col, row = int(a.group(1)), int(a.group(2))
        target = (row in (1, 2) and col == 2) or (3 <= row <= 12 and col == 1)
        if not target or row not in rows:
            return tc
        if re.search(r"<hp:t>[^<]+</hp:t>", tc):  # 이미 내용이 있으면 보존
            return tc
        p = re.search(r'<hp:p id="0" paraPrIDRef="(\d+)"[^>]*><hp:run charPrIDRef="(\d+)"', tc)
        body = "".join(para_xml(t, p.group(1), p.group(2)) for t in rows[row])
        return re.sub(r"(<hp:subList[^>]*>).*?(</hp:subList>)", lambda s: s.group(1) + body + s.group(2), tc, count=1, flags=re.S)

    xml = re.sub(r"<hp:tc .*?</hp:tc>", repl, xml, flags=re.S)
    items["Contents/section0.xml"] = xml.encode("utf-8")
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w") as z:
        for name, data in items.items():  # mimetype 은 첫 항목·무압축 유지
            z.writestr(infos[name], data, compress_type=zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED)
    tmp.replace(path)


# ============================================================================ 산출물 원고 (HTML)
CSS = """<style>
body{font-family:'맑은 고딕';font-size:10pt;line-height:160%}
h1{font-size:20pt;text-align:center} h2{font-size:14pt;color:#1f3a5f;border-bottom:1px solid #1f3a5f} h3{font-size:11.5pt}
table{border-collapse:collapse;width:100%} th,td{border:1px solid #666;padding:3px 5px;font-size:9.5pt;vertical-align:top}
th{background:#dfe6f0} .meta td{background:#f6f7fa}
</style>"""


CELL = "font-family:'맑은 고딕';font-size:9.5pt;text-align:left"


def table(head, rows):
    # 한글 HTML 가져오기는 CSS 를 대부분 무시하므로 열 너비·배경·정렬을 속성으로 지정 (너비는 내용 길이 비례)
    cols = len(head)
    avg = [sum(len(re.sub("<[^>]+>", "", str(r[i]))) for r in [head, *rows]) / (len(rows) + 1) for i in range(cols)]
    weight = [min(max(a, 9), 55) for a in avg]
    widths = [round(w * 100 / sum(weight)) for w in weight]
    h = "".join(f'<th bgcolor="#DCE4EF" align="left" width="{w}%" style="{CELL};font-weight:bold">{c}</th>' for c, w in zip(head, widths))
    b = "".join("<tr>" + "".join(f'<td align="left" valign="top" width="{w}%" style="{CELL}">{c}</td>' for c, w in zip(r, widths)) + "</tr>" for r in rows)
    return f'<table border="1" cellspacing="0" cellpadding="4" width="100%">{"<tr>" + h + "</tr>"}{b}</table><p></p>'


def ul(items):
    return "".join(f'<p align="left" style="{CELL};font-size:10pt">· {i}</p>' for i in items) + "<p></p>"


def doc(title, stage, period, sections):
    meta = table(["항목", "내용"], [["프로젝트", TOPIC], ["단계", stage], ["기간", period], ["작성", "3조 · " + TEAM],
                                   ["서비스", "https://movpick.onrender.com (API: https://movpick-api.onrender.com/docs)"],
                                   ["저장소", "https://github.com/fsclass-n/movpick"]])
    body = "".join(f'<h2><font face="맑은 고딕" color="#1F3A5F">{h}</font></h2>{c}' for h, c in sections)
    body = body.replace("<p>", f'<p align="left" style="{CELL};font-size:10pt">')
    return (f"<html><head><meta charset='utf-8'>{CSS}</head><body><h1 align='center'><font face='맑은 고딕'>{title}</font></h1>"
            f"{meta}{body}</body></html>")


P1 = doc("01. 기획·분석 산출물", "1단계 기획·분석", "2026년 11월 05일(목) ~ 11월 06일(금)", [
    ("1. 프로젝트 개요", "<p>멀티플렉스 3사(CGV·메가박스·롯데시네마)의 상영 시간표와 잔여석을 RPA로 자동 수집·동기화하고, 좌석을 '명당 점수'로 평가하여 "
     "감시 중인 명당 자리에 취소표가 생기면 실시간으로 알려 주는 지능형 티켓팅 보조 플랫폼이다.</p>"
     + table(["구분", "내용"], [["핵심 가치", "명당 자리가 비는 순간, 가장 먼저 알려드린다"], ["대상 사용자", "선호 좌석(명당)을 원하는 영화 관람객, 운영 관리자"],
                               ["범위", "3사 6개 지점(강남·용산아이파크몰 / 코엑스·강남 / 월드타워·가산디지털), 오늘·내일 상영분"],
                               ["주기", "상영 시간표 30분, 좌석 감시 20초"]])),
    ("2. 배경 및 문제 정의", table(["문제", "현상", "해결 방향"], [
        ["반복 새로고침", "명당 자리는 매진 후 취소표로 풀리지만 시점 예측 불가", "서버가 좌석 변동을 감시하고 알림"],
        ["정보 파편화", "체인마다 다른 앱·웹, 같은 영화를 세 번 검색", "3사 시간표를 하나의 화면으로 통합"],
        ["잔여석 숫자만 제공", "목록에서 명당 여부를 알 수 없음", "잔여석 수 기반 좌석 배치 재구성 + 명당 점수"]])),
    ("3. 목표", ul(["3사 상영 시간표·잔여석 자동 동기화(30분 주기)", "명당 자리 하이라이트·히트맵·추천 좌석 제공",
                   "명당 감시 등록 후 취소표 발생 시 실시간 팝업·웹훅 알림", "일반 회원·관리자 권한 분리와 관리자 백오피스",
                   "반응형(PC·태블릿·모바일) 시네마틱 다크 UI, OAuth 소셜 로그인과 테스트 계정 간편 로그인"])),
    ("4. 기능 요구사항", table(["ID", "구분", "요구사항", "우선순위"], [
        ["FR-01", "회원", "이메일 가입·로그인, 비밀번호 규칙(영문 대·소문자+숫자+특수문자 8자 이상)", "상"],
        ["FR-02", "회원", "Google·Naver·Kakao OAuth 로그인", "중"], ["FR-03", "회원", "일반 회원/시스템 관리자 테스트 계정 원클릭 로그인", "상"],
        ["FR-04", "상영작", "3사 상영작·회차·잔여석 조회, 날짜·체인 필터, 검색", "상"],
        ["FR-05", "좌석", "좌석 배치도, 명당 하이라이트, 히트맵, 추천 좌석", "상"],
        ["FR-06", "알림", "명당 전체/선택 좌석 감시 등록, 취소표 발생 시 WebSocket 팝업·토스트", "상"],
        ["FR-07", "알림", "텔레그램·디스코드·이메일 웹훅 알림 채널", "중"],
        ["FR-08", "관리자", "크롤러 주기 설정·수동 실행·성공/실패 로그 모니터링", "상"],
        ["FR-09", "관리자", "회원 목록 조회와 일반 ⇄ 관리자 실시간 권한 변경", "상"],
        ["FR-10", "공통", "반응형 GNB(햄버거↔X 애니메이션, 우측 Drawer), To-Top 버튼", "중"]])),
    ("5. 비기능 요구사항", table(["ID", "항목", "요구사항"], [
        ["NFR-01", "보안", "JWT 인증, bcrypt 해시, 서버 측 권한 검사, 비밀 값 .env 관리(저장소 미포함)"],
        ["NFR-02", "가용성", "사이트 구조 변경·차단 시에도 서비스 지속(모의 데이터 폴백, 실데이터 보호)"],
        ["NFR-03", "성능", "좌석 변동 → 사용자 알림 수 초 이내"], ["NFR-04", "배포", "프런트/백엔드 독립 배포, Docker 이미지에 Chromium 포함"],
        ["NFR-05", "호환성", "PC·태블릿·모바일 반응형, 주요 브라우저 지원"], ["NFR-06", "투명성", "추정값·데모 데이터는 화면에 명시"]])),
    ("6. 수집 대상 조사", table(["체인", "지점", "데이터 경로", "조사 결과"], [
        ["메가박스", "코엑스·강남", "schedulePage.do (POST, JSON)", "회차·잔여석(restSeatCnt)·총좌석·포스터 제공, 일반 요청으로 수집 가능"],
        ["롯데시네마", "월드타워·가산디지털", "TicketingData.aspx (POST, JSON)", "회차·잔여석(BookingSeatCount)·총좌석 제공, 응답에 중복 회차 존재"],
        ["CGV", "강남·용산아이파크몰", "booking/searchMovScnInfo (GET, JSON)", "일반 요청 403(WAF) — 브라우저 컨텍스트 또는 헤더 조건 필요"]])
     + "<p>공통 한계: 세 영화관 모두 좌석 단위 점유 정보가 아닌 '잔여석 수'만 공개한다 → 좌석 배치는 추정값으로 제공한다.</p>"),
    ("7. 기술 스택 선정", table(["영역", "선택", "근거"], [
        ["Frontend", "React 19 · Vite 6 · Tailwind CSS v4", "좌석 맵·실시간 상태 컴포넌트화, 디자인 토큰 일원화"],
        ["Backend", "Python 3.11 · FastAPI · WebSocket", "비동기·WebSocket 기본 지원, Pydantic 검증, 자동 API 문서"],
        ["DB", "TiDB Cloud(MySQL 호환)", "로컬·운영 동일 DB로 환경 차이 제거, TLS"],
        ["RPA·데이터", "Playwright · Requests · BeautifulSoup4 · NumPy · pandas · Plotly", "가벼운 HTTP 우선, 차단 시 실제 브라우저, 점수 연산·집계·리포트"],
        ["Infra", "Docker · Render · Netlify · GitHub Actions", "빌드 타임 Chromium 설치, 독립 배포, CI 품질 게이트"]])),
    ("8. 일정 계획", table(["단계", "기간", "주요 산출물"], [
        ["1단계 기획·분석", "11/05 ~ 11/06", "요구사항 정의서, 수집 대상 조사표, 기술 스택 선정서"],
        ["2단계 설계", "11/09 ~ 11/10", "아키텍처·DB·API·알고리즘·화면 설계서"],
        ["3단계 구현", "11/11 ~ 11/18", "소스 코드, 자동 테스트, 구현 보고서"],
        ["4단계 배포", "11/19 ~ 11/23", "배포 환경, CI/CD, 발표자료·시연 영상·포트폴리오"]])),
    ("9. 위험 요소 및 대응", table(["위험", "영향", "대응"], [
        ["수집 대상 사이트 구조 변경·차단", "데이터 공백", "체인별 어댑터 분리, 실패 격리, 모의 데이터 폴백, 실데이터 보호"],
        ["좌석 단위 데이터 부재", "명당 판단 근거 부족", "잔여석 수 기반 배치 재구성 + 추정값 표기"],
        ["무료 서버 제약(메모리·슬립)", "응답 지연", "브라우저 기동 최소화(HTTP 우선), 경량 이미지"],
        ["테스트 계정 공개", "데이터 변조", "관리자 테스트 계정 읽기 전용"]])),
])

P2 = doc("02. 설계 산출물", "2단계 설계", "2026년 11월 09일(월) ~ 11월 10일(화)", [
    ("1. 시스템 아키텍처", "<p>프런트엔드(정적 CDN) · 백엔드 API(Docker 컨테이너) · 클라우드 DB를 분리 배포한다. 수집 루프와 좌석 모니터는 API 프로세스 안의 "
     "asyncio 백그라운드 작업으로 동작하며(단일 워커), 동기 크롤러는 asyncio.to_thread 로 실행해 WebSocket 이벤트 루프를 막지 않는다.</p>"
     + table(["구성 요소", "역할", "기술"], [
         ["Client", "상영작·좌석 맵·감시·관리자 화면, WebSocket 수신", "React 19 · Vite · Tailwind v4 (Netlify · Render Static)"],
         ["REST API", "인증·상영작·좌석·감시·관리자·통계", "FastAPI · SQLAlchemy 2 · Pydantic · JWT"],
         ["Crawler Loop", "30분마다 3사 오늘·내일 수집 → 정제 → 적재", "asyncio · rpa 패키지"],
         ["Seat Monitor", "20초마다 좌석 변동 감지 → 알림 대상 산출", "asyncio · NumPy"],
         ["WebSocket Hub", "사용자별 연결 관리·이벤트 전송", "FastAPI WebSocket"],
         ["Ingest API", "원격 수집기 데이터 수신(토큰 인증)", "/api/rpa/ingest"],
         ["Notifier", "웹훅 알림", "Telegram · Discord · SMTP"], ["DB", "영속 저장", "TiDB Cloud (MySQL 호환, TLS)"]])),
    ("2. 데이터베이스 설계", table(["테이블", "주요 컬럼", "제약·비고"], [
        ["users", "id, email, name, password_hash, role(user/admin), provider, provider_id, is_active, created_at, last_login_at", "email UNIQUE, (provider, provider_id) UNIQUE"],
        ["showtimes", "id, chain, external_id, theater, screen, movie_title, rating, start_at, end_at, total_seats, available_seats, seat_layout(JSON), source(real/mock), booking_url, poster_url, updated_at", "(chain, external_id) UNIQUE — 멱등 upsert"],
        ["seat_watches", "id, user_id, showtime_id, mode(prime/custom), seats(JSON), channels(JSON), active, last_notified_seats(JSON), created_at", "users·showtimes FK, 회차 삭제 시 함께 정리"],
        ["crawl_logs", "id, job, chain, status, source, items, duration_ms, message, trigger, started_at", "14일 보관"]])),
    ("3. API 명세", table(["그룹", "Method · Path", "설명", "권한"], [
        ["인증", "POST /api/auth/signup · /login · /demo/{user|admin}, GET /api/auth/me · /providers", "가입·로그인·테스트 로그인·내 정보", "공개 / 로그인"],
        ["OAuth", "GET /api/auth/oauth/{google|naver|kakao}/login · /callback", "state JWT 서명, 복귀 Origin 화이트리스트", "공개"],
        ["상영작", "GET /api/showtimes · /api/showtimes/{id} · /api/showtimes/{id}/seats · /api/movies · /api/chains", "시간표·좌석 배치·명당·추천", "공개"],
        ["통계", "GET /api/stats/booking-rates", "판매 좌석 기준 인기 순위·체인별 예매율", "공개"],
        ["감시", "GET·POST /api/watches, PATCH·DELETE /api/watches/{id}, GET /api/watches/channels", "명당/선택 좌석 감시", "로그인"],
        ["관리자", "GET /api/admin/users · /crawler · /crawler/logs · /reports/crawl · /summary, PATCH /users/{id}/role, PUT /crawler/config, POST /crawler/run · /crawler/probe", "크롤러·회원 관리", "관리자(쓰기는 읽기 전용 계정 403)"],
        ["수집 수신", "POST /api/rpa/ingest, GET /api/rpa/ping", "원격 수집기 데이터 수신", "X-RPA-Token"],
        ["실시간·운영", "WS /ws?token=, GET /health", "seat_alert·seat_update·role_changed, 배포 커밋 확인", "공개/로그인"]])),
    ("4. RPA 수집 파이프라인", ul([
        "스케줄러(30분, 오늘·내일) → 체인 어댑터 → 수집 → 정제(BS4 텍스트 정제·external_id 중복 제거) → 정합성 정책 → TiDB upsert → crawl_logs·WebSocket 전파",
        "수집 방식: 메가박스·롯데시네마 JSON(Requests), CGV 는 XHR 헤더 HTTP 우선 → 실패 시 Playwright(Headless Chromium) 브라우저 컨텍스트 fetch",
        "실패 격리: 체인·일자 단위로 예외를 처리해 한 곳의 장애가 전체를 멈추지 않음",
        "정합성 정책: 실데이터가 있으면 수집 실패 시에도 유지(TTL 180분 초과 시 '갱신 지연' 표시), 없으면 모의 데이터로 대체, 출처가 다른 데이터의 혼재 방지, 체인별 데모 모드"])),
    ("5. 명당 점수 · 좌석 추정 알고리즘", table(["단계", "내용"], [
        ["배치 크기", "총 좌석 수 기준 열 = √(좌석×1.6), 행 = ⌈좌석/열⌉, 정원을 맞추기 위해 뒷줄 양끝 좌석 제거"],
        ["명당 점수", "r0 = 0.62·(R−1), c0 = (C−1)/2, dr = |r−r0|/(R−1), dc = |c−c0|/(C−1), score = clip(1 − (1.6·dr + 1.4·dc)^1.2, 0, 1)"],
        ["명당 판정", "score 상위 18% 좌석, 추천은 현재 비어 있는 명당 중 상위 4석"],
        ["점유 분포", "가중 샘플링 (0.35 + score)³ — 명당부터 팔리는 현실적 분포"],
        ["재수집 보정", "새 잔여석 수에 맞춰 기존 배치를 최소 변경(reconcile)"],
        ["인기 순위", "예매율 왜곡(회차 수가 적은 영화) 방지를 위해 판매 좌석 수 합계 기준"]])),
    ("6. 실시간 알림 설계", ul([
        "좌석 모니터(20초): 감시 중 회차 + 표본 회차의 좌석 변동 반영(크롤링 사이 구간은 시뮬레이션)",
        "알림 대상 = 현재 빈 좌석 ∩ 감시 대상(명당 전체 또는 선택 좌석) − last_notified_seats → 새로 빈 좌석만 전송",
        "전송: 사용자별 WebSocket(seat_alert) → 팝업·토스트·브라우저 Notification, 선택 채널에 웹훅",
        "클라이언트: 25초 ping, 연결 끊김 시 지수 백오프 재연결"])),
    ("7. 권한 · 보안 설계", table(["역할", "권한", "생성 방식"], [
        ["일반 회원", "조회, 감시 등록·알림", "가입 · 소셜 로그인 · 테스트 로그인"],
        ["테스트 관리자", "관리자 화면 조회·수집 진단만 (쓰기 API 403)", "원클릭 테스트 로그인"],
        ["실제 관리자", "크롤러 실행·설정, 회원 권한 변경 (본인·환경 변수 관리자 강등 불가)", ".env ADMIN_EMAIL / ADMIN_PASSWORD"]])
     + ul(["비밀번호 bcrypt 해시, JWT(HS256), 비밀번호 정규식 서버·클라이언트 이중 검증",
           "OAuth state JWT 서명(10분 만료)·복귀 Origin 화이트리스트, CORS 허용 Origin 관리, 수신 API 토큰 상수 시간 비교"])),
    ("8. 화면 설계", table(["화면", "주요 구성"], [
        ["로그인/회원가입", "Split(좌: 오늘 인기 1위 포스터·예매율 / 우: 폼), 비밀번호 규칙 체크리스트, 테스트 계정·소셜 로그인 버튼"],
        ["상영작", "날짜·체인 필터, 검색, 영화별 카드(포스터·예매율·회차·잔여석)"],
        ["좌석 맵", "반응형 좌석 그리드, 명당 하이라이트, 히트맵, 추천 좌석, 감시 등록·알림 채널"],
        ["알림 설정", "감시 목록(켜기/끄기·삭제), 세션 알림 기록, 브라우저 알림 권한"],
        ["관리자", "지표 카드, 크롤러 상태·주기·실행, 수집 진단, 실행 로그, Plotly 리포트, 회원 권한"],
        ["공통", "시네마틱 다크 컬러 토큰, 타이틀/본문 서체 이원화, 햄버거↔X GNB, 우측 Drawer, 상용형 푸터, 원형 To-Top"]])),
])

P3 = doc("03. 구현 및 테스트 산출물", "3단계 구현", "2026년 11월 11일(수) ~ 11월 18일(수)", [
    ("1. 구현 범위", table(["영역", "구현 내용"], [
        ["백엔드", "FastAPI 앱(lifespan: DB 초기화·테스트/관리자 계정 동기화·백그라운드 루프), 인증·OAuth, 상영작·좌석·감시·관리자·통계·수신 API, /ws, /health"],
        ["RPA", "CGV(HTTP → Playwright)·메가박스·롯데시네마·Mock 어댑터, crawl_chain(auto/real/mock), CLI·원격 수집기(--push · --every)"],
        ["좌석 모델", "배치 재구성·명당 점수·재수집 보정·변동 시뮬레이션(NumPy)"],
        ["실시간", "WebSocket 허브(사용자별), 좌석 모니터 diff, 웹훅 알림"],
        ["프런트엔드", "Login · Home · Showtime · Alerts · Admin 페이지, Layout(GNB·Drawer·푸터·To-Top), Auth/Realtime/Toast 컨텍스트"],
        ["관리자", "크롤러 주기·실행·로그·수집 진단·Plotly 리포트, 회원 권한 변경, 읽기 전용 테스트 관리자"]])),
    ("2. 디렉터리 구조", table(["경로", "설명"], [
        ["backend/app/main.py", "앱 생성, CORS, 라우터, /ws, /health(배포 커밋)"], ["backend/app/config.py · db.py", "단일 .env 설정, TiDB(TLS)/SQLite 폴백"],
        ["backend/app/models.py · schemas.py", "ORM 모델 4종, 요청/응답 스키마"], ["backend/app/security.py", "JWT·bcrypt·비밀번호 규칙·require_admin(_write)"],
        ["backend/app/routers/", "auth · showtimes · watches · admin · rpa"], ["backend/app/services/", "crawler · monitor · notifier · ws"],
        ["backend/tests/", "pytest 24개"], ["rpa/adapters/ · seatmap.py · service.py · runner.py", "수집 어댑터, 좌석 모델, 수집 서비스, CLI"],
        ["frontend/src/", "pages · components · context · lib"], ["scripts/", "국내 VM 수집기 설치, Windows 수집기"]])),
    ("3. 핵심 로직 구현", ul([
        "CGV 어댑터: Referer·Origin·Sec-Fetch-* 헤더를 갖춘 HTTP 요청 → 403 시 Playwright 로 예매 페이지를 연 뒤 브라우저 컨텍스트에서 스케줄 API 호출, 차단 유형(cf-mitigated·cf-ray 거점) 진단 메시지",
        "persist(): external_id 중복 제거 → (chain, external_id) upsert → 좌석 배치 신규 생성 또는 reconcile → 실데이터 도착 시 같은 일자 모의 회차 정리 → crawl_logs 기록 → 1일 지난 회차 정리",
        "_crawl_one(): 데모 모드 → 원격 수집 체인 → 일반 수집 순서로 처리, 실패 시 실데이터 보호",
        "monitor._tick(): 감시 회차 좌석 변동 반영 → free_targets − last_notified → 알림 큐",
        "OAuth: 프록시 헤더를 반영한 요청 기준 redirect_uri, 결과는 루트(/#oauth_token)로 반환",
        "프런트: WebSocket 지수 백오프 재연결, seat_update 실시간 좌석 반영, 관리자 화면 읽기 전용 안내·자물쇠 표시"])),
    ("4. 테스트 결과", "<p>pytest 24개 전체 통과(임시 SQLite·RPA 비활성으로 운영 DB와 격리).</p>" + table(["테스트", "검증 내용", "결과"], [
        ["test_password_rule", "비밀번호 규칙 8가지 케이스", "통과"], ["test_seat_layout_matches_counts", "배치 정원·잔여석 일치, reconcile", "통과"],
        ["test_signup_login_flow", "약한 비밀번호 422, 중복 가입 409, 잘못된 비밀번호 401", "통과"],
        ["test_demo_login_and_admin_guard", "관리자 API 401/403/200", "통과"], ["test_demo_admin_is_read_only", "테스트 관리자 쓰기 403, .env 관리자 보호", "통과"],
        ["test_env_admin_rejects_weak_password", "규칙 위반·테스트 이메일 관리자 생성 거부", "통과"], ["test_role_change", "권한 변경·본인 강등 금지", "통과"],
        ["test_showtimes_seats_watch_and_alert", "감시 등록 → 좌석 비움 → 알림 대상 산출", "통과"],
        ["test_remote_ingest_replaces_mock", "수신 API 404/401/200, 모의 데이터 정리, ping", "통과"],
        ["test_crawler_keeps_fresh_real_data", "수집 실패 시 실데이터 유지·갱신 지연 표시·원격 체인", "통과"],
        ["test_mock_chain_replaces_real_and_rejects_ingest", "데모 모드 전환·수신 거부(409)", "통과"],
        ["test_persist_dedupes_duplicate_items", "중복 회차 제거", "통과"], ["test_oauth_redirect_uri_follows_request_host", "redirect_uri 생성 규칙", "통과"],
        ["test_stats_and_ws", "통계 API, WebSocket hello/ping/pong", "통과"]])
     + ul(["E2E(Playwright): 감시 등록 후 좌석 비움 → 브라우저 팝업 4.7초 실측",
           "화면 검증: 390·900·1440·1920px 캡처로 반응형 확인, 콘솔 오류 없음"])),
    ("5. 트러블슈팅 기록", table(["문제", "원인", "해결"], [
        ["크롤링 루프 전체 중단", "롯데시네마 응답의 중복 회차 → UNIQUE 위반", "적재 전 중복 제거, 체인·일자 단위 실패 격리"],
        ["로그 시각 9시간 차이", "DB now() 기본값이 UTC", "앱에서 로컬 시각 기록, 컨테이너 TZ=Asia/Seoul"],
        ["CGV 403", "WAF가 브라우저 XHR 형태가 아닌 요청 차단", "헤더 조건 HTTP 우선 → Playwright 폴백"],
        ["관리자 로그인 후 홈으로 이동", "React Router 전환과 상태 갱신 경합", "직접 로그인 시 수동 이동 플래그"],
        ["OAuth 콜백 중복 처리", "StrictMode 이펙트 2회 실행", "ref 가드"], ["Tailwind @apply 오류", "v4는 사용자 클래스에 @utility 필요", "@utility 로 전환"],
        ["실데이터·모의 데이터 혼재", "수집 실패 시 모의 회차 추가", "출처별 정리 정책 + 실데이터 보호"]])),
])

P4 = doc("04. 배포 산출물", "4단계 배포", "2026년 11월 19일(목) ~ 11월 23일(월)", [
    ("1. 배포 구성", table(["구분", "주소", "플랫폼"], [
        ["운영 프런트엔드", "https://movpick.onrender.com", "Render Static (SPA 리라이트 /* → /index.html)"],
        ["스테이징 프런트엔드", "https://movpick.netlify.app", "Netlify (_redirects)"], ["백엔드 API", "https://movpick-api.onrender.com (/docs, /health)", "Render Docker"],
        ["데이터베이스", "TiDB Cloud 클러스터 movpick", "MySQL 호환 · TLS"], ["포트폴리오", "https://fsclass-n.github.io/movpick/", "GitHub Pages"],
        ["저장소", "https://github.com/fsclass-n/movpick", "GitHub"]])),
    ("2. 컨테이너 · 인프라", ul([
        "Dockerfile: python:3.11-slim-bookworm(Playwright 의존성 호환) + playwright install --with-deps chromium(빌드 타임), TZ=Asia/Seoul, 단일 워커 uvicorn(--proxy-headers)",
        "INSTALL_BROWSER=false 빌드 인자로 국내 수집기 전용 경량 이미지 생성",
        "docker-compose: backend · frontend(nginx) · cgv-collector(profile collector, 30분 상주 수집)",
        "render.yaml(Blueprint) · netlify.toml · .gitattributes(LF 고정) · .dockerignore"])),
    ("3. CI/CD", table(["워크플로", "작업", "내용"], [
        ["ci.yml", "backend", "pytest 24개 (RPA 비활성 · 임시 DB)"], ["ci.yml", "frontend", "npm ci · vite build"],
        ["ci.yml", "docker", "API 이미지 + 경량 수집기 이미지 빌드, 컨테이너 /health 기동 점검"], ["ci.yml", "deploy", "Render/Netlify 배포 훅(시크릿 설정 시)"],
        ["pages.yml", "deploy", "포트폴리오(index.html · 영상 · 썸네일) 배포"], ["cgv-collector.yml", "collect", "국내 self-hosted 러너 지정 시 30분 수집"]])
     + "<p>Render·Netlify 는 Git 연동 자동 배포, 배포 버전은 /health 응답의 commit 해시로 확인한다.</p>"),
    ("4. 환경 변수 명세 (값은 저장소에 포함하지 않음)", table(["그룹", "키", "설명"], [
        ["앱", "APP_ENV, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES", "JWT 서명 키 등"], ["주소", "FRONTEND_ORIGINS, FRONTEND_URL, BACKEND_URL", "CORS·OAuth 복귀·콜백"],
        ["DB", "DATABASE_URL 또는 TIDB_HOST/PORT/USER/PASSWORD/DB_NAME, TIDB_SSL_CA", "미설정 시 SQLite"],
        ["OAuth", "GOOGLE/NAVER/KAKAO_CLIENT_ID · _CLIENT_SECRET", "소셜 로그인"], ["관리자", "DEMO_LOGIN_ENABLED, ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NAME", "테스트 계정·실제 관리자"],
        ["RPA", "RPA_ENABLED, RPA_MODE, RPA_HEADLESS, RPA_TIMEOUT_SECONDS, CRAWL_INTERVAL_MINUTES, SEAT_MONITOR_INTERVAL_SECONDS, SEAT_SIMULATION", "수집·감시"],
        ["원격 수집", "RPA_PROXY_URL, RPA_INGEST_TOKEN, RPA_REMOTE_CHAINS, RPA_MOCK_CHAINS, RPA_REAL_TTL_MINUTES", "국외 IP 차단 대응·데모 모드"],
        ["알림", "TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DISCORD_WEBHOOK_URL, SMTP_*", "웹훅 채널"], ["프런트", "VITE_API_URL", "빌드 시 API 주소"]])),
    ("5. 운영 검증 결과", table(["항목", "결과"], [
        ["/health", "status ok, db mysql(TiDB), 배포 커밋 해시 일치"], ["CORS", "Netlify·Render 프런트 Origin 허용 확인"],
        ["WebSocket", "wss 연결 hello · ping/pong 확인, 실시간 취소표 알림 수신"], ["RBAC", "테스트 관리자 쓰기 API 403 확인"],
        ["OAuth", "Google 콜백 URL 운영 주소로 생성·로그인 성공, 결과 루트 경로 복귀"], ["SPA 라우팅", "Render Static 리라이트 후 딥링크 정상"],
        ["수집", "메가박스·롯데시네마 서버 직접 수집 성공, CGV 는 국외 IP 차단(PDX) 확인"]])),
    ("6. 운영 이슈 및 조치", table(["이슈", "조치"], [
        ["Docker 빌드 실패(Debian 13)", "slim-bookworm 고정, CI 러너 ubuntu-24.04 고정"], ["Render Dockerfile 경로", "루트 Dockerfile 로 이동"],
        ["redirect_uri_mismatch", "프록시 반영 요청 주소 기준 콜백 생성"], ["소셜 로그인 후 404", "루트(/#oauth_token) 복귀 + 리라이트 규칙"],
        ["CGV 국외 IP 차단", "cf-ray 거점 비교로 규명 → 원격 수집기·토큰 인증 수신 API·국내 VM 설치 스크립트·데모 모드"]])),
    ("7. 결과물", table(["결과물", "위치"], [
        ["발표자료(16장, 발표자 노트)", "docs/프로젝트_발표자료.pptx"], ["10분 발표·시연 영상", "docs/video/movpick_final.mp4 (10:00, 1080p30, 약 67MB)"],
        ["60초 하이라이트 · 자막", "docs/video/movpick_highlight.mp4 · movpick_final.srt"], ["영상 대본·연출 가이드", "docs/video/영상_대본_및_연출가이드.md"],
        ["포트폴리오", "https://fsclass-n.github.io/movpick/"], ["개발 문서", "README.md · docs/DEVELOPMENT.md"]])),
    ("8. 한계 및 향후 계획", ul(["좌석 단위 배치는 잔여석 수 기반 추정값(화면 표기)", "CGV 실데이터 상시 갱신을 위해 국내 수집 서버 필요",
                              "단일 워커 구조 → Redis Pub/Sub 기반 다중 워커 WebSocket 확장, Alembic 마이그레이션", "데이터 갱신 지연 알림, 좌석 선호 기반 개인화 추천"])),
])

OUTPUTS = {"01_기획분석_산출물.hwpx": P1, "02_설계_산출물.hwpx": P2, "03_구현_산출물.hwpx": P3, "04_배포_산출물.hwpx": P4}


# ============================================================================ 한글 자동화
def hwp_app():
    h = win32.Dispatch("HWPFrame.HwpObject")
    if not h.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule"):
        raise SystemExit("한글 보안 모듈 등록 실패 (HKCU\\Software\\HNC\\HwpAutomation\\Modules 확인)")
    h.XHwpWindows.Item(0).Visible = False
    return h


def main() -> None:
    OUT_PDF.mkdir(exist_ok=True)
    for name, rows in JOURNAL.items():
        fill_journal(DOCS / name, rows)
        print("filled", name)
    h = hwp_app()
    try:
        tmp = Path(tempfile.mkdtemp())
        for name, html_doc in OUTPUTS.items():
            src = tmp / (Path(name).stem + ".html")
            src.write_text(html_doc, encoding="utf-8")
            assert h.Open(str(src), "HTML", "forceopen:true;code:utf8")
            assert h.SaveAs(str(DOCS / "산출물" / name), "HWPX", "")
            assert h.SaveAs(str(OUT_PDF / (Path(name).stem + ".pdf")), "PDF", "")
            print("output", name, "pages", h.PageCount)
            h.Clear(1)
        for name in JOURNAL:
            assert h.Open(str(DOCS / name), "HWPX", "forceopen:true")
            assert h.SaveAs(str(DOCS / name), "HWPX", "")  # 한글로 다시 저장해 줄 배치 정보 갱신
            assert h.SaveAs(str(OUT_PDF / (Path(name).stem + ".pdf")), "PDF", "")
            print("journal", name, "pages", h.PageCount)
            h.Clear(1)
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        h.Quit()


if __name__ == "__main__":
    main()
