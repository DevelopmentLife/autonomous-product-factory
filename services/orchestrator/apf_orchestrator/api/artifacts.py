"""Artifact listing and retrieval endpoints (proxied from artifact-store)."""

from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from apf_db import Artifact, Pipeline, Stage

from ..config import settings
from ..deps import CurrentUser, DBSession

router = APIRouter(prefix="/api/v1/pipelines", tags=["artifacts"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ArtifactResponse(BaseModel):
    id: str
    pipeline_id: str
    stage_id: str
    agent_name: str
    artifact_type: str
    content_url: str
    content_hash: str
    content_size_bytes: int
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/{pipeline_id}/artifacts",
    response_model=list[ArtifactResponse],
    summary="List artifacts for a pipeline",
)
async def list_artifacts(
    pipeline_id: str,
    db: DBSession,
    user: CurrentUser,
) -> list[ArtifactResponse]:
    pipeline = await db.get(Pipeline, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    result = await db.execute(
        select(Artifact)
        .where(Artifact.pipeline_id == pipeline_id)
        .order_by(Artifact.created_at.asc())
    )
    artifacts = result.scalars().all()
    return [ArtifactResponse.model_validate(a) for a in artifacts]


@router.get(
    "/{pipeline_id}/artifacts/{stage_name}",
    summary="Get artifact content for a stage (proxied from artifact-store)",
)
async def get_artifact(
    pipeline_id: str,
    stage_name: str,
    db: DBSession,
    user: CurrentUser,
) -> StreamingResponse:
    # Find the stage
    stage_result = await db.execute(
        select(Stage).where(
            Stage.pipeline_id == pipeline_id,
            Stage.stage_name == stage_name,
        )
    )
    stage = stage_result.scalar_one_or_none()
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage not found")

    # Find latest artifact for this stage
    artifact_result = await db.execute(
        select(Artifact)
        .where(Artifact.stage_id == stage.id)
        .order_by(Artifact.version.desc())
        .limit(1)
    )
    artifact = artifact_result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="No artifact found for this stage")

    # Proxy the content from the artifact store
    artifact_url = artifact.content_url
    # If the URL is relative, prepend the artifact store base URL
    if not artifact_url.startswith("http"):
        artifact_url = f"{settings.ARTIFACT_STORE_URL.rstrip('/')}/{artifact_url.lstrip('/')}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream = await client.get(artifact_url)
        upstream.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Artifact store error: {exc}")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Cannot reach artifact store: {exc}")

    return StreamingResponse(
        content=iter([upstream.content]),
        media_type=upstream.headers.get("content-type", "application/octet-stream"),
        headers={"X-Artifact-Hash": artifact.content_hash},
    )
