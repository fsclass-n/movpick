import asyncio
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CrawlLog, SeatWatch, Showtime, User
from ..schemas import CrawlerConfigIn, CrawlLogOut, RoleIn, UserOut
from ..config import settings
from ..security import require_admin, require_admin_write
from rpa.service import CHAINS, crawl_chain

from ..services.crawler import crawler
from ..services.ws import manager

_tasks: set[asyncio.Task] = set()
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    since = datetime.now() - timedelta(hours=24)
    logs = db.execute(select(CrawlLog.status, func.count()).where(CrawlLog.started_at >= since)
                      .group_by(CrawlLog.status)).all()
    return {
        "users": db.scalar(select(func.count()).select_from(User)),
        "admins": db.scalar(select(func.count()).select_from(User).where(User.role == "admin")),
        "showtimes": db.scalar(select(func.count()).select_from(Showtime)),
        "active_watches": db.scalar(select(func.count()).select_from(SeatWatch).where(SeatWatch.active.is_(True))),
        "ws_connections": manager.count,
        "crawl_24h": {k: v for k, v in logs},
    }


# ------------------------------------------------------------------ users
@router.get("/users", response_model=list[UserOut])
def users(q: str | None = Query(None, max_length=50), db: Session = Depends(get_db)):
    stmt = select(User).order_by(User.created_at.desc(), User.id.desc())
    if q:
        stmt = stmt.where(or_(User.email.like(f"%{q}%"), User.name.like(f"%{q}%")))
    return db.scalars(stmt.limit(500)).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def change_role(user_id: int, body: RoleIn, admin: User = Depends(require_admin_write), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "회원을 찾을 수 없습니다.")
    if user.id == admin.id and body.role != "admin":
        raise HTTPException(400, "본인의 관리자 권한은 해제할 수 없습니다.")
    if settings.admin_email and user.email == settings.admin_email.lower() and body.role != "admin":
        raise HTTPException(400, "환경 변수(ADMIN_EMAIL)로 지정된 관리자는 권한을 변경할 수 없습니다.")
    user.role = body.role
    db.commit()
    await manager.send_user(user.id, {"type": "role_changed", "role": user.role})
    return user


# ---------------------------------------------------------------- crawler
@router.get("/crawler")
def crawler_status():
    return crawler.status()


@router.put("/crawler/config", dependencies=[Depends(require_admin_write)])
def crawler_config(body: CrawlerConfigIn):
    crawler.configure(body.interval_minutes, body.enabled)
    return crawler.status()


@router.post("/crawler/run", status_code=202, dependencies=[Depends(require_admin_write)])
async def crawler_run(chain: str | None = None):
    if crawler.running:
        raise HTTPException(409, "이미 크롤링이 실행 중입니다.")
    task = asyncio.create_task(crawler.run_once("manual", [chain] if chain else None))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"accepted": True}


_probe_lock = asyncio.Lock()


@router.post("/crawler/probe")
async def crawler_probe(chain: str = Query(..., pattern="^(" + "|".join(CHAINS) + ")$")):
    """서버(현재 실행 환경)에서 실제 사이트 수집 가능 여부 진단. DB 에는 저장하지 않음 (읽기 전용 계정 허용)."""
    if _probe_lock.locked():
        raise HTTPException(409, "다른 진단이 실행 중입니다.")
    async with _probe_lock:
        r = await asyncio.to_thread(crawl_chain, chain, datetime.now().date() + timedelta(days=1), "real",
                                    settings.rpa_timeout_seconds, settings.rpa_headless, settings.rpa_proxy_url)
    return {"chain": chain, "ok": r.ok, "via": r.via, "items": len(r.items), "duration_ms": r.duration_ms,
            "message": r.message, "sample": r.items[0].to_dict() if r.items else None}


@router.get("/crawler/logs", response_model=list[CrawlLogOut])
def crawler_logs(limit: int = Query(50, le=200), status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(CrawlLog).order_by(CrawlLog.started_at.desc(), CrawlLog.id.desc())
    if status:
        stmt = stmt.where(CrawlLog.status == status)
    return db.scalars(stmt.limit(limit)).all()


@router.get("/reports/crawl", response_class=HTMLResponse)
def crawl_report(db: Session = Depends(get_db)):
    """Plotly 기반 크롤링 성공률/소요시간 리포트 (HTML)"""
    rows = db.execute(select(CrawlLog.started_at, CrawlLog.chain, CrawlLog.status, CrawlLog.source,
                             CrawlLog.duration_ms, CrawlLog.items)
                      .where(CrawlLog.started_at >= datetime.now() - timedelta(days=7))).all()
    if not rows:
        return "<p style='font-family:sans-serif;color:#aaa'>아직 크롤링 로그가 없습니다.</p>"
    df = pd.DataFrame(rows, columns=["started_at", "chain", "status", "source", "duration_ms", "items"])
    fig = px.scatter(df, x="started_at", y="duration_ms", color="chain", symbol="source", size="items",
                     size_max=18, template="plotly_dark", labels={"started_at": "실행 시각", "duration_ms": "소요(ms)"},
                     title="RPA 크롤링 소요 시간 (최근 7일) · 심볼=데이터 출처")
    fig.update_layout(paper_bgcolor="#0b0b12", plot_bgcolor="#0b0b12", margin=dict(l=40, r=20, t=50, b=40), height=360)
    return fig.to_html(include_plotlyjs="cdn", full_html=True, config={"displayModeBar": False})
