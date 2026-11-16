"""원격 RPA 수집기 수신 API.

CGV 등 해외 데이터센터 IP(Render)를 차단하는 사이트는 국내 PC/서버에서
`python -m rpa.runner --chain cgv --push <API>` 로 수집한 결과를 이 엔드포인트로 전송한다.
"""

import secrets
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from rpa.models import CrawlResult, ShowtimeData

from ..config import settings
from ..services.crawler import crawler

router = APIRouter(prefix="/api/rpa", tags=["rpa"])


class IngestItem(BaseModel):
    external_id: str = Field(min_length=1, max_length=128)
    theater: str = Field(max_length=100)
    screen: str = Field(max_length=100)
    movie_title: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime | None = None
    total_seats: int = Field(ge=1, le=2000)
    available_seats: int = Field(ge=0, le=2000)
    rating: str | None = Field(None, max_length=20)
    booking_url: str | None = Field(None, max_length=500)
    poster_url: str | None = Field(None, max_length=500)


class IngestIn(BaseModel):
    chain: Literal["cgv", "megabox", "lotte"]
    date: date
    items: list[IngestItem] = Field(min_length=1, max_length=3000)
    duration_ms: int = Field(0, ge=0)
    collector: str = Field("remote", max_length=50)


def _check_token(token: str | None) -> None:
    if not settings.rpa_ingest_token:
        raise HTTPException(404, "원격 수집 수신이 비활성화되어 있습니다. (RPA_INGEST_TOKEN 미설정)")
    if not token or not secrets.compare_digest(token, settings.rpa_ingest_token):
        raise HTTPException(401, "유효하지 않은 수집기 토큰입니다.")


@router.get("/ping")
def ping(x_rpa_token: str | None = Header(None)):
    """수집기 설치 시 토큰 확인용 (데이터 변경 없음)"""
    _check_token(x_rpa_token)
    return {"ok": True}


@router.post("/ingest")
async def ingest(body: IngestIn, x_rpa_token: str | None = Header(None)):
    _check_token(x_rpa_token)
    items = [ShowtimeData(chain=body.chain, source="real", **i.model_dump()) for i in body.items]
    result = CrawlResult(body.chain, items, "real", True, body.duration_ms,
                         f"원격 수집기({body.collector}) {len(items)}건 수신", body.date)
    return {"saved": await crawler.ingest(result, body.collector)}
