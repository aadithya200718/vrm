from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import AsyncIterator


class EventBroker:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[dict]]] = defaultdict(list)

    async def publish(self, vendor_id: str, payload: dict) -> None:
        for queue in list(self._queues[vendor_id]):
            await queue.put(payload)

    async def subscribe(self, vendor_id: str) -> AsyncIterator[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        self._queues[vendor_id].append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._queues[vendor_id].remove(queue)


broker = EventBroker()

