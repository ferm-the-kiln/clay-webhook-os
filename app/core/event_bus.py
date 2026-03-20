import asyncio
import json
import logging

logger = logging.getLogger("clay-webhook-os")


class EventBus:
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def publish(self, event_type: str, data: dict) -> None:
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        stale = []
        for q in self._subscribers:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                stale.append(q)
        # Remove subscribers with permanently full queues to prevent leak
        for q in stale:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass
        if stale:
            logger.info("[event_bus] Removed %d stale subscribers (full queue)", len(stale))
