import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

log = logging.getLogger("movpick.ws")


class ConnectionManager:
    """user_id(None=비로그인) 단위로 WebSocket 연결을 관리하고 이벤트를 송출."""

    def __init__(self) -> None:
        self._conns: dict[int | None, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, user_id: int | None) -> None:
        await ws.accept()
        async with self._lock:
            self._conns[user_id].add(ws)

    async def disconnect(self, ws: WebSocket, user_id: int | None) -> None:
        async with self._lock:
            self._conns[user_id].discard(ws)
            if not self._conns[user_id]:
                self._conns.pop(user_id, None)

    @property
    def count(self) -> int:
        return sum(len(v) for v in self._conns.values())

    async def _send(self, targets: list[tuple[int | None, WebSocket]], event: dict) -> None:
        for uid, ws in targets:
            try:
                await ws.send_json(event)
            except Exception:  # noqa: BLE001 - 끊어진 연결 정리
                await self.disconnect(ws, uid)

    async def broadcast(self, event: dict) -> None:
        await self._send([(uid, ws) for uid, conns in list(self._conns.items()) for ws in list(conns)], event)

    async def send_user(self, user_id: int, event: dict) -> None:
        await self._send([(user_id, ws) for ws in list(self._conns.get(user_id, ()))], event)


manager = ConnectionManager()
