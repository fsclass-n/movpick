"""RPA 크롤러 작업 관리: 주기 실행 · 수동 실행 · 상태/로그 기록 · DB 동기화."""

import asyncio
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import delete, select

from rpa import seatmap
from rpa.models import CrawlResult
from rpa.service import CHAINS, crawl_chain

from ..config import settings
from ..db import SessionLocal
from ..models import CrawlLog, SeatWatch, Showtime
from .ws import manager

log = logging.getLogger("movpick.crawler")


def persist(result: CrawlResult, trigger: str) -> int:
    """수집 결과를 showtimes 테이블에 upsert 하고 crawl_logs 기록."""
    result.items = list({i.external_id: i for i in result.items}.values())
    with SessionLocal() as db:
        existing = {
            s.external_id: s
            for s in db.scalars(select(Showtime).where(
                Showtime.chain == result.chain,
                Showtime.external_id.in_([i.external_id for i in result.items] or [""]),
            ))
        }
        for item in result.items:
            st = existing.get(item.external_id)
            seed = f"{item.chain}:{item.external_id}"
            if st is None:
                st = Showtime(chain=item.chain, external_id=item.external_id)
                db.add(st)
                layout = seatmap.build_layout(item.total_seats, item.available_seats, seed)
            elif result.source == "real" or not st.seat_layout:
                layout = seatmap.reconcile(st.seat_layout, item.available_seats, seed) if st.seat_layout else \
                    seatmap.build_layout(item.total_seats, item.available_seats, seed)
            else:
                layout = st.seat_layout
            st.theater, st.screen, st.movie_title, st.rating = item.theater, item.screen, item.movie_title, item.rating
            st.start_at, st.end_at, st.booking_url, st.poster_url = item.start_at, item.end_at, item.booking_url, item.poster_url
            st.source = result.source
            st.seat_layout = layout
            st.total_seats = seatmap.capacity(layout)
            st.available_seats = seatmap.available_count(layout)
            st.updated_at = datetime.now()
        db.add(CrawlLog(
            job="showtimes", chain=result.chain, status="success" if result.ok else "failed",
            source=result.source, items=len(result.items), duration_ms=result.duration_ms,
            message=result.message, trigger=trigger,
        ))
        _cleanup(db)
        db.commit()
        return len(result.items)


def log_failure(result: CrawlResult, trigger: str) -> None:
    with SessionLocal() as db:
        db.add(CrawlLog(job="showtimes", chain=result.chain, status="failed", source=result.source, items=0,
                        duration_ms=result.duration_ms, message=result.message, trigger=trigger))
        db.commit()


def _cleanup(db) -> None:
    cutoff = datetime.now() - timedelta(days=1)
    old_ids = select(Showtime.id).where(Showtime.start_at < cutoff)
    db.execute(delete(SeatWatch).where(SeatWatch.showtime_id.in_(old_ids)))
    db.execute(delete(Showtime).where(Showtime.start_at < cutoff))
    db.execute(delete(CrawlLog).where(CrawlLog.started_at < datetime.now() - timedelta(days=14)))


class CrawlerManager:
    def __init__(self) -> None:
        self.enabled = settings.rpa_enabled
        self.interval_minutes = settings.crawl_interval_minutes
        self.running = False
        self.last_started_at: datetime | None = None
        self.last_finished_at: datetime | None = None
        self.next_run_at: datetime | None = None
        self.last_results: list[dict] = []
        self._lock = asyncio.Lock()
        self._wake = asyncio.Event()

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "running": self.running,
            "mode": settings.rpa_mode,
            "headless": settings.rpa_headless,
            "interval_minutes": self.interval_minutes,
            "seat_monitor_interval_seconds": settings.seat_monitor_interval_seconds,
            "chains": CHAINS,
            "last_started_at": self.last_started_at,
            "last_finished_at": self.last_finished_at,
            "next_run_at": self.next_run_at,
            "last_results": self.last_results,
        }

    def configure(self, interval_minutes: int, enabled: bool) -> None:
        self.interval_minutes, self.enabled = interval_minutes, enabled
        self.next_run_at = (self.last_finished_at or datetime.now()) + timedelta(minutes=interval_minutes)
        self._wake.set()

    async def run_once(self, trigger: str = "schedule", chains: list[str] | None = None) -> list[dict]:
        if self._lock.locked():
            return self.last_results
        async with self._lock:
            self.running = True
            self.last_started_at = datetime.now()
            await manager.broadcast({"type": "crawl_started", "trigger": trigger})
            results = []
            try:
                for chain in chains or CHAINS:
                    for day in (date.today(), date.today() + timedelta(days=1)):
                        r = await asyncio.to_thread(
                            crawl_chain, chain, day, settings.rpa_mode, settings.rpa_timeout_seconds, settings.rpa_headless
                        )
                        try:
                            saved = await asyncio.to_thread(persist, r, trigger)
                        except Exception as e:  # noqa: BLE001 - 한 체인 실패가 전체 작업을 중단시키지 않도록
                            log.exception("persist failed: %s %s", chain, day)
                            r.ok, r.message, saved = False, f"DB 저장 실패: {type(e).__name__}: {e}"[:500], 0
                            await asyncio.to_thread(log_failure, r, trigger)
                        results.append({"chain": chain, "date": day.isoformat(), "ok": r.ok, "source": r.source,
                                        "items": saved, "duration_ms": r.duration_ms, "message": r.message})
                        log.info("crawl %s %s ok=%s source=%s items=%s", chain, day, r.ok, r.source, saved)
            finally:
                self.running = False
                self.last_finished_at = datetime.now()
                self.last_results = results
            await manager.broadcast({"type": "crawl_finished", "trigger": trigger, "results": results})
            return results

    async def loop(self) -> None:
        self.next_run_at = datetime.now()
        while True:
            if self.enabled and datetime.now() >= self.next_run_at:
                try:
                    await self.run_once("schedule")
                except Exception:  # noqa: BLE001
                    log.exception("crawl loop error")
                self.next_run_at = datetime.now() + timedelta(minutes=self.interval_minutes)
            self._wake.clear()
            timeout = max(1.0, (self.next_run_at - datetime.now()).total_seconds()) if self.enabled else None
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass


crawler = CrawlerManager()
