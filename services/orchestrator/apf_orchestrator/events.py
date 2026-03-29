"""Inline event schemas for orchestrator — no external apf_event_bus dependency."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class Streams:
    STAGE_DISPATCH = "apf:stage:dispatch"
    STAGE_STARTED = "apf:stage:started"
    STAGE_COMPLETE = "apf:stage:complete"
    STAGE_FAILED = "apf:stage:failed"
    APPROVAL_REQUIRED = "apf:approval:required"
    APPROVAL_GRANTED = "apf:approval:granted"
    PIPELINE_COMPLETE = "apf:pipeline:complete"
    PIPELINE_FAILED = "apf:pipeline:failed"


class StageDispatchEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_id: str
    run_id: str = ""
    stage_id: str
    stage_name: str
    idea: str
    config: dict = {}
    prior_artifacts: dict = {}


class StageCompleteEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_id: str
    stage_id: str
    stage_name: str
    artifact_url: str = ""
    artifact_hash: str = ""
    duration_ms: int = 0
    llm_tokens_used: int = 0
    llm_cost_usd: float = 0.0


class StageFailedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_id: str
    stage_id: str
    stage_name: str
    error_type: str = "unknown"
    error_message: str
    retry_count: int = 0


class PipelineCompleteEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_id: str
    idea: str
    github_pr_url: str = ""
    duration_seconds: float = 0.0
    total_cost_usd: float = 0.0


class PipelineFailedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_id: str
    idea: str
    failed_stage: str = ""
    error_message: str = ""
