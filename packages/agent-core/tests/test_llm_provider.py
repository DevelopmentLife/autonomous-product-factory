"""
Tests for AnthropicProvider, OpenAIProvider, and LiteLLMProvider.

All external SDK clients are mocked — no real API calls are made.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from apf_agent_core.llm.anthropic import AnthropicProvider
from apf_agent_core.llm.openai import OpenAIProvider
from apf_agent_core.llm.litellm import LiteLLMProvider
from apf_agent_core.llm.provider import LLMMessage
from apf_agent_core.artifacts import PRDArtifact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MESSAGES: list[LLMMessage] = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Tell me about APF."},
]

SAMPLE_PRD_JSON = json.dumps({
    "agent_name": "prd-agent",
    "executive_summary": "Build APF",
    "target_users": ["developers"],
    "core_features": ["pipeline"],
    "success_metrics": ["100 users"],
    "out_of_scope": [],
})


def _make_anthropic_response(text: str) -> MagicMock:
    """Simulate an anthropic.types.Message."""
    msg = MagicMock()
    content_block = MagicMock()
    content_block.text = text
    msg.content = [content_block]
    return msg


def _make_openai_response(text: str) -> MagicMock:
    """Simulate an openai ChatCompletion response."""
    resp = MagicMock()
    choice = MagicMock()
    choice.message.content = text
    resp.choices = [choice]
    return resp


def _make_litellm_response(text: str) -> MagicMock:
    """Simulate a litellm ModelResponse."""
    resp = MagicMock()
    choice = MagicMock()
    choice.message.content = text
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# AnthropicProvider
# ---------------------------------------------------------------------------

class TestAnthropicProvider:

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.messages = MagicMock()
        client.messages.create = AsyncMock(
            return_value=_make_anthropic_response("Hello from Anthropic!")
        )
        # stream context manager
        stream_ctx = MagicMock()
        stream_ctx.__aenter__ = AsyncMock(return_value=stream_ctx)
        stream_ctx.__aexit__ = AsyncMock(return_value=False)

        async def _text_stream():
            for chunk in ["Hello", " world"]:
                yield chunk

        stream_ctx.text_stream = _text_stream()
        client.messages.stream = MagicMock(return_value=stream_ctx)
        return client

    @pytest.fixture
    def provider(self, mock_client):
        return AnthropicProvider(api_key="sk-fake", client=mock_client)

    @pytest.mark.asyncio
    async def test_complete_returns_string(self, provider):
        result = await provider.complete(MESSAGES, model="claude-opus-4-6")
        assert isinstance(result, str)
        assert result == "Hello from Anthropic!"

    @pytest.mark.asyncio
    async def test_complete_passes_model(self, provider, mock_client):
        await provider.complete(MESSAGES, model="claude-3-5-sonnet")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-sonnet"

    @pytest.mark.asyncio
    async def test_complete_separates_system_message(self, provider, mock_client):
        await provider.complete(MESSAGES, model="claude-opus-4-6")
        call_kwargs = mock_client.messages.create.call_args[1]
        # System should be extracted into its own param
        assert call_kwargs["system"] == "You are a helpful assistant."
        # messages list should only have the user message
        msgs = call_kwargs["messages"]
        assert all(m["role"] != "system" for m in msgs)

    @pytest.mark.asyncio
    async def test_complete_respects_max_tokens(self, provider, mock_client):
        await provider.complete(MESSAGES, model="claude-opus-4-6", max_tokens=1024)
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 1024

    @pytest.mark.asyncio
    async def test_stream_yields_strings(self, provider):
        chunks = []
        async for chunk in provider.stream(MESSAGES, model="claude-opus-4-6"):
            chunks.append(chunk)
        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_structured_output_returns_pydantic_model(self, provider, mock_client):
        mock_client.messages.create = AsyncMock(
            return_value=_make_anthropic_response(SAMPLE_PRD_JSON)
        )
        result = await provider.structured_output(
            MESSAGES, schema=PRDArtifact, model="claude-opus-4-6"
        )
        assert isinstance(result, PRDArtifact)
        assert result.executive_summary == "Build APF"

    @pytest.mark.asyncio
    async def test_structured_output_strips_markdown_fences(self, provider, mock_client):
        fenced = f"```json\n{SAMPLE_PRD_JSON}\n```"
        mock_client.messages.create = AsyncMock(
            return_value=_make_anthropic_response(fenced)
        )
        result = await provider.structured_output(
            MESSAGES, schema=PRDArtifact, model="claude-opus-4-6"
        )
        assert isinstance(result, PRDArtifact)

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, provider, mock_client):
        import anthropic as sdk

        call_count = 0

        async def _flaky(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise sdk.RateLimitError(
                    message="rate limit",
                    response=MagicMock(status_code=429, headers={}),
                    body={},
                )
            return _make_anthropic_response("Finally!")

        mock_client.messages.create = _flaky

        with patch("apf_agent_core.llm.anthropic.asyncio.sleep", new_callable=AsyncMock):
            result = await provider.complete(MESSAGES, model="claude-opus-4-6")

        assert result == "Finally!"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self, provider, mock_client):
        import anthropic as sdk

        async def _always_rate_limit(*args, **kwargs):
            raise sdk.RateLimitError(
                message="rate limit",
                response=MagicMock(status_code=429, headers={}),
                body={},
            )

        mock_client.messages.create = _always_rate_limit

        with patch("apf_agent_core.llm.anthropic.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(sdk.RateLimitError):
                await provider.complete(MESSAGES, model="claude-opus-4-6")


# ---------------------------------------------------------------------------
# OpenAIProvider
# ---------------------------------------------------------------------------

class TestOpenAIProvider:

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_openai_response("Hello from OpenAI!")
        )
        return client

    @pytest.fixture
    def provider(self, mock_client):
        return OpenAIProvider(api_key="sk-fake", client=mock_client)

    @pytest.mark.asyncio
    async def test_complete_returns_string(self, provider):
        result = await provider.complete(MESSAGES, model="gpt-4o")
        assert isinstance(result, str)
        assert result == "Hello from OpenAI!"

    @pytest.mark.asyncio
    async def test_complete_passes_model(self, provider, mock_client):
        await provider.complete(MESSAGES, model="gpt-4o-mini")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_complete_passes_temperature(self, provider, mock_client):
        await provider.complete(MESSAGES, model="gpt-4o", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_stream_yields_strings(self, provider, mock_client):
        # Mock the async context manager for streaming
        stream_ctx = MagicMock()
        stream_ctx.__aenter__ = AsyncMock(return_value=stream_ctx)
        stream_ctx.__aexit__ = AsyncMock(return_value=False)

        async def _chunks():
            for text in ["Hello", " OpenAI"]:
                chunk = MagicMock()
                chunk.choices[0].delta.content = text
                yield chunk

        stream_ctx.__aiter__ = lambda self: _chunks()
        mock_client.chat.completions.create = AsyncMock(return_value=stream_ctx)

        chunks = []
        async for chunk in provider.stream(MESSAGES, model="gpt-4o"):
            chunks.append(chunk)
        assert chunks == ["Hello", " OpenAI"]

    @pytest.mark.asyncio
    async def test_structured_output_returns_pydantic_model(self, provider, mock_client):
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_openai_response(SAMPLE_PRD_JSON)
        )
        result = await provider.structured_output(
            MESSAGES, schema=PRDArtifact, model="gpt-4o"
        )
        assert isinstance(result, PRDArtifact)
        assert result.target_users == ["developers"]

    @pytest.mark.asyncio
    async def test_structured_output_uses_json_mode(self, provider, mock_client):
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_openai_response(SAMPLE_PRD_JSON)
        )
        await provider.structured_output(MESSAGES, schema=PRDArtifact, model="gpt-4o")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs.get("response_format") == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, provider, mock_client):
        import openai as sdk

        call_count = 0

        async def _flaky(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise sdk.RateLimitError(
                    message="rate limit",
                    response=MagicMock(status_code=429, headers={}),
                    body={},
                )
            return _make_openai_response("Finally!")

        mock_client.chat.completions.create = _flaky

        with patch("apf_agent_core.llm.openai.asyncio.sleep", new_callable=AsyncMock):
            result = await provider.complete(MESSAGES, model="gpt-4o")

        assert result == "Finally!"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self, provider, mock_client):
        import openai as sdk

        async def _always_rate_limit(*args, **kwargs):
            raise sdk.RateLimitError(
                message="rate limit",
                response=MagicMock(status_code=429, headers={}),
                body={},
            )

        mock_client.chat.completions.create = _always_rate_limit

        with patch("apf_agent_core.llm.openai.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(sdk.RateLimitError):
                await provider.complete(MESSAGES, model="gpt-4o")


# ---------------------------------------------------------------------------
# LiteLLMProvider
# ---------------------------------------------------------------------------

class TestLiteLLMProvider:

    @pytest.fixture
    def provider(self):
        return LiteLLMProvider()

    @pytest.mark.asyncio
    async def test_complete_returns_string(self, provider):
        with patch("apf_agent_core.llm.litellm.litellm.acompletion") as mock_acomp:
            mock_acomp.return_value = _make_litellm_response("Hello from LiteLLM!")
            # Make it awaitable
            async def _acomp(*args, **kwargs):
                return _make_litellm_response("Hello from LiteLLM!")
            mock_acomp.side_effect = _acomp

            result = await provider.complete(MESSAGES, model="ollama/mistral")
            assert isinstance(result, str)
            assert result == "Hello from LiteLLM!"

    @pytest.mark.asyncio
    async def test_complete_passes_model_string(self, provider):
        with patch("apf_agent_core.llm.litellm.litellm.acompletion") as mock_acomp:
            async def _acomp(*args, **kwargs):
                return _make_litellm_response("ok")
            mock_acomp.side_effect = _acomp

            await provider.complete(MESSAGES, model="groq/llama3-70b")
            call_kwargs = mock_acomp.call_args[1]
            assert call_kwargs["model"] == "groq/llama3-70b"

    @pytest.mark.asyncio
    async def test_stream_yields_strings(self, provider):
        async def _chunks():
            for text in ["chunk1", " chunk2"]:
                chunk = MagicMock()
                chunk.choices[0].delta.content = text
                yield chunk

        with patch("apf_agent_core.llm.litellm.litellm.acompletion") as mock_acomp:
            async def _acomp(*args, **kwargs):
                return _chunks()
            mock_acomp.side_effect = _acomp

            chunks = []
            async for c in provider.stream(MESSAGES, model="ollama/mistral"):
                chunks.append(c)
            assert chunks == ["chunk1", " chunk2"]

    @pytest.mark.asyncio
    async def test_structured_output_returns_pydantic_model(self, provider):
        with patch("apf_agent_core.llm.litellm.litellm.acompletion") as mock_acomp:
            async def _acomp(*args, **kwargs):
                return _make_litellm_response(SAMPLE_PRD_JSON)
            mock_acomp.side_effect = _acomp

            result = await provider.structured_output(
                MESSAGES, schema=PRDArtifact, model="ollama/mistral"
            )
            assert isinstance(result, PRDArtifact)
            assert result.core_features == ["pipeline"]

    @pytest.mark.asyncio
    async def test_structured_output_strips_markdown_fences(self, provider):
        fenced = f"```json\n{SAMPLE_PRD_JSON}\n```"
        with patch("apf_agent_core.llm.litellm.litellm.acompletion") as mock_acomp:
            async def _acomp(*args, **kwargs):
                return _make_litellm_response(fenced)
            mock_acomp.side_effect = _acomp

            result = await provider.structured_output(
                MESSAGES, schema=PRDArtifact, model="ollama/mistral"
            )
            assert isinstance(result, PRDArtifact)

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, provider):
        import litellm as litellm_mod

        call_count = 0

        async def _flaky(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise litellm_mod.RateLimitError(
                    message="rate limit",
                    llm_provider="test",
                    model="test-model",
                )
            return _make_litellm_response("Finally!")

        with patch("apf_agent_core.llm.litellm.litellm.acompletion", side_effect=_flaky):
            with patch("apf_agent_core.llm.litellm.asyncio.sleep", new_callable=AsyncMock):
                result = await provider.complete(MESSAGES, model="ollama/mistral")

        assert result == "Finally!"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self, provider):
        import litellm as litellm_mod

        async def _always_rate_limit(*args, **kwargs):
            raise litellm_mod.RateLimitError(
                message="rate limit",
                llm_provider="test",
                model="test-model",
            )

        with patch("apf_agent_core.llm.litellm.litellm.acompletion", side_effect=_always_rate_limit):
            with patch("apf_agent_core.llm.litellm.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(litellm_mod.RateLimitError):
                    await provider.complete(MESSAGES, model="ollama/mistral")

    @pytest.mark.asyncio
    async def test_default_kwargs_forwarded(self):
        """Constructor kwargs (e.g. api_base) are forwarded to acompletion."""
        provider = LiteLLMProvider(api_base="http://localhost:11434")
        with patch("apf_agent_core.llm.litellm.litellm.acompletion") as mock_acomp:
            async def _acomp(*args, **kwargs):
                return _make_litellm_response("ok")
            mock_acomp.side_effect = _acomp

            await provider.complete(MESSAGES, model="ollama/mistral")
            call_kwargs = mock_acomp.call_args[1]
            assert call_kwargs.get("api_base") == "http://localhost:11434"
