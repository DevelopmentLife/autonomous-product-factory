"""Regression Agent — fixes bugs found by QA and verifies resolution."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import BaseAgent, PipelineContext, RegressionArtifact
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class RegressionAgent(BaseAgent):
    """Produces a RegressionArtifact describing which bugs were fixed."""

    agent_name: ClassVar[str] = "regression"
    output_artifact_class: ClassVar[type] = RegressionArtifact

    async def execute(self, ctx: PipelineContext) -> RegressionArtifact:
        system, user = render_prompt("regression.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        artifact = RegressionArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            bugs_fixed=data.get("bugs_fixed", []),
            files_modified=data.get("files_modified", []),
        )
        return artifact
