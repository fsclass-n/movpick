from datetime import date, datetime, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from rpa import seatmap
from rpa.service import CHAIN_LABELS

from ..db import get_db
from ..models import Showtime
from ..schemas import ShowtimeOut

router = APIRouter(prefix="/api", tags=["showtimes"])


def _day_range(day: date | None) -> tuple[datetime, datetime]:
    d = day or date.today()
    start = datetime(d.year, d.month, d.day)
    return start, start + timedelta(days=1, hours=6)


@router.get("/chains")
def chains():
    return [{"id": k, "label": v} for k, v in CHAIN_LABELS.items()]


@router.get("/showtimes", response_model=list[ShowtimeOut])
def list_showtimes(
    day: date | None = Query(None, alias="date"),
    chain: str | None = None,
    q: str | None = Query(None, max_length=50),
    theater: str | None = None,
    upcoming: bool = True,
    db: Session = Depends(get_db),
):
    start, end = _day_range(day)
    stmt = select(Showtime).where(Showtime.start_at >= start, Showtime.start_at < end)
    if upcoming:
        stmt = stmt.where(Showtime.start_at > datetime.now() - timedelta(minutes=10))
    if chain:
        stmt = stmt.where(Showtime.chain == chain)
    if theater:
        stmt = stmt.where(Showtime.theater == theater)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Showtime.movie_title.like(like), Showtime.theater.like(like)))
    return db.scalars(stmt.order_by(Showtime.start_at, Showtime.theater).limit(1000)).all()


@router.get("/movies")
def movies(day: date | None = Query(None, alias="date"), db: Session = Depends(get_db)):
    """영화별 상영 회차 · 평균 예매율 · 잔여석 요약 (pandas 집계)"""
    start, end = _day_range(day)
    rows = db.execute(
        select(Showtime.movie_title, Showtime.rating, Showtime.poster_url, Showtime.chain,
               Showtime.total_seats, Showtime.available_seats)
        .where(Showtime.start_at >= start, Showtime.start_at < end)
    ).all()
    if not rows:
        return []
    df = pd.DataFrame(rows, columns=["title", "rating", "poster_url", "chain", "total", "available"])
    g = df.groupby("title").agg(
        rating=("rating", "first"),
        poster_url=("poster_url", lambda s: next((x for x in s if x), None)),
        chains=("chain", lambda s: sorted(set(s))),
        showtimes=("chain", "size"),
        total=("total", "sum"),
        available=("available", "sum"),
    )
    g["booking_rate"] = (1 - g.available / g.total.clip(lower=1)).round(3)
    g = g.sort_values(["booking_rate", "showtimes"], ascending=False).reset_index()
    return g.to_dict(orient="records")


@router.get("/showtimes/{showtime_id}", response_model=ShowtimeOut)
def get_showtime(showtime_id: int, db: Session = Depends(get_db)):
    st = db.get(Showtime, showtime_id)
    if not st:
        raise HTTPException(404, "상영 정보를 찾을 수 없습니다.")
    return st


@router.get("/showtimes/{showtime_id}/seats")
def seats(showtime_id: int, db: Session = Depends(get_db)):
    st = db.get(Showtime, showtime_id)
    if not st or not st.seat_layout:
        raise HTTPException(404, "좌석 정보를 찾을 수 없습니다.")
    layout = st.seat_layout
    free = seatmap.free_seats(layout)
    prime_free = sorted((s for s in layout["prime"] if s in free), key=lambda s: -layout["scores"][s])
    return {
        "showtime": ShowtimeOut.model_validate(st),
        "rows": layout["rows"],
        "cols": layout["cols"],
        "aisles": layout["aisles"],
        "blocked": layout.get("blocked", []),
        "prime": layout["prime"],
        "taken": layout["taken"],
        "scores": layout["scores"],
        "prime_free": prime_free,
        "recommended": prime_free[:4] or sorted(free, key=lambda s: -layout["scores"][s])[:4],
        "estimated": st.source == "real",
    }


POSTER_PRIORITY = {"lotte": 0, "cgv": 1, "megabox": 2}  # 고해상도 포스터 우선


def _popular(df: pd.DataFrame, n: int = 5) -> list[dict]:
    """인기 순위: 오늘 판매 좌석 수 합계 기준 (회차 수가 적은 영화의 예매율 왜곡 방지)"""
    posters = (df.dropna(subset=["poster_url"]).assign(p=lambda d: d.chain.map(POSTER_PRIORITY))
               .sort_values("p").groupby("title").poster_url.first())
    g = df.groupby("title").agg(sold=("sold", "sum"), total=("total", "sum"), showtimes=("chain", "size"),
                                rating=("rating", "first"), chains=("chain", lambda s: sorted(set(s))))
    g["rate"] = (g.sold / g.total.clip(lower=1)).round(3)
    g = g.sort_values(["sold", "rate"], ascending=False).head(n)
    return [{"title": t, "poster_url": posters.get(t), "rating": r.rating, "sold": int(r.sold), "rate": float(r.rate),
             "showtimes": int(r.showtimes), "chains": [CHAIN_LABELS.get(c, c) for c in r.chains]}
            for t, r in g.iterrows()]


@router.get("/stats/booking-rates")
def booking_rates(db: Session = Depends(get_db)):
    """로그인 화면 실시간 예매율 비주얼용 통계"""
    start, end = _day_range(None)
    rows = db.execute(
        select(Showtime.movie_title, Showtime.chain, Showtime.total_seats, Showtime.available_seats, Showtime.source,
               Showtime.rating, Showtime.poster_url)
        .where(Showtime.start_at >= start, Showtime.start_at < end)
    ).all()
    if not rows:
        return {"movies": [], "top": [], "chains": [], "totals": {"showtimes": 0, "seats": 0, "available": 0},
                "updated_at": None}
    df = pd.DataFrame(rows, columns=["title", "chain", "total", "available", "source", "rating", "poster_url"])
    df["sold"] = df.total - df.available

    def rate(frame: pd.DataFrame, key: str) -> list[dict]:
        g = frame.groupby(key)[["total", "sold"]].sum()
        g["rate"] = (g.sold / g.total.clip(lower=1)).round(3)
        return [{"name": CHAIN_LABELS.get(k, k), "rate": float(v)} for k, v in g.rate.sort_values(ascending=False).items()]

    return {
        "movies": rate(df, "title")[:5],
        "top": _popular(df),
        "chains": rate(df, "chain"),
        "totals": {"showtimes": int(len(df)), "seats": int(df.total.sum()), "available": int(df.available.sum())},
        "live_ratio": round(float((df.source == "real").mean()), 3),
        "updated_at": datetime.now().isoformat(),
    }
