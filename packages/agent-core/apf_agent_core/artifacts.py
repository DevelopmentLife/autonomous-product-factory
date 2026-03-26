from uuid import uuid4
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime
from enum import Enum


class ArtifactStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class BaseArtifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str
    status: ArtifactStatus = ArtifactStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    raw_content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PRDArtifact(BaseArtifact):
    agent_name: str = "prd-agent"
    executive_summary: str = ""
    target_users: list[str] = Field(default_factory=list)
    core_features: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)


class ArchitectureArtifact(BaseArtifact):
    agent_name: str = "architect-agent"
    services: list[str] = Field(default_factory=list)
    tech_stack: dict[str, str] = Field(default_factory=dict)
    architecture_diagram: str = ""


class MarketArtifact(BaseArtifact):
    agent_name: str = "market-agent"
    market_size: str = ""
    competitors: list[dict[str, Any]] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)
    recommended_features: list[str] = Field(default_factory=list)


class UXArtifact(BaseArtifact):
    agent_name: str = "ux-agent"
    cli_commands: list[str] = Field(default_factory=list)
    dashboard_screens: list[str] = Field(default_factory=list)
    user_flows: list[str] = Field(default_factory=list)


class EngineeringArtifact(BaseArtifact):
    agent_name: str = "engineering-agent"
    tech_stack: dict[str, str] = Field(default_factory=dict)
    phases: list[dict[str, Any]] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)


class DeveloperArtifact(BaseArtifact):
    agent_name: str = "developer-agent"
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    tests_written: list[str] = Field(default_factory=list)
    coverage_pct: float = 0.0
    github_branch: str = ""
    github_pr_url: str = ""


class QAArtifact(BaseArtifact):
    agent_name: str = "qa-agent"
    bugs: list[dict[str, Any]] = Field(default_factory=list)
    test_results: dict[str, Any] = Field(default_factory=dict)
    coverage_pct: float = 0.0
    critical_bug_count: int = 0
    high_bug_count: int = 0
    passed: bool = False


class RegressionArtifact(BaseArtifact):
    agent_name: str = "regression-agent"
    bugs_fixed: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)


class ReviewArtifact(BaseArtifact):
    agent_name: str = "review-agent"
    approved: bool = False
    comments: list[dict[str, Any]] = Field(default_factory=list)
    security_issues: list[str] = Field(default_factory=list)
    coverage_pct: float = 0.0


class DevOpsArtifact(BaseArtifact):
    agent_name: str = "devops-agent"
    deployment_url: str = ""
    pipeline_url: str = ""
    environment: str = ""


class ReadmeArtifact(BaseArtifact):
    agent_name: str = "readme-agent"
    content: str = ""
