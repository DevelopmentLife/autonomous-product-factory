"""AgentRunner — dispatches StageDispatchEvent to the right agent."""

from __future__ import annotations

import hashlib
import time
import logging
from typing import Any

import httpx
import structlog

from apf_agent_core import (
    LLMProvider,
    PipelineConfig,
    PipelineContext,
)
from apf_event_bus import (
    InMemoryEventBus,
    StageCompleteEvent,
    StageDispatchEvent,
    StageFailedEvent,
    StageStartedEvent,
)
from apf_event_bus.client import EventBusClient

from .agents import (
    ArchitectAgent,
    DeveloperAgent,
    DevOpsAgent,
    EngineeringAgent,
    MarketAgent,
    PRDAgent,
    QAAgent,
    ReadmeAgent,
    RegressionAgent,
    ReviewAgent,
    UXAgent,
)
from .config import AgentRunnerConfig

logger = structlog.get_logger(__name__)


class AgentRunner:
    """Dispatches a StageDispatchEvent to the correct agent and manages lifecycle."""

    def __init__(
        self,
        llm: LLMProvider,
        event_bus: EventBusClient | InMemoryEventBus,
        config: AgentRunnerConfig,
    ) -> None:
        self.llm = llm
        self.event_bus = event_bus
        self.config = config

        self.agents = {
            "prd": PRDAgent(llm),
            "architect": ArchitectAgent(llm),
            "market": MarketAgent(llm),
            "ux": UXAgent(llm),
            "engineering": EngineeringAgent(llm),
            "developer": DeveloperAgent(llm),
            "qa": QAAgent(llm),
            "regression": RegressionAgent(llm),
            "review": ReviewAgent(llm),
            "devops": DevOpsAgent(llm),
            "readme": ReadmeAgent(llm),
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def handle_dispatch(self, event: StageDispatchEvent) -> None:
        """Main entry-point called by the event bus consumer loop.

        Lifecycle:
          1. Publish StageStartedEvent
          2. Reconstruct PipelineContext from the dispatch event
          3. Execute the appropriate agent
          4. POST the artifact to the artifact-store
          5. Publish StageCompleteEvent

        On any exception: publish StageFailedEvent (with retry_count=0).
        """
        stage_name = event.stage_name
        log = logger.bind(
            pipeline_id=event.pipeline_id,
            stage_id=event.stage_id,
            stage_name=stage_name,
            worker_id=self.config.WORKER_ID,
        )
        log.info("stage_dispatch_received")

        # 1. Publish StageStartedEvent
        await self.event_bus.publish(
            StageStartedEvent(
                pipeline_id=event.pipeline_id,
                stage_id=event.stage_id,
                stage_name=stage_name,
                worker_id=self.config.WORKER_ID,
            )
        )

        start_ms = int(time.monotonic() * 1000)

        try:
            # 2. Reconstruct PipelineContext
            ctx = self._build_context(event)

            # 3. Execute agent
            agent = self._get_agent(stage_name)
            log.info("agent_executing")
            artifact = await agent.execute(ctx)
            log.info("agent_complete", artifact_id=artifact.artifact_id)

            # 4. POST artifact to artifact-store
            artifact_url, artifact_hash = await self._post_artifact(
                event.pipeline_id, event.stage_id, stage_name, artifact
            )

            duration_ms = int(time.monotonic() * 1000) - start_ms

            # 5. Publish StageCompleteEvent
            await self.event_bus.publish(
                StageCompleteEvent(
                    pipeline_id=event.pipeline_id,
                    stage_id=event.stage_id,
                    stage_name=stage_name,
                    artifact_url=artifact_url,
                    artifact_hash=artifact_hash,
                    duration_ms=duration_ms,
                    llm_tokens_used=0,   # placeholder — provider doesn't expose yet
                    llm_cost_usd=0.0,
                )
            )
            log.info("stage_complete", duration_ms=duration_ms, artifact_url=artifact_url)

        except Exception as exc:  # noqa: BLE001
            duration_ms = int(time.monotonic() * 1000) - start_ms
            log.exception("stage_failed", error=str(exc))
            await self.event_bus.publish(
                StageFailedEvent(
                    pipeline_id=event.pipeline_id,
                    stage_id=event.stage_id,
                    stage_name=stage_name,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    retry_count=0,
                )
            )
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_agent(self, stage_name: str):
        """Return the agent for *stage_name*, raising ValueError if unknown."""
        agent = self.agents.get(stage_name)
        if agent is None:
            raise ValueError(
                f"No agent registered for stage '{stage_name}'. "
                f"Available stages: {sorted(self.agents.keys())}"
            )
        return agent

    def _build_context(self, event: StageDispatchEvent) -> PipelineContext:
        """Reconstruct a PipelineContext from a StageDispatchEvent."""
        raw_cfg: dict[str, Any] = event.config or {}

        pipeline_config = PipelineConfig(
            llm_provider=raw_cfg.get("llm_provider", self.config.LLM_PROVIDER),
            llm_model=raw_cfg.get("llm_model", self.config.LLM_MODEL),
            artifact_store_url=self.config.ARTIFACT_STORE_URL,
        )

        return PipelineContext(
            run_id=event.run_id,
            idea=event.idea,
            config=pipeline_config,
            artifacts=dict(event.prior_artifacts),
        )

    async def _post_artifact(
        self,
        pipeline_id: str,
        stage_id: str,
        stage_name: str,
        artifact: Any,
    ) -> tuple[str, str]:
        """POST the serialised artifact to the artifact-store.

        Returns ``(artifact_url, sha256_hex)``.

        Falls back gracefully if the artifact-store is unreachable — returns a
        placeholder URL so the pipeline can continue.
        """
        payload_bytes: bytes
        if hasattr(artifact, "model_dump_json"):
            payload_bytes = artifact.model_dump_json().encode()
        else:
            import json
            payload_bytes = json.dumps(str(artifact)).encode()

        artifact_hash = hashlib.sha256(payload_bytes).hexdigest()
        artifact_url = (
            f"{self.config.ARTIFACT_STORE_URL}/artifacts"
            f"/{pipeline_id}/{stage_id}/{stage_name}"
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    artifact_url,
                    content=payload_bytes,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                logger.debug(
                    "artifact_stored",
                    status=resp.status_code,
                    url=artifact_url,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "artifact_store_unavailable",
                error=str(exc),
                fallback_url=artifact_url,
            )
            # Do not fail the stage — the artifact was produced successfully.

        return artifact_url, artifact_hash
