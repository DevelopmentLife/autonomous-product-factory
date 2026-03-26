from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import anthropic

from .provider import LLMMessage

logger = logging.getLogger(__name__)

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 1.0  # seconds


class AnthropicProvider:
    """LLMProvider implementation backed by Anthropic's AsyncAnthropic client."""

    def __init__(self, api_key: str, client: anthropic.AsyncAnthropic | None = None) -> None:
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_messages(
        self, messages: list[LLMMessage]
    ) -> tuple[str, list[dict[str, str]]]:
        """Separate the optional leading system message from the rest."""
        system = ""
        chat: list[dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system" and not chat:
                system = msg["content"]
            else:
                chat.append({"role": msg["role"], "content": msg["content"]})
        return system, chat

    async def _call_with_retry(self, coro_factory, attempt: int = 0):  # type: ignore[return]
        """Execute a coroutine factory with exponential backoff on rate-limit errors."""
        try:
            return await coro_factory()
        except anthropic.RateLimitError as exc:
            if attempt >= _RETRY_ATTEMPTS - 1:
                raise
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Anthropic rate limit hit; retrying in %.1fs (attempt %d)", delay, attempt + 1)
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
        system, chat = self._split_messages(messages)

        def factory():
            return self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or anthropic.NOT_GIVEN,
                messages=chat,
                **kwargs,
            )

        response = await self._call_with_retry(factory)
        return response.content[0].text  # type: ignore[index]

    async def stream(
        self,
        messages: list[LLMMessage],
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        system, chat = self._split_messages(messages)

        async with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or anthropic.NOT_GIVEN,
            messages=chat,
            **kwargs,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def structured_output(
        self,
        messages: list[LLMMessage],
        schema: type,
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> Any:
        """Ask the LLM to respond with JSON matching `schema`, then parse."""
        schema_name = getattr(schema, "__name__", str(schema))
        json_instruction: LLMMessage = {
            "role": "user",
            "content": (
                f"Respond ONLY with a valid JSON object that matches the {schema_name} schema. "
                "Do not include any prose, markdown fences, or explanation."
            ),
        }
        augmented = list(messages) + [json_instruction]
        raw = await self.complete(augmented, model, max_tokens, temperature, **kwargs)

        # Strip markdown code fences if the model wraps the JSON anyway
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
