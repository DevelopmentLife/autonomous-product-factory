"""Shared pytest fixtures for the event-bus test suite."""

import pytest
import pytest_asyncio

from apf_event_bus import InMemoryEventBus, StageCompleteEvent, StageDispatchEvent


@pytest_asyncio.fixture
async def in_memory_bus() -> InMemoryEventBus:
    """Fresh InMemoryEventBus instance for each test."""
    return InMemoryEventBus()


@pytest.fixture
def sample_dispatch_event() -> StageDispatchEvent:
    """A fully-populated StageDispatchEvent for use in tests."""
    return StageDispatchEvent(
        pipeline_id="pipe-001",
        run_id="run-abc",
        stage_name="developer",
        stage_id="stage-dev-001",
        idea="An AI-powered code review tool",
        config={"model": "claude-sonnet-4-6", "max_tokens": 8192},
        prior_artifacts={
            "prd": "s3://apf-artifacts/pipe-001/prd.md",
            "architect": "s3://apf-artifacts/pipe-001/architecture.md",
        },
    )


@pytest.fixture
def sample_complete_event() -> StageCompleteEvent:
    """A fully-populated StageCompleteEvent for use in tests."""
    return StageCompleteEvent(
        pipeline_id="pipe-001",
        stage_id="stage-dev-001",
        stage_name="developer",
        artifact_url="s3://apf-artifacts/pipe-001/code.zip",
        artifact_hash="sha256:abc123def456",
        duration_ms=42_000,
        llm_tokens_used=15_000,
        llm_cost_usd=0.045,
    )
