import json
from datetime import date

import requests

from ..models import ShowtimeData
from .base import USER_AGENT, BaseAdapter, CrawlError, parse_hm

ENDPOINT = "https://www.lottecinema.co.kr/LCWS/Ticketing/TicketingData.aspx"
BOOKING_URL = "https://www.lottecinema.co.kr/NLCHS/Ticketing"

# (cinemaID = 지역구분|상세지역|영화관코드, region) — GetCinemaItems 응답 기준
CINEMAS = [
    ("1|0001|1016", "seoul"),    # 월드타워
    ("1|0001|1013", "seoul"),    # 가산디지털
    ("1|0001|1005", "seoul"),    # 홍대입구
    ("1|0002|3024", "gyeonggi"), # 수원(수원역)
    ("1|0002|3048", "gyeonggi"), # 동탄
    ("1|0002|9129", "gyeonggi"), # 하남미사
    ("1|0002|3008", "incheon"),  # 부평역사
    ("1|0002|3038", "incheon"),  # 인천터미널
    ("1|0002|3051", "incheon"),  # 검단아라
]


class LotteAdapter(BaseAdapter):
    chain = "lotte"
    label = "롯데시네마"

    def fetch(self, day: date) -> list[ShowtimeData]:
        items: list[ShowtimeData] = []
        with requests.Session() as s:
            s.proxies.update(self.requests_proxies or {})
            s.headers.update({"User-Agent": USER_AGENT, "Referer": "https://www.lottecinema.co.kr/"})
            for cinema, region in CINEMAS:
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
