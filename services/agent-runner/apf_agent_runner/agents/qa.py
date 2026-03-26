"""QA Agent — performs quality assurance and generates a bug report."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import BaseAgent, PipelineContext, QAArtifact
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class QAAgent(BaseAgent):
    """Produces a QAArtifact with bugs, test results, and a pass/fail verdict."""

    agent_name: ClassVar[str] = "qa"
    output_artifact_class: ClassVar[type] = QAArtifact

    async def execute(self, ctx: PipelineContext) -> QAArtifact:
        system, user = render_prompt("qa.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        bugs: list[dict] = data.get("bugs", [])
        critical_count = sum(1 for b in bugs if b.get("severity") == "critical")
        high_count = sum(1 for b in bugs if b.get("severity") == "high")

        # Override passed based on bug counts even if LLM says otherwise
        passed_from_llm: bool = bool(data.get("passed", False))
        passed = passed_from_llm and critical_count == 0

        artifact = QAArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            bugs=bugs,
            test_results=data.get("test_results", {}),
            coverage_pct=float(data.get("coverage_pct", 0.0)),
            critical_bug_count=critical_count,
            high_bug_count=high_count,
            passed=passed,
        )
        return artifact
