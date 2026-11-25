import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import func, inspect, select, text

from .config import settings
from .db import Base, SessionLocal, engine
from .models import Showtime
from .routers import admin, auth, rpa, showtimes, watches
from .routers.auth import ensure_demo_user, ensure_env_admin
from .security import user_from_token
from .services.crawler import crawler
from .services.monitor import monitor_loop
from .services.ws import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("movpick")


def _migrate() -> None:
    """경량 스키마 마이그레이션: 누락 컬럼 추가 + 기존 데이터 백필."""
    cols = {c["name"] for c in inspect(engine).get_columns("showtimes")}
    with engine.begin() as conn:
        if "region" not in cols:
            conn.execute(text("ALTER TABLE showtimes ADD COLUMN region VARCHAR(20)"))
            # 기존 수집 지점은 모두 서울 지점
            conn.execute(text("UPDATE showtimes SET region='seoul' WHERE region IS NULL"))
        # 수집 대상에서 빠진 지역 데이터 정리
        conn.execute(text("DELETE FROM seat_watches WHERE showtime_id IN (SELECT id FROM showtimes WHERE region='incheon')"))
        conn.execute(text("DELETE FROM showtimes WHERE region='incheon'"))


def init_db() -> None:
    Base.metadata.create_all(engine)
    _migrate()
    with SessionLocal() as db:
        ensure_env_admin(db)
        if settings.demo_login_enabled:
            ensure_demo_user(db, "user")
            ensure_demo_user(db, "admin")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(init_db)
    log.info("DB ready: %s", engine.url.render_as_string(hide_password=True))
    tasks = []
    if settings.rpa_enabled:
        tasks = [asyncio.create_task(crawler.loop()), asyncio.create_task(monitor_loop())]
    yield
    for t in tasks:
        t.cancel()
        with suppress(asyncio.CancelledError):
            await t


app = FastAPI(title="movpick API", version="1.0.0", lifespan=lifespan,
              description="RPA 기반 영화 상영 시간표 동기화 · 명당 자리 실시간 예매 추천 API")
app.add_middleware(GZipMiddleware, minimum_size=1000)  # 서울·경기 전 지점 상영표 응답 압축
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (auth.router, showtimes.router, watches.router, admin.router, rpa.router):
    app.include_router(r)


@app.get("/")
def root():
    return {"service": "movpick-api", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        count = db.scalar(select(func.count()).select_from(Showtime))
    return {"status": "ok", "commit": os.getenv("RENDER_GIT_COMMIT", "local")[:7], "db": engine.dialect.name,
            "showtimes": count, "ws_connections": manager.count,
            "crawler": {"enabled": crawler.enabled, "running": crawler.running, "mode": settings.rpa_mode}}


@app.websocket("/ws")
async def websocket(ws: WebSocket, token: str | None = Query(None)):
    with SessionLocal() as db:
        user = user_from_token(db, token)
    uid = user.id if user else None
    await manager.connect(ws, uid)
    await ws.send_json({"type": "hello", "user_id": uid, "crawler_running": crawler.running})
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except (WebSocketDisconnect, RuntimeError, ValueError):
        pass
    finally:
        await manager.disconnect(ws, uid)
