from datetime import date, datetime

from ..models import ShowtimeData
from .base import USER_AGENT, BaseAdapter, CrawlError, parse_hm

BOOKING_PAGE = "https://cgv.co.kr/cnm/movieBook"
SCHEDULE_API = "https://cgv.co.kr/api/v1/booking/searchMovScnInfo?coCd=A420&siteNo={site}&scnYmd={de}&rtctlScopCd=08"
SITES = ["0056", "0013"]  # 강남, 용산아이파크몰

FETCH_JS = """async (urls) => Promise.all(urls.map(async (u) => {
  const r = await fetch(u, { headers: { Accept: 'application/json' } });
  return { status: r.status, body: r.ok ? await r.json() : null };
}))"""


class CgvAdapter(BaseAdapter):
    """CGV 스케줄 API는 WAF로 일반 HTTP 요청을 차단(403)하므로,
    Playwright Headless Chromium으로 예매 페이지를 연 뒤 브라우저 컨텍스트 안에서 API를 호출한다."""

    chain = "cgv"
    label = "CGV"

    def fetch(self, day: date) -> list[ShowtimeData]:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright

        de = day.strftime("%Y%m%d")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless, proxy=self.playwright_proxy,
                                            args=["--no-sandbox", "--disable-dev-shm-usage"])
                page = browser.new_page(user_agent=USER_AGENT, locale="ko-KR")
                page.goto(BOOKING_PAGE, timeout=self.timeout * 1000, wait_until="domcontentloaded")
                responses = page.evaluate(FETCH_JS, [SCHEDULE_API.format(site=s, de=de) for s in SITES])
                browser.close()
        except PlaywrightError as e:
            raise CrawlError(f"Playwright 오류: {str(e).splitlines()[0]}") from e

        items: list[ShowtimeData] = []
        for site, res in zip(SITES, responses):
            if res["status"] != 200 or not res["body"]:
                raise CrawlError(f"CGV {site} 응답 오류: HTTP {res['status']}")
            for m in res["body"].get("data") or []:
                scn_day = datetime.strptime(m.get("scnYmd") or de, "%Y%m%d").date()
                items.append(ShowtimeData(
                    chain=self.chain,
                    external_id=f"{m['siteNo']}-{m['scnYmd']}-{m['scnsNo']}-{m['scnSseq']}",
                    theater=m.get("siteNm") or f"CGV {site}",
                    screen=m.get("expoScnsNm") or m.get("scnsNm") or "",
                    movie_title=m.get("movNm") or m.get("prodNm") or "",
                    rating=m.get("cratgClsNm"),
                    start_at=parse_hm(scn_day, m["scnsrtTm"]),
                    end_at=parse_hm(scn_day, m["scnendTm"]) if m.get("scnendTm") else None,
                    total_seats=int(m.get("stcnt") or 0),
                    available_seats=int(m.get("frSeatCnt") or 0),
                    booking_url=BOOKING_PAGE,
                ))
        if not items:
            raise CrawlError("CGV 상영 시간표가 비어 있습니다.")
        return items
