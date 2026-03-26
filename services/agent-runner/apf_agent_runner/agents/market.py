"""Market Agent — conducts market research and competitive analysis."""

from __future__ import annotations

from typing import ClassVar

from apf_agent_core import BaseAgent, MarketArtifact, PipelineContext
from apf_agent_core.artifacts import ArtifactStatus

from ._base import extract_json, render_prompt


class MarketAgent(BaseAgent):
    """Produces a MarketArtifact from the PRD and product idea."""

    agent_name: ClassVar[str] = "market"
    output_artifact_class: ClassVar[type] = MarketArtifact

    async def execute(self, ctx: PipelineContext) -> MarketArtifact:
        system, user = render_prompt("market.j2", ctx)
        raw = await self._call_llm(system=system, user=user)

        data = extract_json(raw)

        artifact = MarketArtifact(
            raw_content=raw,
            status=ArtifactStatus.COMPLETE,
            market_size=data.get("market_size", ""),
            competitors=data.get("competitors", []),
            differentiators=data.get("differentiators", []),
            recommended_features=data.get("recommended_features", []),
        )
        return artifact
