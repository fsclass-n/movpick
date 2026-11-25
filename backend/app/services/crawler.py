"""RPA 크롤러 작업 관리: 주기 실행 · 수동 실행 · 상태/로그 기록 · DB 동기화."""

import asyncio
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select

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
        if result.day and result.items:
            if result.source == "real":
                _purge(db, result.chain, result.day, "mock")
            elif result.chain in settings.rpa_mock_chains:  # 데모 모드 체인: 남아 있는 실데이터와 섞이지 않도록 정리
                _purge(db, result.chain, result.day, "real")
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
            st.region = item.region
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


def day_window(day: date) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day)
    return start, start + timedelta(days=1, hours=6)


def _purge(db, chain: str, day: date, source: str) -> None:
    """같은 체인·일자에서 다른 출처(source)의 회차를 제거해 실데이터/모의 데이터 혼재를 방지."""
    start, end = day_window(day)
    cond = (Showtime.chain == chain, Showtime.source == source, Showtime.start_at >= start, Showtime.start_at < end)
    db.execute(delete(SeatWatch).where(SeatWatch.showtime_id.in_(select(Showtime.id).where(*cond))))
    db.execute(delete(Showtime).where(*cond))


def real_state(chain: str, day: date) -> tuple[bool, bool]:
    """(실데이터 존재, TTL 이내 갱신). 실데이터가 있으면 수집 실패 시에도 모의 데이터를 섞지 않는다."""
    start, end = day_window(day)
    with SessionLocal() as db:
        last = db.scalar(select(func.max(Showtime.updated_at)).where(
            Showtime.chain == chain, Showtime.source == "real", Showtime.start_at >= start, Showtime.start_at < end))
    return last is not None, bool(last and last >= datetime.now() - timedelta(minutes=settings.rpa_real_ttl_minutes))


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
        self.remote: dict[str, dict] = {}
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
            "remote_chains": [c for c in settings.rpa_remote_chains if c not in settings.rpa_mock_chains],
            "mock_chains": settings.rpa_mock_chains,
            "remote": self.remote,
            "proxy": bool(settings.rpa_proxy_url),
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
                    for i in range(settings.crawl_days):
                        results.append(await self._crawl_one(chain, date.today() + timedelta(days=i), trigger))
            finally:
                self.running = False
                self.last_finished_at = datetime.now()
                self.last_results = results
            await manager.broadcast({"type": "crawl_finished", "trigger": trigger, "results": results})
            return results

    async def _crawl_one(self, chain: str, day: date, trigger: str) -> dict:
        if chain in settings.rpa_mock_chains:
            # 데모 모드: 실제 수집 없이 모의 데이터만 사용 (원격 수집 설정보다 우선)
            r = await asyncio.to_thread(crawl_chain, chain, day, "mock")
            r.message = f"데모 데이터 모드 → 모의 데이터 {len(r.items)}건"
            saved = await asyncio.to_thread(persist, r, trigger)
            return {"chain": chain, "date": day.isoformat(), "ok": True, "source": "demo", "items": saved,
                    "duration_ms": r.duration_ms, "message": r.message}
        has_real, fresh = await asyncio.to_thread(real_state, chain, day)
        stale = "" if fresh else f" · 갱신 지연(TTL {settings.rpa_real_ttl_minutes}분 초과)"
        if chain in settings.rpa_remote_chains:
            # 데이터센터 IP 차단 체인: 국내 원격 수집기(rpa.runner --push)가 보낸 실데이터 사용
            if has_real:
                return {"chain": chain, "date": day.isoformat(), "ok": fresh, "source": "remote", "items": 0,
                        "duration_ms": 0, "message": f"원격 수집기 실데이터 사용 중{stale}"}
            r = await asyncio.to_thread(crawl_chain, chain, day, "mock")
            r.ok, r.message = False, f"원격 수집기 데이터 없음 → 모의 데이터 {len(r.items)}건"
        else:
            r = await asyncio.to_thread(crawl_chain, chain, day, settings.rpa_mode, settings.rpa_timeout_seconds,
                                        settings.rpa_headless, settings.rpa_proxy_url)
            if r.source == "mock" and r.error and has_real:
                r.items, r.message = [], f"실제 수집 실패 → 기존 실데이터 유지{stale} ({r.error})"[:500]
                await asyncio.to_thread(log_failure, r, trigger)
                return {"chain": chain, "date": day.isoformat(), "ok": False, "source": "real", "items": 0,
                        "duration_ms": r.duration_ms, "message": r.message}
        try:
            saved = await asyncio.to_thread(persist, r, trigger)
        except Exception as e:  # noqa: BLE001 - 한 체인 실패가 전체 작업을 중단시키지 않도록
            log.exception("persist failed: %s %s", chain, day)
            r.ok, r.message, saved = False, f"DB 저장 실패: {type(e).__name__}: {e}"[:500], 0
            await asyncio.to_thread(log_failure, r, trigger)
        log.info("crawl %s %s ok=%s source=%s items=%s", chain, day, r.ok, r.source, saved)
        return {"chain": chain, "date": day.isoformat(), "ok": r.ok, "source": r.source, "items": saved,
                "duration_ms": r.duration_ms, "message": r.message}

    async def ingest(self, result: CrawlResult, collector: str) -> int:
        """원격 수집기(국내 PC 등)가 push 한 실데이터 저장"""
        saved = await asyncio.to_thread(persist, result, "remote")
        self.remote[result.chain] = {"at": datetime.now(), "date": result.day.isoformat() if result.day else None,
                                     "items": saved, "collector": collector}
        await manager.broadcast({"type": "crawl_finished", "trigger": "remote", "results": [
            {"chain": result.chain, "date": self.remote[result.chain]["date"], "ok": True, "source": "real",
             "items": saved, "duration_ms": result.duration_ms, "message": result.message}]})
        return saved

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
