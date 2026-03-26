"""In-memory event bus backed by asyncio.Queue — drop-in for unit tests."""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable

from .schemas import BaseEvent

logger = logging.getLogger(__name__)


class InMemoryEventBus:
    """asyncio.Queue-backed event bus for testing and minimal installs.

    Provides the same async interface as EventBusClient so it can be used
    as a drop-in replacement in tests without a running Redis instance.

    Acknowledged messages are tracked per (stream, message_id) pair so that
    tests can verify acknowledgement behaviour.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[tuple[str, BaseEvent]]] = {}
        self._pending: dict[str, dict[str, BaseEvent]] = {}  # stream -> {msg_id: event}
        self._acknowledged: dict[str, set[str]] = {}         # stream -> {msg_id}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_queue(self, stream: str) -> asyncio.Queue[tuple[str, BaseEvent]]:
        if stream not in self._queues:
            self._queues[stream] = asyncio.Queue()
            self._pending[stream] = {}
            self._acknowledged[stream] = set()
        return self._queues[stream]

    # ------------------------------------------------------------------
    # Public interface (mirrors EventBusClient)
    # ------------------------------------------------------------------

    async def publish(self, event: BaseEvent) -> str:
        """Enqueue *event* and return a synthetic message ID."""
        msg_id = f"{id(event)}-{uuid.uuid4().hex[:8]}"
        queue = self._get_queue(event.stream)
        self._pending[event.stream][msg_id] = event
        await queue.put((msg_id, event))
        logger.debug("InMemoryEventBus: published %s → %s (id=%s)", type(event).__name__, event.stream, msg_id)
        return msg_id

    async def consume(
        self,
        stream: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> list[tuple[str, BaseEvent]]:
        """Dequeue up to *count* messages from *stream*.

        Blocks for up to *block_ms* / 1000 seconds if the queue is empty.
        """
        queue = self._get_queue(stream)
        results: list[tuple[str, BaseEvent]] = []

        # Try to get the first message, optionally blocking
        timeout_s = block_ms / 1000.0
        try:
            msg_id, event = await asyncio.wait_for(queue.get(), timeout=timeout_s)
            results.append((msg_id, event))
        except asyncio.TimeoutError:
            return []

        # Drain any additional immediately-available messages up to *count*
        while len(results) < count:
            try:
                msg_id, event = queue.get_nowait()
                results.append((msg_id, event))
            except asyncio.QueueEmpty:
                break

        return results

    async def acknowledge(self, stream: str, message_id: str) -> None:
        """Mark *message_id* as acknowledged and remove it from pending."""
        pending = self._pending.get(stream, {})
        if message_id in pending:
            del pending[message_id]
        acked = self._acknowledged.setdefault(stream, set())
        acked.add(message_id)
        logger.debug("InMemoryEventBus: acknowledged %s on %s", message_id, stream)

    async def subscribe(
        self,
        stream: str,
        handler: Callable[[BaseEvent], Awaitable[None]],
        *,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Consume loop: read → call *handler* → ack.

        Runs until *stop_event* is set or the coroutine is cancelled.
        """
        logger.info("InMemoryEventBus: subscribing to stream '%s'", stream)
        while stop_event is None or not stop_event.is_set():
            try:
                messages = await self.consume(stream, block_ms=200)
            except asyncio.CancelledError:
                logger.info("InMemoryEventBus: subscribe() cancelled — exiting.")
                break

            for msg_id, event in messages:
                if stop_event is not None and stop_event.is_set():
                    break
                try:
                    await handler(event)
                    await self.acknowledge(stream, msg_id)
                except asyncio.CancelledError:
                    logger.info("InMemoryEventBus: handler cancelled for %s — exiting.", msg_id)
                    return
                except Exception:
                    logger.exception(
                        "InMemoryEventBus: handler raised for message %s — left unacknowledged.",
                        msg_id,
                    )

        logger.info("InMemoryEventBus: subscribe() loop exited for stream '%s'.", stream)

    # ------------------------------------------------------------------
    # Test-support helpers (not on EventBusClient)
    # ------------------------------------------------------------------

    def pending_count(self, stream: str) -> int:
        """Return the number of unacknowledged messages on *stream*."""
        return len(self._pending.get(stream, {}))

    def acknowledged_ids(self, stream: str) -> set[str]:
        """Return the set of acknowledged message IDs for *stream*."""
        return set(self._acknowledged.get(stream, set()))
