"""Engineering Agent — creates the detailed engineering plan."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import BaseAgent, EngineeringArtifact, PipelineContext
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class EngineeringAgent(BaseAgent):
    """Produces an EngineeringArtifact from PRD, architecture, market and UX artifacts."""

    agent_name: ClassVar[str] = "engineering"
    output_artifact_class: ClassVar[type] = EngineeringArtifact

    async def execute(self, ctx: PipelineContext) -> EngineeringArtifact:
        system, user = render_prompt("engineering.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        artifact = EngineeringArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            tech_stack=data.get("tech_stack", {}),
            phases=data.get("phases", []),
            milestones=data.get("milestones", []),
        )
        return artifact
