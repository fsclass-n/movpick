"""실제 사이트 수집 실패 시 사용하는 결정적(deterministic) 모의 데이터 생성기."""

import random
from datetime import date, datetime, timedelta

from ..models import ShowtimeData
from .base import BaseAdapter

THEATERS = {
    "cgv": ["CGV 강남", "CGV 용산아이파크몰"],
    "megabox": ["메가박스 코엑스", "메가박스 강남"],
    "lotte": ["롯데시네마 월드타워", "롯데시네마 가산디지털"],
}
SCREENS = [("1관", 172), ("3관 IMAX", 300), ("5관 Dolby", 248), ("7관 리클라이너", 96), ("9관", 140)]
MOVIES = [
    ("미드나잇 시그널", "15세이상관람가", 124),
    ("서울 2049: 네온 레인", "12세이상관람가", 138),
    ("마지막 상영관", "15세이상관람가", 109),
    ("하이 템포", "전체관람가", 101),
    ("블루 아워", "12세이상관람가", 117),
    ("별의 궤도", "전체관람가", 132),
]


class MockAdapter(BaseAdapter):
    label = "모의 데이터"

    def __init__(self, chain: str, **kw):
        super().__init__(**kw)
        self.chain = chain

    def fetch(self, day: date) -> list[ShowtimeData]:
        rng = random.Random(f"{self.chain}-{day.isoformat()}")
        items: list[ShowtimeData] = []
        for theater in THEATERS.get(self.chain, [f"{self.chain} 극장"]):
            for idx, (screen, seats) in enumerate(rng.sample(SCREENS, 3)):
                title, rating, runtime = MOVIES[(idx + rng.randrange(len(MOVIES))) % len(MOVIES)]
                start = datetime(day.year, day.month, day.day, 9, 30) + timedelta(minutes=rng.randrange(0, 90, 10))
                for n in range(5):
                    end = start + timedelta(minutes=runtime + 10)
                    hours_left = (start - datetime.now()).total_seconds() / 3600
                    sold_ratio = min(0.97, max(0.05, 0.85 - hours_left * 0.04 + rng.uniform(-0.15, 0.15)))
                    items.append(ShowtimeData(
                        chain=self.chain,
                        external_id=f"mock-{theater}-{screen}-{start:%Y%m%d%H%M}",
                        theater=theater,
                        screen=screen,
                        movie_title=title,
                        rating=rating,
                        start_at=start,
                        end_at=end,
                        total_seats=seats,
                        available_seats=int(seats * (1 - sold_ratio)),
                        source="mock",
                    ))
                    start = end + timedelta(minutes=rng.randrange(15, 40, 5))
                    if start.hour >= 24 or start.date() != day:
                        break
        return items
