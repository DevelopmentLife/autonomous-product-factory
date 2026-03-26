"""Factory function to create an LLMProvider from configuration."""

from __future__ import annotations

from apf_agent_core import AnthropicProvider, LiteLLMProvider, LLMProvider, OpenAIProvider

from .config import AgentRunnerConfig


def create_llm_provider(config: AgentRunnerConfig) -> LLMProvider:
    """Instantiate and return the correct LLMProvider based on *config*.

    Raises ``ValueError`` if the configured provider is unknown or the
    required API key is missing.
    """
    provider = config.LLM_PROVIDER

    if provider == "anthropic":
        if not config.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY must be set when LLM_PROVIDER=anthropic"
            )
        return AnthropicProvider(api_key=config.ANTHROPIC_API_KEY)

    if provider == "openai":
        if not config.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY must be set when LLM_PROVIDER=openai"
            )
        return OpenAIProvider(api_key=config.OPENAI_API_KEY)

    if provider == "litellm":
        # LiteLLM reads keys from environment variables itself.
        return LiteLLMProvider()

    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")
