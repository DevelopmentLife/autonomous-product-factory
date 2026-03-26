"""Pydantic v2 event schemas for all APF event types."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .streams import Streams


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    stream: str

    model_config = {"arbitrary_types_allowed": True}


class StageDispatchEvent(BaseEvent):
    """Published by orchestrator when dispatching a stage to agent-runner."""

    stream: str = Streams.STAGE_DISPATCH
    pipeline_id: str
    run_id: str
    stage_name: str  # prd|architect|market|ux|engineering|developer|qa|regression|review|devops|readme
    stage_id: str
    idea: str
    config: dict
    prior_artifacts: dict  # keyed by agent_name


class StageStartedEvent(BaseEvent):
    """Published by agent-runner when a stage begins execution."""

    stream: str = Streams.STAGE_STARTED
    pipeline_id: str
    stage_id: str
    stage_name: str
    worker_id: str


class StageCompleteEvent(BaseEvent):
    """Published by agent-runner when a stage finishes successfully."""

    stream: str = Streams.STAGE_COMPLETE
    pipeline_id: str
    stage_id: str
    stage_name: str
    artifact_url: str
    artifact_hash: str
    duration_ms: int
    llm_tokens_used: int
    llm_cost_usd: float


class StageFailedEvent(BaseEvent):
    """Published by agent-runner when a stage fails."""

    stream: str = Streams.STAGE_FAILED
    pipeline_id: str
    stage_id: str
    stage_name: str
    error_type: str
    error_message: str
    retry_count: int


class ApprovalRequiredEvent(BaseEvent):
    """Published by orchestrator to request human approval."""

    stream: str = Streams.APPROVAL_REQUIRED
    pipeline_id: str
    stage_id: str
    stage_name: str
    artifact_url: str
    approval_timeout_seconds: int = 3600


class ApprovalGrantedEvent(BaseEvent):
    """Published by slack/dashboard when approval decision is made."""

    stream: str = Streams.APPROVAL_GRANTED
    pipeline_id: str
    stage_id: str
    approved: bool
    approved_by: str
    comment: str = ""


class PipelineCompleteEvent(BaseEvent):
    """Published by orchestrator when a full pipeline finishes successfully."""

    stream: str = Streams.PIPELINE_COMPLETE
    pipeline_id: str
    idea: str
    github_pr_url: str
    duration_seconds: float
    total_cost_usd: float


class PipelineFailedEvent(BaseEvent):
    """Published by orchestrator when a pipeline fails unrecoverably."""

    stream: str = Streams.PIPELINE_FAILED
    pipeline_id: str
    idea: str
    failed_stage: str
    error_message: str


class ConnectorEvent(BaseEvent):
    """Published by external connectors (slack, jira, confluence, aws) to orchestrator."""

    stream: str = Streams.CONNECTOR_EVENT
    connector_type: str   # slack|jira|confluence|aws
    event_type: str       # command.received|approval.submitted|deployment.triggered
    payload: dict


# Mapping of stream name -> event class for deserialization
EVENT_TYPE_MAP: dict[str, type[BaseEvent]] = {
    Streams.STAGE_DISPATCH: StageDispatchEvent,
    Streams.STAGE_STARTED: StageStartedEvent,
    Streams.STAGE_COMPLETE: StageCompleteEvent,
    Streams.STAGE_FAILED: StageFailedEvent,
    Streams.APPROVAL_REQUIRED: ApprovalRequiredEvent,
    Streams.APPROVAL_GRANTED: ApprovalGrantedEvent,
    Streams.PIPELINE_COMPLETE: PipelineCompleteEvent,
    Streams.PIPELINE_FAILED: PipelineFailedEvent,
    Streams.CONNECTOR_EVENT: ConnectorEvent,
}
