"""Architect Agent — designs the system architecture."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import ArchitectureArtifact, BaseAgent, PipelineContext
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class ArchitectAgent(BaseAgent):
    """Produces an ArchitectureArtifact from the PRD."""

    agent_name: ClassVar[str] = "architect"
    output_artifact_class: ClassVar[type] = ArchitectureArtifact

    async def execute(self, ctx: PipelineContext) -> ArchitectureArtifact:
        system, user = render_prompt("architect.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        artifact = ArchitectureArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            services=data.get("services", []),
            tech_stack=data.get("tech_stack", {}),
            architecture_diagram=data.get("architecture_diagram", ""),
        )
        return artifact
