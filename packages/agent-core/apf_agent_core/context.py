from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineConfig:
    llm_provider: str = "anthropic"
    llm_model: str = "claude-opus-4-6"
    max_tokens: int = 8192
    temperature: float = 0.3
    artifact_store_url: str = "http://artifact-store:8001"
    github_integration_url: str = "http://github-integration:8002"
    enable_hitl: bool = False
    hitl_timeout_seconds: int = 3600


@dataclass
class CredentialStore:
    """Never serialised to disk or logs"""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    github_token: str = ""
    slack_bot_token: str = ""
    jira_api_token: str = ""
    confluence_api_token: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""


@dataclass
class PipelineContext:
    run_id: str
    idea: str
    config: PipelineConfig = field(default_factory=PipelineConfig)
    credentials: CredentialStore = field(default_factory=CredentialStore)
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
