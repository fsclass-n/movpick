from datetime import date

import requests
from bs4 import BeautifulSoup

from ..models import ShowtimeData
from .base import USER_AGENT, BaseAdapter, CrawlError, parse_hm

ENDPOINT = "https://www.megabox.co.kr/on/oh/ohc/Brch/schedulePage.do"
BRANCHES = ["1351", "1372"]  # 코엑스, 강남


def clean(text: str | None) -> str:
    """HTML 엔티티/태그가 섞인 상영관·영화명 정제"""
    return BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)


class MegaboxAdapter(BaseAdapter):
    chain = "megabox"
    label = "메가박스"

    def fetch(self, day: date) -> list[ShowtimeData]:
        de = day.strftime("%Y%m%d")
        items: list[ShowtimeData] = []
        with requests.Session() as s:
            s.proxies.update(self.requests_proxies or {})
            s.headers.update({"User-Agent": USER_AGENT, "Referer": "https://www.megabox.co.kr/"})
            for brch in BRANCHES:
                body = {"masterType": "brch", "detailType": "area", "brchNo": brch, "firstAt": "Y",
                        "brchNo1": brch, "crtDe": de, "playDe": de}
                res = s.post(ENDPOINT, json=body, timeout=self.timeout)
                res.raise_for_status()
                for m in (res.json().get("megaMap") or {}).get("movieFormList") or []:
                    poster = m.get("moviePosterImg")
                    items.append(ShowtimeData(
                        chain=self.chain,
                        external_id=f"{m['playSchdlNo']}",
                        theater=f"메가박스 {clean(m.get('brchNm'))}".strip(),
                        screen=clean(m.get("theabExpoNm")),
                        movie_title=clean(m.get("movieNm")),
                        rating=m.get("admisClassCdNm"),
                        start_at=parse_hm(day, m["playStartTime"]),
                        end_at=parse_hm(day, m["playEndTime"]) if m.get("playEndTime") else None,
                        total_seats=int(m.get("totSeatCnt") or 0),
                        available_seats=int(m.get("restSeatCnt") or 0),
                        poster_url=f"https://www.megabox.co.kr{poster}" if poster else None,
                        booking_url=f"https://www.megabox.co.kr/booking?brchNo={brch}&playDe={de}",
                    ))
        if not items:
            raise CrawlError("메가박스 상영 시간표가 비어 있습니다.")
        return items
