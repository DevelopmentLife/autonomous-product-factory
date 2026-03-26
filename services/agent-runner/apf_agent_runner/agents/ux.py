"""UX Agent — designs the user experience."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import BaseAgent, PipelineContext, UXArtifact
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class UXAgent(BaseAgent):
    """Produces a UXArtifact from the PRD and market research."""

    agent_name: ClassVar[str] = "ux"
    output_artifact_class: ClassVar[type] = UXArtifact

    async def execute(self, ctx: PipelineContext) -> UXArtifact:
        system, user = render_prompt("ux.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        artifact = UXArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            cli_commands=data.get("cli_commands", []),
            dashboard_screens=data.get("dashboard_screens", []),
            user_flows=data.get("user_flows", []),
        )
        return artifact
