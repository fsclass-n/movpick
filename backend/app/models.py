from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .accounts import READ_ONLY_EMAILS
from .db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("provider", "provider_id", name="uq_users_provider"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    provider: Mapped[str] = mapped_column(String(20), default="local")
    provider_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    watches: Mapped[list["SeatWatch"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def read_only(self) -> bool:
        """테스트 관리자: 관리자 화면 조회만 허용"""
        return self.email in READ_ONLY_EMAILS


class Showtime(Base):
    __tablename__ = "showtimes"
    __table_args__ = (UniqueConstraint("chain", "external_id", name="uq_showtimes_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain: Mapped[str] = mapped_column(String(20), index=True)
    external_id: Mapped[str] = mapped_column(String(128))
    theater: Mapped[str] = mapped_column(String(100))
    screen: Mapped[str] = mapped_column(String(100))
    movie_title: Mapped[str] = mapped_column(String(200), index=True)
    rating: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_seats: Mapped[int] = mapped_column(Integer, default=0)
    available_seats: Mapped[int] = mapped_column(Integer, default=0)
    seat_layout: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="mock")
    booking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class SeatWatch(Base):
    __tablename__ = "seat_watches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtimes.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(10), default="prime")
    seats: Mapped[list | None] = mapped_column(JSON, nullable=True)
    channels: Mapped[list | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_notified_seats: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user: Mapped[User] = relationship(back_populates="watches")
    showtime: Mapped[Showtime] = relationship()


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job: Mapped[str] = mapped_column(String(30), default="showtimes")
    chain: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(String(10), default="mock")
    items: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str] = mapped_column(String(10), default="schedule")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
