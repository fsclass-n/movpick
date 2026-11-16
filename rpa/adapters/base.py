from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta

from ..models import ShowtimeData

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class CrawlError(RuntimeError):
    pass


def parse_hm(day: date, hm: str) -> datetime:
    """'22:30' / '2230' / '24:19'(익일) → datetime"""
    hm = (hm or "").replace(":", "").strip().zfill(4)
    hour, minute = int(hm[:2]), int(hm[2:4])
    return datetime(day.year, day.month, day.day) + timedelta(hours=hour, minutes=minute)


class BaseAdapter(ABC):
    chain: str = ""
    label: str = ""

    def __init__(self, timeout: int = 20, headless: bool = True):
        self.timeout = timeout
        self.headless = headless

    @abstractmethod
    def fetch(self, day: date) -> list[ShowtimeData]:
        """지정 일자의 상영 시간표/잔여석을 수집. 실패 시 CrawlError."""
