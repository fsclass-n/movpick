"""명당 자리 잔여석 모니터: 좌석 변동 감지 → 감시 중인 사용자에게 실시간 알림."""

import asyncio
import logging
import random
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from rpa import seatmap

from ..config import settings
from ..db import SessionLocal
from ..models import SeatWatch, Showtime
from .notifier import notify_seats
from .ws import manager

log = logging.getLogger("movpick.monitor")
LIVE_SAMPLE = 40


def watch_targets(watch: SeatWatch, layout: dict) -> set[str]:
    return set(layout["prime"]) if watch.mode == "prime" else set(watch.seats or [])


def free_targets(watch: SeatWatch, layout: dict) -> list[str]:
    return sorted(watch_targets(watch, layout) & seatmap.free_seats(layout))


def _tick(rng: random.Random) -> tuple[list[dict], list[tuple]]:
    now = datetime.now()
    updates, alerts = [], []
    with SessionLocal() as db:
        watches = db.scalars(
            select(SeatWatch).options(selectinload(SeatWatch.showtime), selectinload(SeatWatch.user))
            .where(SeatWatch.active.is_(True))
        ).all()
        watched_ids = {w.showtime_id for w in watches}
        upcoming = db.scalars(
            select(Showtime).where(Showtime.start_at > now, Showtime.start_at < now + timedelta(hours=36))
            .order_by(Showtime.start_at).limit(300)
        ).all()
        sample = [s for s in upcoming if s.id in watched_ids]
        others = [s for s in upcoming if s.id not in watched_ids]
        sample += rng.sample(others, min(LIVE_SAMPLE, len(others)))

        if settings.seat_simulation:
            for st in sample:
                if not st.seat_layout:
                    continue
                layout, freed, booked = seatmap.simulate_tick(st.seat_layout, rng)
                if freed or booked:
                    st.seat_layout = layout
                    st.available_seats = seatmap.available_count(layout)
                    updates.append({"showtime_id": st.id, "available_seats": st.available_seats,
                                    "taken": layout["taken"], "freed": freed, "booked": booked})

        for w in watches:
            st = w.showtime
            if not st or not st.seat_layout or st.start_at <= now:
                if st and st.start_at <= now:
                    w.active = False
                continue
            current = free_targets(w, st.seat_layout)
            new = sorted(set(current) - set(w.last_notified_seats or []))
            w.last_notified_seats = current
            if new:
                alerts.append((w.user, w, st, new))
        db.commit()
    return updates, alerts


async def monitor_loop() -> None:
    rng = random.Random()
    while True:
        await asyncio.sleep(settings.seat_monitor_interval_seconds)
        try:
            updates, alerts = await asyncio.to_thread(_tick, rng)
            for u in updates:
                await manager.broadcast({"type": "seat_update", **u})
            for user, watch, st, seats in alerts:
                await notify_seats(user, watch, st, seats)
            if alerts:
                log.info("seat alerts sent: %d", len(alerts))
        except Exception:  # noqa: BLE001
            log.exception("seat monitor error")
