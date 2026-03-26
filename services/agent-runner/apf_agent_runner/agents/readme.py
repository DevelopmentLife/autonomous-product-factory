"""Readme Agent — generates the project README.md."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import BaseAgent, PipelineContext, ReadmeArtifact
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class ReadmeAgent(BaseAgent):
    """Produces a ReadmeArtifact with the full README.md content."""

    agent_name: ClassVar[str] = "readme"
    output_artifact_class: ClassVar[type] = ReadmeArtifact

    async def execute(self, ctx: PipelineContext) -> ReadmeArtifact:
        system, user = render_prompt("readme.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        artifact = ReadmeArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            content=data.get("content", raw),
        )
        return artifact
