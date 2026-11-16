import json
from datetime import date

import requests

from ..models import ShowtimeData
from .base import USER_AGENT, BaseAdapter, CrawlError, parse_hm

ENDPOINT = "https://www.lottecinema.co.kr/LCWS/Ticketing/TicketingData.aspx"
CINEMAS = ["1|0001|1016", "1|0001|1013"]  # 월드타워, 가산디지털


class LotteAdapter(BaseAdapter):
    chain = "lotte"
    label = "롯데시네마"

    def fetch(self, day: date) -> list[ShowtimeData]:
        items: list[ShowtimeData] = []
        with requests.Session() as s:
            s.headers.update({"User-Agent": USER_AGENT, "Referer": "https://www.lottecinema.co.kr/"})
            for cinema in CINEMAS:
                param = {"MethodName": "GetPlaySequence", "channelType": "HO", "osType": "W",
                         "osVersion": USER_AGENT, "playDate": day.isoformat(), "cinemaID": cinema,
                         "representationMovieCode": ""}
                res = s.post(ENDPOINT, data={"paramList": json.dumps(param)}, timeout=self.timeout)
                res.raise_for_status()
                for m in (res.json().get("PlaySeqs") or {}).get("Items") or []:
                    items.append(ShowtimeData(
                        chain=self.chain,
                        external_id=f"{m['CinemaID']}-{m['ScreenID']}-{m['PlayDt']}-{m['PlaySequence']}",
                        theater=f"롯데시네마 {m.get('CinemaNameKR', '')}".strip(),
                        screen=m.get("ScreenNameKR") or "",
                        movie_title=m.get("MovieNameKR") or "",
                        rating=m.get("ViewGradeNameKR"),
                        start_at=parse_hm(day, m["StartTime"]),
                        end_at=parse_hm(day, m["EndTime"]) if m.get("EndTime") else None,
                        total_seats=int(m.get("TotalSeatCount") or 0),
                        available_seats=int(m.get("BookingSeatCount") or 0),
                        poster_url=(m.get("PosterURL") or "").replace("http://", "https://") or None,
                        booking_url="https://www.lottecinema.co.kr/NLCHS/Ticketing",
                    ))
        if not items:
            raise CrawlError("롯데시네마 상영 시간표가 비어 있습니다.")
        return items
