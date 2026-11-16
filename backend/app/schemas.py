from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .security import PASSWORD_RULE_MESSAGE, validate_password

EMAIL_RULE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str
    provider: str
    is_active: bool
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginIn(BaseModel):
    email: str = Field(pattern=EMAIL_RULE)
    password: str = Field(min_length=1, max_length=64)


class SignupIn(BaseModel):
    email: str = Field(pattern=EMAIL_RULE)
    name: str = Field(min_length=1, max_length=50)
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        if not validate_password(v):
            raise ValueError(PASSWORD_RULE_MESSAGE)
        return v


class RoleIn(BaseModel):
    role: Literal["user", "admin"]


class ShowtimeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chain: str
    theater: str
    screen: str
    movie_title: str
    rating: str | None
    start_at: datetime
    end_at: datetime | None
    total_seats: int
    available_seats: int
    source: str
    booking_url: str | None
    poster_url: str | None = None
    updated_at: datetime | None = None


class WatchIn(BaseModel):
    showtime_id: int
    mode: Literal["prime", "custom"] = "prime"
    seats: list[str] = Field(default_factory=list, max_length=20)
    channels: list[Literal["web", "telegram", "discord", "email"]] = Field(default_factory=lambda: ["web"])


class WatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    showtime_id: int
    mode: str
    seats: list[str] | None
    channels: list[str] | None
    active: bool
    created_at: datetime | None
    showtime: ShowtimeOut


class CrawlLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job: str
    chain: str
    status: str
    source: str
    items: int
    duration_ms: int
    message: str | None
    trigger: str
    started_at: datetime


class CrawlerConfigIn(BaseModel):
    interval_minutes: int = Field(ge=5, le=1440)
    enabled: bool = True
