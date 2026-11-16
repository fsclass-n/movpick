import time
from datetime import date

from .adapters.base import BaseAdapter
from .adapters.cgv import CgvAdapter
from .adapters.lotte import LotteAdapter
from .adapters.megabox import MegaboxAdapter
from .adapters.mock import MockAdapter
from .models import CrawlResult

ADAPTERS: dict[str, type[BaseAdapter]] = {
    "cgv": CgvAdapter,
    "megabox": MegaboxAdapter,
    "lotte": LotteAdapter,
}
CHAINS = list(ADAPTERS)
CHAIN_LABELS = {k: v.label for k, v in ADAPTERS.items()}


def crawl_chain(chain: str, day: date, mode: str = "auto", timeout: int = 20, headless: bool = True) -> CrawlResult:
    """mode: auto(실제→실패 시 모의) | real | mock"""
    started = time.perf_counter()
    elapsed = lambda: int((time.perf_counter() - started) * 1000)  # noqa: E731
    error = ""
    if mode in ("auto", "real"):
        try:
            items = ADAPTERS[chain](timeout=timeout, headless=headless).fetch(day)
            return CrawlResult(chain, items, "real", True, elapsed(), f"{len(items)}건 수집")
        except Exception as e:  # noqa: BLE001 - 사이트 구조 변경/차단 등 모든 실패를 폴백 처리
            error = f"{type(e).__name__}: {e}"[:500]
            if mode == "real":
                return CrawlResult(chain, [], "real", False, elapsed(), error)
    items = MockAdapter(chain).fetch(day)
    message = f"실제 수집 실패 → 모의 데이터 {len(items)}건 대체 ({error})" if error else f"모의 데이터 {len(items)}건 생성"
    return CrawlResult(chain, items, "mock", not error, elapsed(), message)
