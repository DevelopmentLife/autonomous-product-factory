"""Tests for the APF event bus using InMemoryEventBus (no Redis required)."""

import asyncio

import pytest
import pytest_asyncio

from apf_event_bus import (
    ApprovalGrantedEvent,
    ApprovalRequiredEvent,
    ConnectorEvent,
    InMemoryEventBus,
    PipelineCompleteEvent,
    PipelineFailedEvent,
    StageCompleteEvent,
    StageDispatchEvent,
    StageFailedEvent,
    StageStartedEvent,
    Streams,
)


# ---------------------------------------------------------------------------
# publish / consume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_and_consume(
    in_memory_bus: InMemoryEventBus,
    sample_dispatch_event: StageDispatchEvent,
) -> None:
    """Publishing an event and consuming it should return the same data."""
    msg_id = await in_memory_bus.publish(sample_dispatch_event)
    assert isinstance(msg_id, str)
    assert len(msg_id) > 0

    messages = await in_memory_bus.consume(Streams.STAGE_DISPATCH)
    assert len(messages) == 1

    returned_id, returned_event = messages[0]
    assert returned_id == msg_id
    assert isinstance(returned_event, StageDispatchEvent)
    assert returned_event.pipeline_id == sample_dispatch_event.pipeline_id
    assert returned_event.run_id == sample_dispatch_event.run_id
    assert returned_event.stage_name == sample_dispatch_event.stage_name
    assert returned_event.stage_id == sample_dispatch_event.stage_id
    assert returned_event.idea == sample_dispatch_event.idea
    assert returned_event.config == sample_dispatch_event.config
    assert returned_event.prior_artifacts == sample_dispatch_event.prior_artifacts
    assert returned_event.event_id == sample_dispatch_event.event_id


# ---------------------------------------------------------------------------
# acknowledge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge(
    in_memory_bus: InMemoryEventBus,
    sample_dispatch_event: StageDispatchEvent,
) -> None:
    """Acknowledging a message should remove it from pending."""
    msg_id = await in_memory_bus.publish(sample_dispatch_event)

    messages = await in_memory_bus.consume(Streams.STAGE_DISPATCH)
    assert len(messages) == 1

    # Before ack: message is still pending
    assert in_memory_bus.pending_count(Streams.STAGE_DISPATCH) == 1

    returned_id, _ = messages[0]
    await in_memory_bus.acknowledge(Streams.STAGE_DISPATCH, returned_id)

    # After ack: message is no longer pending
    assert in_memory_bus.pending_count(Streams.STAGE_DISPATCH) == 0
    assert msg_id in in_memory_bus.acknowledged_ids(Streams.STAGE_DISPATCH)


# ---------------------------------------------------------------------------
# subscribe — handler called
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribe_calls_handler(
    in_memory_bus: InMemoryEventBus,
    sample_dispatch_event: StageDispatchEvent,
) -> None:
    """subscribe() should call the handler with the published event."""
    received: list[StageDispatchEvent] = []
    stop = asyncio.Event()

    async def handler(event: StageDispatchEvent) -> None:
        received.append(event)
        stop.set()  # stop after first message

    await in_memory_bus.publish(sample_dispatch_event)

    await asyncio.wait_for(
        in_memory_bus.subscribe(Streams.STAGE_DISPATCH, handler, stop_event=stop),
        timeout=3.0,
    )

    assert len(received) == 1
    assert received[0].pipeline_id == sample_dispatch_event.pipeline_id
    assert received[0].event_id == sample_dispatch_event.event_id


# ---------------------------------------------------------------------------
# subscribe — stop_event triggers clean shutdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribe_stops_on_event(in_memory_bus: InMemoryEventBus) -> None:
    """Setting stop_event should cause subscribe() to exit cleanly."""
    stop = asyncio.Event()
    call_count = 0

    async def handler(event: StageDispatchEvent) -> None:
        nonlocal call_count
        call_count += 1

    # Signal stop before any messages arrive
    stop.set()

    # Should return promptly without blocking
    await asyncio.wait_for(
        in_memory_bus.subscribe(Streams.STAGE_DISPATCH, handler, stop_event=stop),
        timeout=2.0,
    )
    assert call_count == 0


# ---------------------------------------------------------------------------
# serialization round-trips
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_serialization() -> None:
    """All event types should serialise and deserialise without data loss."""
    events = [
        StageDispatchEvent(
            pipeline_id="p1",
            run_id="r1",
            stage_name="prd",
            stage_id="s1",
            idea="idea",
            config={},
            prior_artifacts={},
        ),
        StageStartedEvent(pipeline_id="p1", stage_id="s1", stage_name="prd", worker_id="w1"),
        StageCompleteEvent(
            pipeline_id="p1",
            stage_id="s1",
            stage_name="prd",
            artifact_url="s3://bucket/key",
            artifact_hash="sha256:abc",
            duration_ms=1000,
            llm_tokens_used=500,
            llm_cost_usd=0.01,
        ),
        StageFailedEvent(
            pipeline_id="p1",
            stage_id="s1",
            stage_name="prd",
            error_type="TimeoutError",
            error_message="LLM timed out",
            retry_count=2,
        ),
        ApprovalRequiredEvent(
            pipeline_id="p1",
            stage_id="s1",
            stage_name="review",
            artifact_url="s3://bucket/key",
        ),
        ApprovalGrantedEvent(
            pipeline_id="p1",
            stage_id="s1",
            approved=True,
            approved_by="alice",
            comment="LGTM",
        ),
        PipelineCompleteEvent(
            pipeline_id="p1",
            idea="idea",
            github_pr_url="https://github.com/org/repo/pull/1",
            duration_seconds=120.5,
            total_cost_usd=1.23,
        ),
        PipelineFailedEvent(
            pipeline_id="p1",
            idea="idea",
            failed_stage="developer",
            error_message="OOM",
        ),
        ConnectorEvent(
            connector_type="slack",
            event_type="command.received",
            payload={"text": "/build something cool"},
        ),
    ]

    for event in events:
        json_str = event.model_dump_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Re-hydrate using the same class
        restored = type(event).model_validate_json(json_str)
        assert restored.event_id == event.event_id
        assert restored.stream == event.stream
        assert type(restored) is type(event)


# ---------------------------------------------------------------------------
# field-level tests
# ---------------------------------------------------------------------------


def test_stage_dispatch_event_fields(sample_dispatch_event: StageDispatchEvent) -> None:
    """StageDispatchEvent should carry all required fields with correct types."""
    evt = sample_dispatch_event
    assert isinstance(evt.event_id, str) and len(evt.event_id) > 0
    assert evt.stream == Streams.STAGE_DISPATCH
    assert isinstance(evt.pipeline_id, str)
    assert isinstance(evt.run_id, str)
    assert isinstance(evt.stage_name, str)
    assert isinstance(evt.stage_id, str)
    assert isinstance(evt.idea, str)
    assert isinstance(evt.config, dict)
    assert isinstance(evt.prior_artifacts, dict)


def test_pipeline_complete_event_fields() -> None:
    """PipelineCompleteEvent should carry all required fields with correct types."""
    evt = PipelineCompleteEvent(
        pipeline_id="pipe-999",
        idea="Build a rocket",
        github_pr_url="https://github.com/org/rocket/pull/42",
        duration_seconds=300.0,
        total_cost_usd=5.67,
    )
    assert evt.stream == Streams.PIPELINE_COMPLETE
    assert isinstance(evt.pipeline_id, str)
    assert isinstance(evt.idea, str)
    assert isinstance(evt.github_pr_url, str)
    assert isinstance(evt.duration_seconds, float)
    assert isinstance(evt.total_cost_usd, float)
    assert evt.duration_seconds == 300.0
    assert evt.total_cost_usd == 5.67


# ---------------------------------------------------------------------------
# multiple streams isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_streams(in_memory_bus: InMemoryEventBus) -> None:
    """Events published on different streams must not cross-contaminate."""
    dispatch_evt = StageDispatchEvent(
        pipeline_id="p1",
        run_id="r1",
        stage_name="developer",
        stage_id="s1",
        idea="idea",
        config={},
        prior_artifacts={},
    )
    complete_evt = StageCompleteEvent(
        pipeline_id="p1",
        stage_id="s1",
        stage_name="developer",
        artifact_url="s3://bucket/key",
        artifact_hash="sha256:abc",
        duration_ms=1000,
        llm_tokens_used=500,
        llm_cost_usd=0.01,
    )

    await in_memory_bus.publish(dispatch_evt)
    await in_memory_bus.publish(complete_evt)

    dispatch_messages = await in_memory_bus.consume(Streams.STAGE_DISPATCH)
    complete_messages = await in_memory_bus.consume(Streams.STAGE_COMPLETE)

    assert len(dispatch_messages) == 1
    assert len(complete_messages) == 1

    _, d_evt = dispatch_messages[0]
    _, c_evt = complete_messages[0]

    assert isinstance(d_evt, StageDispatchEvent)
    assert isinstance(c_evt, StageCompleteEvent)

    # No leakage: dispatch stream has only dispatch events
    assert d_evt.stream == Streams.STAGE_DISPATCH
    assert c_evt.stream == Streams.STAGE_COMPLETE

    # Second consume on each stream returns nothing
    assert await in_memory_bus.consume(Streams.STAGE_DISPATCH, block_ms=100) == []
    assert await in_memory_bus.consume(Streams.STAGE_COMPLETE, block_ms=100) == []
