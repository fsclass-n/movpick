"""잔여석 알림 송출: WebSocket(웹 토스트) + 텔레그램 / 디스코드 웹훅 / 이메일."""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

import httpx

from ..config import settings
from ..models import SeatWatch, Showtime, User
from .ws import manager

log = logging.getLogger("movpick.notifier")


def available_channels() -> dict[str, bool]:
    return {
        "web": True,
        "telegram": bool(settings.telegram_bot_token and settings.telegram_chat_id),
        "discord": bool(settings.discord_webhook_url),
        "email": bool(settings.smtp_host and settings.smtp_from),
    }


def _message(st: Showtime, seats: list[str]) -> str:
    return (
        f"[movpick] 명당 자리 잔여석 발생!\n"
        f"{st.movie_title} · {st.theater} {st.screen}\n"
        f"{st.start_at:%m/%d %H:%M} 상영 · 좌석 {', '.join(seats[:10])}\n"
        f"{st.booking_url or ''}"
    ).strip()


async def _telegram(text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": text},
        )


async def _discord(text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(settings.discord_webhook_url, json={"content": text})


def _email_sync(to: str, text: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = "[movpick] 명당 자리 잔여석 알림"
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(text)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
        s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg)


async def notify_seats(user: User, watch: SeatWatch, st: Showtime, seats: list[str]) -> None:
    channels = set(watch.channels or ["web"])
    enabled = available_channels()
    text = _message(st, seats)
    await manager.send_user(user.id, {
        "type": "seat_alert",
        "watch_id": watch.id,
        "showtime_id": st.id,
        "movie_title": st.movie_title,
        "theater": st.theater,
        "screen": st.screen,
        "start_at": st.start_at.isoformat(),
        "seats": seats,
        "booking_url": st.booking_url,
    })
    jobs = []
    if "telegram" in channels and enabled["telegram"]:
        jobs.append(_telegram(text))
    if "discord" in channels and enabled["discord"]:
        jobs.append(_discord(text))
    if "email" in channels and enabled["email"]:
        jobs.append(asyncio.to_thread(_email_sync, user.email, text))
    for r in await asyncio.gather(*jobs, return_exceptions=True):
        if isinstance(r, Exception):
            log.warning("webhook 알림 실패: %s", r)
