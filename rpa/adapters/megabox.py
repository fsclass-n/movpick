from datetime import date

import requests
from bs4 import BeautifulSoup

from ..models import ShowtimeData
from .base import USER_AGENT, BaseAdapter, CrawlError, parse_hm

ENDPOINT = "https://www.megabox.co.kr/on/oh/ohb/SimpleBooking/selectBokdList.do"
BOOKING_URL = "https://www.megabox.co.kr/booking?brchNo={brch}&playDe={de}"

# selectBokdList.do 의 areaBrchList.areaCdNm → 지역 코드 (서울·경기 전 지점 수집)
AREA_TO_REGION = {"서울": "seoul", "경기": "gyeonggi"}

# 지점 목록 조회 실패 시 사용하는 대표 지점
FALLBACK_BRANCHES = [
    ("10", "1351", "seoul"),     # 코엑스
    ("10", "1372", "seoul"),     # 강남
    ("10", "1211", "seoul"),     # 상암월드컵경기장
    ("30", "4121", "gyeonggi"),  # 고양스타필드
    ("30", "4451", "gyeonggi"),  # 동탄
    ("30", "4651", "gyeonggi"),  # 하남스타필드
]


def clean(text: str | None) -> str:
    """HTML 엔티티/태그가 섞인 상영관·영화명 정제"""
    return BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)


def _body(area: str, brch: str, de: str) -> dict:
    return {"masterType": "brch", "detailType": "area", "areaCode": area,
            "brchNo": brch, "brchNo1": brch, "firstAt": "N", "crtDe": de, "playDe": de}


class MegaboxAdapter(BaseAdapter):
    chain = "megabox"
    label = "메가박스"

    def _branches(self, s: requests.Session, de: str) -> list[tuple[str, str, str]]:
        """서울·경기 전 지점 (areaCd, brchNo, region). 목록 조회 실패 시 대표 지점으로 대체."""
        try:
            res = s.post(ENDPOINT, data=_body("10", "1351", de), timeout=self.timeout)
            res.raise_for_status()
            branches = [
                (b["areaCd"], b["brchNo"], AREA_TO_REGION[b["areaCdNm"]])
                for b in res.json().get("areaBrchList") or []
                if b.get("areaCdNm") in AREA_TO_REGION and "휴관" not in (b.get("brchNm") or "")
            ]
            return branches or FALLBACK_BRANCHES
        except Exception:  # noqa: BLE001
            return FALLBACK_BRANCHES

    def fetch(self, day: date) -> list[ShowtimeData]:
        de = day.strftime("%Y%m%d")
        items: list[ShowtimeData] = []
        with requests.Session() as s:
            s.proxies.update(self.requests_proxies or {})
            s.headers.update({"User-Agent": USER_AGENT, "Referer": "https://www.megabox.co.kr/booking",
                              "X-Requested-With": "XMLHttpRequest"})
            for area, brch, region in self._branches(s, de):
                try:
                    res = s.post(ENDPOINT, data=_body(area, brch, de), timeout=self.timeout)
                    res.raise_for_status()
                    form_list = res.json().get("movieFormList") or []
                except Exception:  # noqa: BLE001 - 한 지점 실패가 다른 지점 수집을 막지 않도록
                    continue
                for m in form_list:
                    poster = m.get("moviePosterImg")
                    items.append(ShowtimeData(
                        chain=self.chain,
                        external_id=f"{m['playSchdlNo']}",
                        theater=f"메가박스 {clean(m.get('brchNm'))}".strip(),
                        region=region,
                        screen=clean(m.get("theabExpoNm")),
                        movie_title=clean(m.get("movieNm")),
                        rating=m.get("admisClassCdNm"),
                        start_at=parse_hm(day, m["playStartTime"]),
                        end_at=parse_hm(day, m["playEndTime"]) if m.get("playEndTime") else None,
                        total_seats=int(m.get("totSeatCnt") or 0),
                        available_seats=int(m.get("restSeatCnt") or 0),
                        poster_url=f"https://www.megabox.co.kr{poster.replace('_150.', '_420.')}" if poster else None,
                        booking_url=BOOKING_URL.format(brch=brch, de=de),
                    ))
        if not items:
            raise CrawlError("메가박스 상영 시간표가 비어 있습니다.")
        return items
