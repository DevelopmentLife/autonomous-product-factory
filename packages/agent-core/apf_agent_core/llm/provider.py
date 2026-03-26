from typing import Any, AsyncIterator, Protocol, runtime_checkable
from typing import TypedDict


class LLMMessage(TypedDict):
    role: str   # "system" | "user" | "assistant"
    content: str


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM provider implementations must satisfy."""

    async def complete(
        self,
        messages: list[LLMMessage],
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> str:
        """Send messages and return the full response as a string."""
        ...

    async def stream(
        self,
        messages: list[LLMMessage],
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Send messages and yield response chunks as strings."""
        ...

    async def structured_output(
        self,
        messages: list[LLMMessage],
        schema: type,
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> Any:
        """Send messages and return a validated instance of `schema`."""
        ...
