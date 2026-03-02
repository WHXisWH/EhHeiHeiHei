from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket


@dataclass
class _Client:
    client_id: int
    ws: WebSocket
    subscribed_agent_ids: set[str]


class WebSocketHub:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._clients: dict[int, _Client] = {}

    async def connect(self, ws: WebSocket) -> _Client:
        await ws.accept()
        client = _Client(client_id=id(ws), ws=ws, subscribed_agent_ids=set())
        async with self._lock:
            self._clients[client.client_id] = client
        return client

    async def disconnect(self, client: _Client) -> None:
        async with self._lock:
            self._clients.pop(client.client_id, None)

    async def subscribe(self, client: _Client, agent_ids: list[str]) -> None:
        client.subscribed_agent_ids = set(agent_ids)

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        msg = json.dumps({"type": event_type, "payload": payload}, ensure_ascii=False)
        agent_id = payload.get("agent_id")

        async with self._lock:
            clients = list(self._clients.values())

        for c in clients:
            if agent_id and c.subscribed_agent_ids and str(agent_id) not in c.subscribed_agent_ids:
                continue
            try:
                await c.ws.send_text(msg)
            except Exception:
                # Best-effort; cleanup happens on receive loop errors.
                pass
