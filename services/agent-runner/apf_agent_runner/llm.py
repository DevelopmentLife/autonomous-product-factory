from __future__ import annotations
from typing import Protocol, AsyncIterator, Any, runtime_checkable
from pydantic import BaseModel


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, messages: list[dict], model: str,
                       max_tokens: int = 4096, temperature: float = 0.3) -> str: ...

    async def stream(self, messages: list[dict], model: str,
                     max_tokens: int = 4096) -> AsyncIterator[str]: ...


_MOCK_JSON = (
    '{"executive_summary":"Mock pipeline run — no LLM key configured.",'
    '"target_users":["developers","product managers"],'
    '"core_features":["feature A","feature B","feature C"],'
    '"success_metrics":["metric 1","metric 2"],'
    '"out_of_scope":[],"risks":[],"competitors":[],"user_personas":[],'
    '"milestones":[],"phases":[],"test_strategy":"unit + integration",'
    '"coverage_targets":{"unit":80},"approval":"approved",'
    '"verdict":"approved","comments":[],"blockers":[],'
    '"infrastructure":[],"services":[],"deployment_steps":[],'
    '"summary":"Mock artifact — set an LLM API key for real output."}'
)


class MockLLMProvider:
    """Returns deterministic stub JSON for every agent call.

    Enables running the full 11-stage pipeline locally with zero API keys.
    Every agent can parse the response; artifacts will contain placeholder text.
    """

    def __init__(self, response: str | None = None):
        self._response = response or _MOCK_JSON

    async def complete(self, messages: list[dict], model: str,
                       max_tokens: int = 4096, temperature: float = 0.3) -> str:
        return self._response

    async def stream(self, messages: list[dict], model: str, max_tokens: int = 4096):
        for word in self._response.split():
            yield word + ' '


def create_llm_provider(settings) -> LLMProvider:
    # Explicit mock mode — skips all API calls regardless of keys present
    if getattr(settings, 'MOCK_LLM', False):
        return MockLLMProvider()

    if settings.LLM_PROVIDER == 'anthropic' and settings.ANTHROPIC_API_KEY:
        from .providers.anthropic import AnthropicProvider
        return AnthropicProvider(settings.ANTHROPIC_API_KEY, settings.LLM_MODEL)
    elif settings.LLM_PROVIDER == 'openai' and settings.OPENAI_API_KEY:
        from .providers.openai import OpenAIProvider
        return OpenAIProvider(settings.OPENAI_API_KEY, settings.LLM_MODEL)
    elif settings.LLM_PROVIDER == 'litellm' and settings.LITELLM_BASE_URL:
        from .providers.litellm import LiteLLMProvider
        return LiteLLMProvider(settings.LITELLM_BASE_URL, settings.LLM_MODEL)

    # Fallback: no key configured — use mock so the pipeline still runs
    import logging
    logging.getLogger(__name__).warning(
        'No LLM API key configured. Running in MOCK mode. '
        'Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or MOCK_LLM=true to suppress this warning.'
    )
    return MockLLMProvider()
