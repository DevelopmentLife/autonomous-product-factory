"""
apf_agent_core — Core agent abstractions, LLM providers, and artifact schemas
for the Autonomous Product Factory (APF).
"""

from .agent import BaseAgent
from .context import PipelineContext, PipelineConfig, CredentialStore
from .artifacts import (
    ArtifactStatus,
    BaseArtifact,
    PRDArtifact,
    ArchitectureArtifact,
    MarketArtifact,
    UXArtifact,
    EngineeringArtifact,
    DeveloperArtifact,
    QAArtifact,
    RegressionArtifact,
    ReviewArtifact,
    DevOpsArtifact,
    ReadmeArtifact,
)
from .llm import (
    LLMProvider,
    LLMMessage,
    AnthropicProvider,
    OpenAIProvider,
    LiteLLMProvider,
)
from .validators import ArtifactValidationError, validate_artifact

__all__ = [
    # Agent base
    "BaseAgent",
    # Context
    "PipelineContext",
    "PipelineConfig",
    "CredentialStore",
    # Artifact types
    "ArtifactStatus",
    "BaseArtifact",
    "PRDArtifact",
    "ArchitectureArtifact",
    "MarketArtifact",
    "UXArtifact",
    "EngineeringArtifact",
    "DeveloperArtifact",
    "QAArtifact",
    "RegressionArtifact",
    "ReviewArtifact",
    "DevOpsArtifact",
    "ReadmeArtifact",
    # LLM
    "LLMProvider",
    "LLMMessage",
    "AnthropicProvider",
    "OpenAIProvider",
    "LiteLLMProvider",
    # Validators
    "ArtifactValidationError",
    "validate_artifact",
]
