from datetime import date

import requests
from bs4 import BeautifulSoup

from ..models import ShowtimeData
from .base import USER_AGENT, BaseAdapter, CrawlError, parse_hm

ENDPOINT = "https://www.megabox.co.kr/on/oh/ohb/SimpleBooking/selectBokdList.do"
BOOKING_URL = "https://www.megabox.co.kr/booking?brchNo={brch}&playDe={de}"

# (지역코드, 지점코드, region) — 지점 목록·지역은 selectBokdList.do 의 areaBrchList/areaCdNm 과 동일
BRANCHES = [
    ("10", "1351", "seoul"),     # 코엑스
    ("10", "1372", "seoul"),     # 강남
    ("10", "1211", "seoul"),     # 상암월드컵경기장
    ("30", "4121", "gyeonggi"),  # 고양스타필드
    ("30", "4451", "gyeonggi"),  # 동탄
    ("30", "4651", "gyeonggi"),  # 하남스타필드
    ("35", "4062", "incheon"),   # 송도(트리플스트리트)
    ("35", "4051", "incheon"),   # 인천논현
    ("35", "4041", "incheon"),   # 검단
]


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
            s.headers.update({"User-Agent": USER_AGENT, "Referer": "https://www.megabox.co.kr/booking",
                              "X-Requested-With": "XMLHttpRequest"})
            for area, brch, region in BRANCHES:
                body = {"masterType": "brch", "detailType": "area", "areaCode": area,
                        "brchNo": brch, "brchNo1": brch, "firstAt": "N", "crtDe": de, "playDe": de}
                try:
                    res = s.post(ENDPOINT, data=body, timeout=self.timeout)
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
