"""
Shared pytest fixtures for apf_agent_core tests.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from apf_agent_core.context import PipelineContext, PipelineConfig, CredentialStore
from apf_agent_core.artifacts import PRDArtifact, ArtifactStatus
from apf_agent_core.llm.provider import LLMProvider


# ---------------------------------------------------------------------------
# mock_llm
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm() -> MagicMock:
    """
    A MagicMock that satisfies the LLMProvider Protocol.

    - complete()          → returns "Mock LLM response"
    - stream()            → async generator yielding ["chunk1", " chunk2"]
    - structured_output() → returns a PRDArtifact with test data
    """
    llm = MagicMock(spec=LLMProvider)

    # complete is an async method
    llm.complete = AsyncMock(return_value="Mock LLM response")

    # structured_output is an async method returning a PRDArtifact by default
    llm.structured_output = AsyncMock(
        return_value=PRDArtifact(
            executive_summary="Test summary",
            target_users=["developers"],
            core_features=["feature A", "feature B"],
            success_metrics=["metric 1"],
            out_of_scope=["feature X"],
        )
    )

    # stream is an async generator
    async def _stream_gen(*args, **kwargs):
        for chunk in ["chunk1", " chunk2"]:
            yield chunk

    llm.stream = _stream_gen

    return llm


# ---------------------------------------------------------------------------
# pipeline_context
# ---------------------------------------------------------------------------

@pytest.fixture
def pipeline_context() -> PipelineContext:
    """A PipelineContext with deterministic test data."""
    return PipelineContext(
        run_id="test-run-001",
        idea="An AI-powered autonomous software factory that builds products end-to-end.",
        config=PipelineConfig(
            llm_provider="anthropic",
            llm_model="claude-opus-4-6",
            max_tokens=4096,
            temperature=0.2,
        ),
        credentials=CredentialStore(
            anthropic_api_key="sk-test-key",
        ),
    )


# ---------------------------------------------------------------------------
# sample_prd_artifact
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_prd_artifact() -> PRDArtifact:
    """A PRDArtifact populated with realistic test data."""
    return PRDArtifact(
        agent_name="prd-agent",
        status=ArtifactStatus.COMPLETE,
        raw_content="# PRD\n\nThis is the raw markdown output.",
        executive_summary=(
            "Build an Autonomous Product Factory (APF) that accepts a one-line product idea "
            "and autonomously produces a production-ready codebase, tests, and deployment."
        ),
        target_users=[
            "Indie hackers who want to ship MVPs quickly",
            "Enterprise teams automating internal tooling",
            "Startup CTOs prototyping new ideas",
        ],
        core_features=[
            "Multi-agent pipeline (PRD → Architecture → Code → QA → Deploy)",
            "Human-in-the-loop approval gates",
            "GitHub integration for PR creation",
            "Artifact store with versioning",
        ],
        success_metrics=[
            "End-to-end pipeline completes in < 30 minutes",
            "Generated code passes 80%+ test coverage",
            "Zero critical bugs in QA report",
        ],
        out_of_scope=[
            "Mobile app generation",
            "Hardware integrations",
        ],
        metadata={"model_used": "claude-opus-4-6", "tokens_used": 4200},
    )
