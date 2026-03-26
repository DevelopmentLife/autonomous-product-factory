from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import openai

from .provider import LLMMessage

logger = logging.getLogger(__name__)

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 1.0  # seconds


class OpenAIProvider:
    """LLMProvider implementation backed by OpenAI's AsyncOpenAI client."""

    def __init__(self, api_key: str, client: openai.AsyncOpenAI | None = None) -> None:
        self._client = client or openai.AsyncOpenAI(api_key=api_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_openai_messages(self, messages: list[LLMMessage]) -> list[dict[str, str]]:
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    async def _call_with_retry(self, coro_factory, attempt: int = 0):  # type: ignore[return]
        """Execute a coroutine factory with exponential backoff on rate-limit errors."""
        try:
            return await coro_factory()
        except openai.RateLimitError as exc:
            if attempt >= _RETRY_ATTEMPTS - 1:
                raise
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("OpenAI rate limit hit; retrying in %.1fs (attempt %d)", delay, attempt + 1)
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
        oai_msgs = self._to_openai_messages(messages)

        def factory():
            return self._client.chat.completions.create(
                model=model,
                messages=oai_msgs,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
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
        oai_msgs = self._to_openai_messages(messages)

        async with await self._client.chat.completions.create(
            model=model,
            messages=oai_msgs,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            **kwargs,
        ) as stream:
            async for chunk in stream:
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
        """Use JSON mode to obtain a response matching `schema`."""
        oai_msgs = self._to_openai_messages(messages)
        schema_name = getattr(schema, "__name__", str(schema))

        # Append instruction to return JSON
        oai_msgs = oai_msgs + [
            {
                "role": "user",
                "content": (
                    f"Respond ONLY with a valid JSON object that matches the {schema_name} schema. "
                    "Do not include any prose, markdown fences, or explanation."
                ),
            }
        ]

        def factory():
            return self._client.chat.completions.create(
                model=model,
                messages=oai_msgs,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
                **kwargs,
            )

        response = await self._call_with_retry(factory)
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        if hasattr(schema, "model_validate"):
            return schema.model_validate(data)
        return schema(**data)
