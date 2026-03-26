from __future__ import annotations
from typing import Protocol, AsyncIterator, Any, runtime_checkable
from pydantic import BaseModel


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, messages: list[dict], model: str,
                       max_tokens: int = 4096, temperature: float = 0.3) -> str: ...

    async def stream(self, messages: list[dict], model: str,
                     max_tokens: int = 4096) -> AsyncIterator[str]: ...


class MockLLMProvider:
    def __init__(self, response: str = 'Mock LLM response'):
        self._response = response

    async def complete(self, messages: list[dict], model: str,
                       max_tokens: int = 4096, temperature: float = 0.3) -> str:
        return self._response

    async def stream(self, messages: list[dict], model: str, max_tokens: int = 4096):
        for word in self._response.split():
            yield word + ' '


def create_llm_provider(settings) -> LLMProvider:
    if settings.LLM_PROVIDER == 'anthropic' and settings.ANTHROPIC_API_KEY:
        from .providers.anthropic import AnthropicProvider
        return AnthropicProvider(settings.ANTHROPIC_API_KEY, settings.LLM_MODEL)
    elif settings.LLM_PROVIDER == 'openai' and settings.OPENAI_API_KEY:
        from .providers.openai import OpenAIProvider
        return OpenAIProvider(settings.OPENAI_API_KEY, settings.LLM_MODEL)
    return MockLLMProvider(f'[{settings.LLM_MODEL}] Simulated response for testing')
