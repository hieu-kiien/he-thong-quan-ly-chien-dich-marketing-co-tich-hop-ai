"""In-process event bus để chuyển tiếp sự kiện từ MCP Tool Handler tới luồng SSE của turn."""

from __future__ import annotations

import asyncio
from typing import Any


class AssistantEventBus:
    def __init__(self) -> None:
        self._queues: dict[int, list[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def register(self, message_id: int) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            if message_id not in self._queues:
                self._queues[message_id] = []
            self._queues[message_id].append(q)
        return q

    async def unregister(self, message_id: int, q: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            if message_id in self._queues:
                if q in self._queues[message_id]:
                    self._queues[message_id].remove(q)
                if not self._queues[message_id]:
                    del self._queues[message_id]

    async def publish(self, message_id: int, event_type: str, data: dict[str, Any]) -> None:
        event = {"event": event_type, "data": data}
        # Copy queue list safely
        async with self._lock:
            queues = list(self._queues.get(message_id, []))
        for q in queues:
            await q.put(event)


event_bus = AssistantEventBus()
