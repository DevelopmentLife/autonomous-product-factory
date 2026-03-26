from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from .context import PipelineContext
from .artifacts import BaseArtifact
from .llm.provider import LLMProvider, LLMMessage


class BaseAgent(ABC):
    """Abstract base for all APF pipeline agents."""

    agent_name: ClassVar[str]
    output_artifact_class: ClassVar[type[BaseArtifact]]

    def __init__(self, llm: LLMProvider, config: dict[str, Any] | None = None) -> None:
        self.llm = llm
        self.config: dict[str, Any] = config or {}

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> BaseArtifact:
        """Run the agent and return a populated artifact."""
        ...

    async def _call_llm(
        self,
        system: str,
        user: str,
        model: str | None = None,
    ) -> str:
        """
        Convenience wrapper: build system+user messages and call
        ``self.llm.complete``, returning the string response.
        """
        messages: list[LLMMessage] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        resolved_model = model or self.config.get("model", "claude-opus-4-6")
        return await self.llm.complete(messages, model=resolved_model)

    async def _structured_output(
        self,
        system: str,
        user: str,
        schema: type,
        model: str | None = None,
    ) -> Any:
        """
        Convenience wrapper: build system+user messages and call
        ``self.llm.structured_output``, returning a validated schema instance.
        """
        messages: list[LLMMessage] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        resolved_model = model or self.config.get("model", "claude-opus-4-6")
        return await self.llm.structured_output(messages, schema=schema, model=resolved_model)
