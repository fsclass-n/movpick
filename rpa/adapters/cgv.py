import re
from datetime import date, datetime

import requests

from ..models import ShowtimeData
from .base import USER_AGENT, BaseAdapter, CrawlError, parse_hm

BOOKING_PAGE = "https://cgv.co.kr/cnm/movieBook"
SCHEDULE_API = "https://cgv.co.kr/api/v1/booking/searchMovScnInfo?coCd=A420&siteNo={site}&scnYmd={de}&rtctlScopCd=08"
POSTER_BASE = "https://cdn.cgv.co.kr/cgvpomsfilm/Movie/Thumbnail/Poster/"
POSTER_SIZE = re.compile(r"_\d+\.jpg$")  # API 가 주는 _185 는 CDN 미제공 → _320 사용
SITES = ["0056", "0013"]  # 강남, 용산아이파크몰

# Cloudflare WAF 는 브라우저 XHR 형태(Referer/Origin/Sec-Fetch-*)가 아닌 요청을 403 으로 차단
XHR_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": BOOKING_PAGE,
    "Origin": "https://cgv.co.kr",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}

FETCH_JS = """async (urls) => Promise.all(urls.map(async (u) => {
  const r = await fetch(u, { headers: { Accept: 'application/json' } });
  return { status: r.status, body: r.ok ? await r.json() : null };
}))"""


def block_reason(headers, body: str) -> str:
    """Cloudflare 차단 유형 진단: challenge(JS 챌린지) / block(WAF 규칙) + 페이지 제목"""
    title = re.search(r"<title>([^<]{0,80})", body or "", re.I)
    parts = [f"cf-mitigated={headers.get('cf-mitigated')}" if headers.get("cf-mitigated") else "",
             f"ray={headers.get('cf-ray', '')[-3:]}" if headers.get("cf-ray") else "",
             f"title={title.group(1).strip()}" if title else ""]
    return f" ({', '.join(p for p in parts if p)})" if any(parts) else ""


class CgvAdapter(BaseAdapter):
    """CGV 스케줄 API (Cloudflare WAF).
    1차: 브라우저 XHR 헤더를 갖춘 HTTP 요청 (가볍고 빠름)
    2차: 차단 시 Playwright Headless Chromium 으로 예매 페이지를 연 뒤 브라우저 컨텍스트에서 API 호출"""

    chain = "cgv"
    label = "CGV"

    def fetch(self, day: date) -> list[ShowtimeData]:
        de = day.strftime("%Y%m%d")
        urls = [SCHEDULE_API.format(site=s, de=de) for s in SITES]
        try:
            responses = self._fetch_http(urls)
            self.via = "http"
        except CrawlError as http_error:
            try:
                responses = self._fetch_browser(urls)
                self.via = "playwright"
            except CrawlError as e:
                raise CrawlError(f"{http_error} / {e}") from e
        items = [self._item(m, de) for res in responses for m in (res.get("data") or [])]
        if not items:
            raise CrawlError("CGV 상영 시간표가 비어 있습니다.")
        return items

    def _fetch_http(self, urls: list[str]) -> list[dict]:
        out = []
        with requests.Session() as s:
            s.headers.update(XHR_HEADERS)
            s.proxies.update(self.requests_proxies or {})
            for u in urls:
                res = s.get(u, timeout=self.timeout)
                if res.status_code != 200:
                    raise CrawlError(f"HTTP 수집 차단: {res.status_code}{block_reason(res.headers, res.text)}")
                out.append(res.json())
        return out

    def _fetch_browser(self, urls: list[str]) -> list[dict]:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless, proxy=self.playwright_proxy,
                                            args=["--no-sandbox", "--disable-dev-shm-usage"])
                page = browser.new_page(user_agent=USER_AGENT, locale="ko-KR")
                page.goto(BOOKING_PAGE, timeout=self.timeout * 1000, wait_until="domcontentloaded")
                responses = page.evaluate(FETCH_JS, urls)
                browser.close()
        except PlaywrightError as e:
            raise CrawlError(f"Playwright 오류: {str(e).splitlines()[0]}") from e
        for res in responses:
            if res["status"] != 200 or not res["body"]:
                raise CrawlError(f"Playwright 수집 차단: HTTP {res['status']}")
        return [r["body"] for r in responses]

    def _item(self, m: dict, de: str) -> ShowtimeData:
        scn_day = datetime.strptime(m.get("scnYmd") or de, "%Y%m%d").date()
        poster = m.get("physcFilePathnm")
        return ShowtimeData(
            chain=self.chain,
            external_id=f"{m['siteNo']}-{m['scnYmd']}-{m['scnsNo']}-{m['scnSseq']}",
            theater=m.get("siteNm") or f"CGV {m.get('siteNo')}",
            screen=m.get("expoScnsNm") or m.get("scnsNm") or "",
            movie_title=m.get("movNm") or m.get("prodNm") or "",
            rating=m.get("cratgClsNm"),
            start_at=parse_hm(scn_day, m["scnsrtTm"]),
            end_at=parse_hm(scn_day, m["scnendTm"]) if m.get("scnendTm") else None,
            total_seats=int(m.get("stcnt") or 0),
            available_seats=int(m.get("frSeatCnt") or 0),
            poster_url=POSTER_BASE + POSTER_SIZE.sub("_320.jpg", poster) if poster else None,
            booking_url=BOOKING_PAGE,
        )
