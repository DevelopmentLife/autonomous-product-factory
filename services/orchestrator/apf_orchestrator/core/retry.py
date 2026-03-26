"""Exponential-backoff retry helper for async callables."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_retry(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Call *func* up to *max_attempts* times with exponential back-off.

    On each failure the coroutine sleeps for ``base_delay * 2 ** (attempt - 1)``
    seconds before retrying.  After all attempts are exhausted the last
    exception is re-raised.

    Args:
        func:         Zero-argument async callable to execute.
        max_attempts: Maximum number of total attempts (including the first).
        base_delay:   Base sleep duration in seconds for the first retry.
        exceptions:   Tuple of exception types that trigger a retry; others
                      propagate immediately.

    Returns:
        The return value of *func* on success.

    Raises:
        The last exception raised by *func* once all attempts are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except exceptions as exc:
            last_exc = exc
            if attempt == max_attempts:
                logger.warning(
                    "with_retry: all %d attempts exhausted — raising %s: %s",
                    max_attempts,
                    type(exc).__name__,
                    exc,
                )
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "with_retry: attempt %d/%d failed (%s: %s) — retrying in %.2fs",
                attempt,
                max_attempts,
                type(exc).__name__,
                exc,
                delay,
            )
            await asyncio.sleep(delay)

    # Should never reach here, but satisfies type-checkers.
    raise last_exc  # type: ignore[misc]
