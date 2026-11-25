import json
from datetime import date

import requests

from ..models import ShowtimeData
from .base import USER_AGENT, BaseAdapter, CrawlError, parse_hm

ENDPOINT = "https://www.lottecinema.co.kr/LCWS/Ticketing/TicketingData.aspx"
LIST_ENDPOINT = "https://www.lottecinema.co.kr/LCWS/Cinema/CinemaData.aspx"
BOOKING_URL = "https://www.lottecinema.co.kr/NLCHS/Ticketing"

# GetCinemaItems 의 DetailDivisionCode: 0001=서울, 0002=경기·인천 혼합
# 0002 에는 인천 지점도 섞여 있어 이름으로 제외한다
DIVISION_REGION = {"0001": "seoul", "0002": "gyeonggi"}
INCHEON_TOKENS = ("인천", "부평", "검단", "청라", "송도", "계양", "주안", "연수")

# 지점 목록 조회 실패 시 사용하는 대표 지점 (cinemaID = 지역구분|상세지역|영화관코드)
FALLBACK_CINEMAS = [
    ("1|0001|1016", "seoul"),    # 월드타워
    ("1|0001|1013", "seoul"),    # 가산디지털
    ("1|0001|1005", "seoul"),    # 홍대입구
    ("1|0002|3024", "gyeonggi"), # 수원(수원역)
    ("1|0002|3048", "gyeonggi"), # 동탄
    ("1|0002|9129", "gyeonggi"), # 하남미사
]


class LotteAdapter(BaseAdapter):
    chain = "lotte"
    label = "롯데시네마"

    def _cinemas(self, s: requests.Session) -> list[tuple[str, str]]:
        """서울·경기 전 지점 (cinemaID, region). 목록 조회 실패 시 대표 지점으로 대체."""
        param = {"MethodName": "GetCinemaItems", "channelType": "HO", "osType": "W",
                 "osVersion": USER_AGENT, "divisionList": [], "favoriteMovieList": [], "memberSeq": ""}
        try:
            res = s.post(LIST_ENDPOINT, data={"paramList": json.dumps(param)}, timeout=self.timeout)
            res.raise_for_status()
            cinemas = [
                (f"1|{it['DetailDivisionCode']}|{it['CinemaID']}", region)
                for it in (res.json().get("Cinemas") or {}).get("Items") or []
                if it.get("DivisionCode") == 1
                for region in (DIVISION_REGION.get(it.get("DetailDivisionCode") or ""),)
                if region and not any(t in (it.get("CinemaNameKR") or "") for t in INCHEON_TOKENS)
            ]
            return cinemas or FALLBACK_CINEMAS
        except Exception:  # noqa: BLE001
            return FALLBACK_CINEMAS

    def fetch(self, day: date) -> list[ShowtimeData]:
        items: list[ShowtimeData] = []
        with requests.Session() as s:
            s.proxies.update(self.requests_proxies or {})
            s.headers.update({"User-Agent": USER_AGENT, "Referer": "https://www.lottecinema.co.kr/"})
            for cinema, region in self._cinemas(s):
                param = {"MethodName": "GetPlaySequence", "channelType": "HO", "osType": "W",
                         "osVersion": USER_AGENT, "playDate": day.isoformat(), "cinemaID": cinema,
                         "representationMovieCode": ""}
                try:
                    res = s.post(ENDPOINT, data={"paramList": json.dumps(param)}, timeout=self.timeout)
                    res.raise_for_status()
                    seqs = (res.json().get("PlaySeqs") or {}).get("Items") or []
                except Exception:  # noqa: BLE001 - 한 지점 실패가 다른 지점 수집을 막지 않도록
                    continue
                for m in seqs:
                    items.append(ShowtimeData(
                        chain=self.chain,
                        external_id=f"{m['CinemaID']}-{m['ScreenID']}-{m['PlayDt']}-{m['PlaySequence']}",
                        theater=f"롯데시네마 {m.get('CinemaNameKR', '')}".strip(),
                        region=region,
                        screen=m.get("ScreenNameKR") or "",
                        movie_title=m.get("MovieNameKR") or "",
                        rating=m.get("ViewGradeNameKR"),
                        start_at=parse_hm(day, m["StartTime"]),
                        end_at=parse_hm(day, m["EndTime"]) if m.get("EndTime") else None,
                        total_seats=int(m.get("TotalSeatCount") or 0),
                        available_seats=int(m.get("BookingSeatCount") or 0),
                        poster_url=(m.get("PosterURL") or "").replace("http://", "https://") or None,
                        booking_url=BOOKING_URL,
                    ))
        if not items:
            raise CrawlError("롯데시네마 상영 시간표가 비어 있습니다.")
        return items
