from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import SeatWatch, Showtime, User
from ..schemas import WatchIn, WatchOut
from ..security import get_current_user
from ..services.monitor import free_targets
from ..services.notifier import available_channels

router = APIRouter(prefix="/api/watches", tags=["watches"])


@router.get("/channels")
def channels():
    return available_channels()


@router.get("", response_model=list[WatchOut])
def my_watches(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(SeatWatch).options(selectinload(SeatWatch.showtime))
        .where(SeatWatch.user_id == user.id).order_by(SeatWatch.created_at.desc())
    ).all()


@router.post("", status_code=201)
def create_watch(body: WatchIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    st = db.get(Showtime, body.showtime_id)
    if not st or not st.seat_layout:
        raise HTTPException(404, "상영 정보를 찾을 수 없습니다.")
    valid = set(st.seat_layout["scores"])
    seats = [s for s in body.seats if s in valid]
    if body.mode == "custom" and not seats:
        raise HTTPException(422, "감시할 좌석을 1개 이상 선택하세요.")
    watch = db.scalar(select(SeatWatch).where(SeatWatch.user_id == user.id, SeatWatch.showtime_id == st.id))
    if not watch:
        watch = SeatWatch(user_id=user.id, showtime_id=st.id)
        db.add(watch)
    watch.mode, watch.seats, watch.channels, watch.active = body.mode, seats, body.channels, True
    current = free_targets(watch, st.seat_layout)
    watch.last_notified_seats = current
    db.commit()
    db.refresh(watch)
    return {"watch": WatchOut.model_validate(watch), "available_now": current}


@router.patch("/{watch_id}", response_model=WatchOut)
def toggle_watch(watch_id: int, active: bool, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    watch = db.get(SeatWatch, watch_id)
    if not watch or watch.user_id != user.id:
        raise HTTPException(404, "알림 설정을 찾을 수 없습니다.")
    watch.active = active
    db.commit()
    return watch


@router.delete("/{watch_id}", status_code=204)
def delete_watch(watch_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    watch = db.get(SeatWatch, watch_id)
    if not watch or watch.user_id != user.id:
        raise HTTPException(404, "알림 설정을 찾을 수 없습니다.")
    db.delete(watch)
    db.commit()
