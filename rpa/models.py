from dataclasses import asdict, dataclass, field
from datetime import date, datetime

# 수집 대상 지역 코드 → 표시명 (프런트엔드 format.js 의 REGIONS 와 동일 값 유지)
REGIONS = {"seoul": "서울", "gyeonggi": "경기", "incheon": "인천"}


@dataclass
class ShowtimeData:
    chain: str
    external_id: str
    theater: str
    screen: str
    movie_title: str
    start_at: datetime
    total_seats: int
    available_seats: int
    end_at: datetime | None = None
    rating: str | None = None
    booking_url: str | None = None
    poster_url: str | None = None
    region: str | None = None  # REGIONS 키 (seoul/gyeonggi/incheon)
    source: str = "real"
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start_at"] = self.start_at.isoformat()
        d["end_at"] = self.end_at.isoformat() if self.end_at else None
        return d


@dataclass
class CrawlResult:
    chain: str
    items: list[ShowtimeData]
    source: str
    ok: bool
    duration_ms: int
    message: str = ""
    day: date | None = None
    error: str = ""
    via: str = ""
