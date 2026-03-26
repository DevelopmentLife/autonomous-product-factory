"""Async Redis Streams event bus client."""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as aioredis
from redis.exceptions import ResponseError

from .schemas import BaseEvent, EVENT_TYPE_MAP

logger = logging.getLogger(__name__)


class EventBusClient:
    """Async Redis Streams client for publishing and consuming APF events.

    Usage:
        bus = EventBusClient(redis_url="redis://localhost:6379", consumer_group="orchestrator", consumer_name="worker-1")
        await bus.connect()
        msg_id = await bus.publish(some_event)
        ...
        await bus.disconnect()
    """

    def __init__(self, redis_url: str, consumer_group: str, consumer_name: str) -> None:
        self._redis_url = redis_url
        self._consumer_group = consumer_group
        self._consumer_name = consumer_name
        self._redis: aioredis.Redis | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Initialize Redis connection and verify it is reachable."""
        self._redis = aioredis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._redis.ping()
        logger.info(
            "EventBusClient connected to %s (group=%s, consumer=%s)",
            self._redis_url,
            self._consumer_group,
            self._consumer_name,
        )

    async def disconnect(self) -> None:
        """Close the Redis connection gracefully."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            logger.info("EventBusClient disconnected.")

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(self, event: BaseEvent) -> str:
        """Serialize *event* to JSON and XADD to the event's stream.

        Returns the Redis message ID assigned by the server.
        """
        self._ensure_connected()
        payload = event.model_dump_json()
        msg_id: str = await self._redis.xadd(event.stream, {"data": payload})  # type: ignore[union-attr]
        logger.debug("Published %s to %s → %s", type(event).__name__, event.stream, msg_id)
        return msg_id

    # ------------------------------------------------------------------
    # Consumer groups
    # ------------------------------------------------------------------

    async def create_consumer_group(
        self,
        stream: str,
        group: str,
        mkstream: bool = True,
    ) -> None:
        """Create a consumer group on *stream*.

        Silently ignores the BUSYGROUP error if the group already exists.
        When *mkstream* is True the stream is created if it does not exist.
        """
        self._ensure_connected()
        try:
            await self._redis.xgroup_create(stream, group, id="0", mkstream=mkstream)  # type: ignore[union-attr]
            logger.debug("Consumer group '%s' created on stream '%s'.", group, stream)
        except ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                logger.debug("Consumer group '%s' already exists on '%s' — skipping.", group, stream)
            else:
                raise

    # ------------------------------------------------------------------
    # Consuming
    # ------------------------------------------------------------------

    async def consume(
        self,
        stream: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> list[tuple[str, BaseEvent]]:
        """Read up to *count* pending messages from *stream* via XREADGROUP.

        Blocks for up to *block_ms* milliseconds waiting for new messages.
        Returns a list of ``(message_id, event)`` tuples.
        """
        self._ensure_connected()
        raw = await self._redis.xreadgroup(  # type: ignore[union-attr]
            self._consumer_group,
            self._consumer_name,
            {stream: ">"},
            count=count,
            block=block_ms,
        )
        if not raw:
            return []

        results: list[tuple[str, BaseEvent]] = []
        for _stream_name, messages in raw:
            for msg_id, fields in messages:
                try:
                    event = self._deserialize(stream, fields)
                    results.append((msg_id, event))
                except Exception:
                    logger.exception("Failed to deserialize message %s on stream %s", msg_id, stream)
        return results

    async def acknowledge(self, stream: str, message_id: str) -> None:
        """Acknowledge *message_id* so it is removed from the PEL."""
        self._ensure_connected()
        await self._redis.xack(stream, self._consumer_group, message_id)  # type: ignore[union-attr]
        logger.debug("Acknowledged message %s on stream %s", message_id, stream)

    # ------------------------------------------------------------------
    # Subscription loop
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        stream: str,
        handler: Callable[[BaseEvent], Awaitable[None]],
        *,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Run a consume loop: read → call *handler* → ack.

        Continues until *stop_event* is set (or forever if none is given).
        Each message is acknowledged only after *handler* returns without raising.
        """
        logger.info(
            "Subscribing to stream '%s' (group=%s, consumer=%s)",
            stream,
            self._consumer_group,
            self._consumer_name,
        )
        while stop_event is None or not stop_event.is_set():
            try:
                messages = await self.consume(stream)
            except asyncio.CancelledError:
                logger.info("subscribe() cancelled — exiting loop.")
                break
            except Exception:
                logger.exception("Error reading from stream '%s' — retrying.", stream)
                await asyncio.sleep(1)
                continue

            for msg_id, event in messages:
                try:
                    await handler(event)
                    await self.acknowledge(stream, msg_id)
                except asyncio.CancelledError:
                    logger.info("Handler cancelled for message %s — exiting loop.", msg_id)
                    return
                except Exception:
                    logger.exception(
                        "Handler raised an exception for message %s — message left unacknowledged.",
                        msg_id,
                    )

        logger.info("subscribe() loop exited for stream '%s'.", stream)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if self._redis is None:
            raise RuntimeError("EventBusClient is not connected. Call await connect() first.")

    @staticmethod
    def _deserialize(stream: str, fields: dict) -> BaseEvent:
        """Deserialize a raw Redis message into the appropriate event type."""
        raw_json: str = fields.get("data", "{}")
        data = json.loads(raw_json)

        # Prefer the stream embedded in the JSON payload; fall back to the
        # stream name the message was read from.
        stream_key = data.get("stream", stream)
        event_cls = EVENT_TYPE_MAP.get(stream_key, BaseEvent)

        # BaseEvent is abstract (requires stream), so pass stream_key if missing
        if "stream" not in data:
            data["stream"] = stream_key

        return event_cls.model_validate(data)
