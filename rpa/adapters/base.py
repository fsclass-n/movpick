from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

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

    def __init__(self, timeout: int = 20, headless: bool = True, proxy: str | None = None):
        self.timeout = timeout
        self.headless = headless
        self.proxy = proxy or None

    @property
    def requests_proxies(self) -> dict | None:
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

    @property
    def playwright_proxy(self) -> dict | None:
        if not self.proxy:
            return None
        u = urlsplit(self.proxy)
        cfg = {"server": f"{u.scheme}://{u.hostname}:{u.port}" if u.port else f"{u.scheme}://{u.hostname}"}
        if u.username:
            cfg |= {"username": u.username, "password": u.password or ""}
        return cfg

    @abstractmethod
    def fetch(self, day: date) -> list[ShowtimeData]:
        """지정 일자의 상영 시간표/잔여석을 수집. 실패 시 CrawlError."""
