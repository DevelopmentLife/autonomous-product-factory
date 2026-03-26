from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import litellm

from .provider import LLMMessage

logger = logging.getLogger(__name__)

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 1.0  # seconds


class LiteLLMProvider:
    """
    LLMProvider implementation backed by litellm.acompletion.

    Supports any model string accepted by litellm (anthropic/, openai/,
    ollama/, groq/, mistral/, etc.).
    """

    def __init__(self, **litellm_kwargs: Any) -> None:
        """
        Optional keyword arguments are forwarded to every acompletion call
        (e.g. api_key, api_base for local models).
        """
        self._default_kwargs = litellm_kwargs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_litellm_messages(self, messages: list[LLMMessage]) -> list[dict[str, str]]:
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    async def _call_with_retry(self, coro_factory, attempt: int = 0):  # type: ignore[return]
        """Execute a coroutine factory with exponential backoff on rate-limit errors."""
        try:
            return await coro_factory()
        except litellm.RateLimitError as exc:
            if attempt >= _RETRY_ATTEMPTS - 1:
                raise
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("LiteLLM rate limit hit; retrying in %.1fs (attempt %d)", delay, attempt + 1)
            await asyncio.sleep(delay)
            return await self._call_with_retry(coro_factory, attempt + 1)

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[LLMMessage],
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> str:
        ll_msgs = self._to_litellm_messages(messages)
        merged = {**self._default_kwargs, **kwargs}

        def factory():
            return litellm.acompletion(
                model=model,
                messages=ll_msgs,
                max_tokens=max_tokens,
                temperature=temperature,
                **merged,
            )

        response = await self._call_with_retry(factory)
        return response.choices[0].message.content or ""

    async def stream(
        self,
        messages: list[LLMMessage],
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        ll_msgs = self._to_litellm_messages(messages)
        merged = {**self._default_kwargs, **kwargs}

        response = await litellm.acompletion(
            model=model,
            messages=ll_msgs,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            **merged,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def structured_output(
        self,
        messages: list[LLMMessage],
        schema: type,
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> Any:
        """Ask the model to return JSON matching `schema`, then parse and validate."""
        schema_name = getattr(schema, "__name__", str(schema))
        augmented = self._to_litellm_messages(messages) + [
            {
                "role": "user",
                "content": (
                    f"Respond ONLY with a valid JSON object that matches the {schema_name} schema. "
                    "Do not include any prose, markdown fences, or explanation."
                ),
            }
        ]
        merged = {**self._default_kwargs, **kwargs}

        def factory():
            return litellm.acompletion(
                model=model,
                messages=augmented,
                max_tokens=max_tokens,
                temperature=temperature,
                **merged,
            )

        response = await self._call_with_retry(factory)
        raw = response.choices[0].message.content or "{}"

        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)
        if hasattr(schema, "model_validate"):
            return schema.model_validate(data)
        return schema(**data)
