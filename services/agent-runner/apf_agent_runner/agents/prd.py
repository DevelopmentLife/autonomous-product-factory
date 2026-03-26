"""PRD Agent — generates a Product Requirements Document."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import BaseAgent, PipelineContext, PRDArtifact
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class PRDAgent(BaseAgent):
    """Produces a PRDArtifact from a raw product idea."""

    agent_name: ClassVar[str] = "prd"
    output_artifact_class: ClassVar[type] = PRDArtifact

    async def execute(self, ctx: PipelineContext) -> PRDArtifact:
        """Call the LLM with the PRD prompt and parse the JSON response."""
        system, user = render_prompt("prd.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        artifact = PRDArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            executive_summary=data.get("executive_summary", ""),
            target_users=data.get("target_users", []),
            core_features=data.get("core_features", []),
            success_metrics=data.get("success_metrics", []),
            out_of_scope=data.get("out_of_scope", []),
        )
        return artifact
