from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class BaseArtifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str = ''
    status: str = 'pending'
    raw_content: str = ''
    metadata: dict = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PRDArtifact(BaseArtifact):
    agent_name: str = 'prd-agent'

class ArchitectureArtifact(BaseArtifact):
    agent_name: str = 'architect-agent'

class MarketArtifact(BaseArtifact):
    agent_name: str = 'market-agent'

class UXArtifact(BaseArtifact):
    agent_name: str = 'ux-agent'

class EngineeringArtifact(BaseArtifact):
    agent_name: str = 'engineering-agent'

class DeveloperArtifact(BaseArtifact):
    agent_name: str = 'developer-agent'
    files_created: list = []
    coverage_pct: float = 0.0

class QAArtifact(BaseArtifact):
    agent_name: str = 'qa-agent'
    bugs: list = []
    critical_bug_count: int = 0
    high_bug_count: int = 0
    passed: bool = True

class RegressionArtifact(BaseArtifact):
    agent_name: str = 'regression-agent'
    bugs_fixed: list = []

class ReviewArtifact(BaseArtifact):
    agent_name: str = 'review-agent'
    approved: bool = False
    comments: list = []
    security_issues: list = []

class DevOpsArtifact(BaseArtifact):
    agent_name: str = 'devops-agent'
    deployment_url: str = ''

class ReadmeArtifact(BaseArtifact):
    agent_name: str = 'readme-agent'
    content: str = ''


@dataclass
class PipelineContext:
    run_id: str
    idea: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    config: dict = field(default_factory=dict)


class BaseAgent:
    agent_name: str = ''
    output_artifact_class = BaseArtifact

    def __init__(self, llm, model: str = 'claude-opus-4-6'):
        self.llm = llm
        self.model = model

    async def execute(self, ctx: PipelineContext) -> BaseArtifact:
        raise NotImplementedError

    def _get_prior(self, ctx: PipelineContext, stage: str, default: str = '') -> str:
        art = ctx.artifacts.get(stage, {})
        if hasattr(art, 'raw_content'):
            return art.raw_content
        if isinstance(art, dict):
            return art.get('raw_content', default)
        return default
