"""Agent-runner worker entrypoint.

Run with:
    python -m apf_agent_runner.main
"""

from __future__ import annotations

import asyncio
import logging
import signal

import structlog

from apf_event_bus import EventBusClient, Streams

from .config import get_config
from .llm_factory import create_llm_provider
from .runner import AgentRunner


def _configure_logging(log_level: str) -> None:
    """Configure structlog with a human-friendly renderer for the given level."""
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


async def main() -> None:
    """Start the agent-runner worker loop."""
    config = get_config()
    _configure_logging(config.LOG_LEVEL)

    log = structlog.get_logger("apf_agent_runner.main")
    log.info(
        "agent_runner_starting",
        worker_id=config.WORKER_ID,
        llm_provider=config.LLM_PROVIDER,
        llm_model=config.LLM_MODEL,
        redis_url=config.REDIS_URL,
    )

    llm = create_llm_provider(config)

    event_bus = EventBusClient(
        redis_url=config.REDIS_URL,
        consumer_group="agent-runner",
        consumer_name=config.WORKER_ID,
    )
    await event_bus.connect()

    # Ensure the consumer group exists before subscribing.
    await event_bus.create_consumer_group(Streams.STAGE_DISPATCH, "agent-runner")

    runner = AgentRunner(llm=llm, event_bus=event_bus, config=config)

    stop_event = asyncio.Event()

    def _handle_signal(sig: signal.Signals) -> None:
        log.info("shutdown_signal_received", signal=sig.name)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig)
        except (NotImplementedError, OSError):
            # Windows does not support add_signal_handler for all signals.
            pass

    log.info("agent_runner_ready", stream=Streams.STAGE_DISPATCH)

    try:
        await event_bus.subscribe(
            Streams.STAGE_DISPATCH,
            handler=runner.handle_dispatch,
            stop_event=stop_event,
        )
    finally:
        await event_bus.disconnect()
        log.info("agent_runner_stopped", worker_id=config.WORKER_ID)


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
