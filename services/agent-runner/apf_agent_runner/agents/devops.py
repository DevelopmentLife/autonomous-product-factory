"""DevOps Agent — sets up deployment pipelines and infrastructure."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import BaseAgent, DevOpsArtifact, PipelineContext
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class DevOpsAgent(BaseAgent):
    """Produces a DevOpsArtifact with deployment and pipeline URLs."""

    agent_name: ClassVar[str] = "devops"
    output_artifact_class: ClassVar[type] = DevOpsArtifact

    async def execute(self, ctx: PipelineContext) -> DevOpsArtifact:
        system, user = render_prompt("devops.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        artifact = DevOpsArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            deployment_url=data.get("deployment_url", ""),
            pipeline_url=data.get("pipeline_url", ""),
            environment=data.get("environment", ""),
        )
        return artifact
