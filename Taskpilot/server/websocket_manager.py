from fastapi import WebSocket
from typing import Set, Any, Dict, Optional
import asyncio

class WebSocketManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._credentials_event = asyncio.Event()
        self._credentials: Optional[Dict[str, str]] = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)

    async def broadcast_json(self, message: Dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self._connections)
        if not connections:
            return
        await asyncio.gather(
            *[self._safe_send(ws, message) for ws in connections],
            return_exceptions=True,
        )

    async def _safe_send(self, ws: WebSocket, message: Dict[str, Any]) -> None:
        try:
            await ws.send_json(message)
        except Exception:
            await self.disconnect(ws)

    async def send_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        await self.broadcast_json({"type": event_type, **payload})

    async def send_log(self, level: str, message: str) -> None:
        await self.send_event("LOG", {"level": level, "message": message})

    async def send_frame(self, image_base64: str, source: str | None = None) -> None:
        payload = {"image": image_base64}
        if source:
            payload["source"] = source
        await self.send_event("BROWSER_FRAME", payload)

    async def request_credentials(self, fields: Dict[str, bool]) -> Dict[str, str]:
        self._credentials_event.clear()
        self._credentials = None
        await self.send_event("CREDENTIALS_REQUIRED", {"fields": fields})
        await self._credentials_event.wait()
        return self._credentials or {}

    def set_credentials(self, data: Dict[str, str]) -> None:
        self._credentials = data
        self._credentials_event.set()
