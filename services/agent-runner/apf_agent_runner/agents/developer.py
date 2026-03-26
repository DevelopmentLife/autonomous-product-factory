"""Developer Agent — generates the code structure description."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import BaseAgent, DeveloperArtifact, PipelineContext
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class DeveloperAgent(BaseAgent):
    """Produces a DeveloperArtifact describing the implementation.

    In the real system this would generate actual code.  For now it generates
    a realistic code-structure description so the rest of the pipeline can
    proceed without requiring a code-execution sandbox.
    """

    agent_name: ClassVar[str] = "developer"
    output_artifact_class: ClassVar[type] = DeveloperArtifact

    async def execute(self, ctx: PipelineContext) -> DeveloperArtifact:
        system, user = render_prompt("developer.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        artifact = DeveloperArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            files_created=data.get("files_created", []),
            files_modified=data.get("files_modified", []),
            tests_written=data.get("tests_written", []),
            coverage_pct=float(data.get("coverage_pct", 0.0)),
            github_branch=data.get("github_branch", ""),
            github_pr_url=data.get("github_pr_url", ""),
        )
        return artifact
