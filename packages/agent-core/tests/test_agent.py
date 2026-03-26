"""
Tests for apf_agent_core.agent.BaseAgent.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from apf_agent_core.agent import BaseAgent
from apf_agent_core.artifacts import BaseArtifact, PRDArtifact, ArtifactStatus
from apf_agent_core.context import PipelineContext
from apf_agent_core.llm.provider import LLMProvider, LLMMessage


# ---------------------------------------------------------------------------
# Concrete test subclass
# ---------------------------------------------------------------------------

class ConcreteAgent(BaseAgent):
    agent_name = "concrete-agent"
    output_artifact_class = PRDArtifact

    async def execute(self, ctx: PipelineContext) -> PRDArtifact:
        response = await self._call_llm(
            system="You are a helpful assistant.",
            user=ctx.idea,
        )
        return PRDArtifact(
            status=ArtifactStatus.COMPLETE,
            raw_content=response,
            executive_summary=response,
        )


class ConcreteAgentWithStructured(BaseAgent):
    agent_name = "structured-agent"
    output_artifact_class = PRDArtifact

    async def execute(self, ctx: PipelineContext) -> PRDArtifact:
        return await self._structured_output(
            system="You are a helpful assistant.",
            user=ctx.idea,
            schema=PRDArtifact,
        )


# ---------------------------------------------------------------------------
# Tests: cannot instantiate abstract class
# ---------------------------------------------------------------------------

class TestBaseAgentAbstract:
    def test_cannot_instantiate(self, mock_llm):
        with pytest.raises(TypeError):
            BaseAgent(llm=mock_llm)  # type: ignore[abstract]

    def test_concrete_instantiates(self, mock_llm):
        agent = ConcreteAgent(llm=mock_llm)
        assert agent.llm is mock_llm
        assert agent.config == {}

    def test_concrete_with_config(self, mock_llm):
        agent = ConcreteAgent(llm=mock_llm, config={"model": "gpt-4o"})
        assert agent.config["model"] == "gpt-4o"


# ---------------------------------------------------------------------------
# Tests: execute calls LLM correctly
# ---------------------------------------------------------------------------

class TestConcreteAgentExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_artifact(self, mock_llm, pipeline_context):
        agent = ConcreteAgent(llm=mock_llm)
        artifact = await agent.execute(pipeline_context)
        assert isinstance(artifact, PRDArtifact)
        assert artifact.status == ArtifactStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_execute_calls_complete(self, mock_llm, pipeline_context):
        agent = ConcreteAgent(llm=mock_llm)
        await agent.execute(pipeline_context)
        mock_llm.complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_passes_correct_messages(self, mock_llm, pipeline_context):
        agent = ConcreteAgent(llm=mock_llm)
        await agent.execute(pipeline_context)

        call_args = mock_llm.complete.call_args
        messages: list[LLMMessage] = call_args[0][0]  # positional arg 0

        assert messages[0]["role"] == "system"
        assert "helpful assistant" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert pipeline_context.idea in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_execute_uses_default_model_from_config(self, mock_llm, pipeline_context):
        """When no model provided in config, falls back to 'claude-opus-4-6'."""
        agent = ConcreteAgent(llm=mock_llm)
        await agent.execute(pipeline_context)

        call_args = mock_llm.complete.call_args
        model = call_args[1].get("model") or call_args[0][1]
        assert model == "claude-opus-4-6"

    @pytest.mark.asyncio
    async def test_execute_uses_model_from_config(self, mock_llm, pipeline_context):
        agent = ConcreteAgent(llm=mock_llm, config={"model": "gpt-4o-mini"})
        await agent.execute(pipeline_context)

        call_args = mock_llm.complete.call_args
        model = call_args[1].get("model") or call_args[0][1]
        assert model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_raw_content_is_llm_response(self, mock_llm, pipeline_context):
        mock_llm.complete = AsyncMock(return_value="Specific LLM output")
        agent = ConcreteAgent(llm=mock_llm)
        artifact = await agent.execute(pipeline_context)
        assert artifact.raw_content == "Specific LLM output"


# ---------------------------------------------------------------------------
# Tests: _structured_output
# ---------------------------------------------------------------------------

class TestStructuredOutput:
    @pytest.mark.asyncio
    async def test_structured_output_returns_schema_instance(self, mock_llm, pipeline_context):
        agent = ConcreteAgentWithStructured(llm=mock_llm)
        artifact = await agent.execute(pipeline_context)
        assert isinstance(artifact, PRDArtifact)

    @pytest.mark.asyncio
    async def test_structured_output_calls_llm_structured_output(self, mock_llm, pipeline_context):
        agent = ConcreteAgentWithStructured(llm=mock_llm)
        await agent.execute(pipeline_context)
        mock_llm.structured_output.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_structured_output_passes_schema(self, mock_llm, pipeline_context):
        agent = ConcreteAgentWithStructured(llm=mock_llm)
        await agent.execute(pipeline_context)

        call_kwargs = mock_llm.structured_output.call_args[1]
        assert call_kwargs["schema"] is PRDArtifact

    @pytest.mark.asyncio
    async def test_structured_output_passes_messages(self, mock_llm, pipeline_context):
        agent = ConcreteAgentWithStructured(llm=mock_llm)
        await agent.execute(pipeline_context)

        call_args = mock_llm.structured_output.call_args
        messages = call_args[0][0]
        assert any(m["role"] == "system" for m in messages)
        assert any(m["role"] == "user" for m in messages)


# ---------------------------------------------------------------------------
# Tests: ClassVar attributes
# ---------------------------------------------------------------------------

class TestClassVarAttributes:
    def test_agent_name_is_class_var(self, mock_llm):
        agent = ConcreteAgent(llm=mock_llm)
        assert ConcreteAgent.agent_name == "concrete-agent"
        assert agent.agent_name == "concrete-agent"

    def test_output_artifact_class_is_class_var(self, mock_llm):
        agent = ConcreteAgent(llm=mock_llm)
        assert ConcreteAgent.output_artifact_class is PRDArtifact
        assert agent.output_artifact_class is PRDArtifact
