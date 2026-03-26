"""Review Agent — performs code review for correctness, security, and maintainability."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import BaseAgent, PipelineContext, ReviewArtifact
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class ReviewAgent(BaseAgent):
    """Produces a ReviewArtifact with approval decision, comments, and security issues."""

    agent_name: ClassVar[str] = "review"
    output_artifact_class: ClassVar[type] = ReviewArtifact

    async def execute(self, ctx: PipelineContext) -> ReviewArtifact:
        system, user = render_prompt("review.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        # Force rejection if security issues are present and LLM approved anyway.
        security_issues: list[str] = data.get("security_issues", [])
        approved_from_llm: bool = bool(data.get("approved", False))
        approved = approved_from_llm and len(security_issues) == 0

        artifact = ReviewArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            approved=approved,
            comments=data.get("comments", []),
            security_issues=security_issues,
            coverage_pct=float(data.get("coverage_pct", 0.0)),
        )
        return artifact
