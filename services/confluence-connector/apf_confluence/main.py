from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .client import ConfluenceClient
from .config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(title="APF Confluence Connector", lifespan=lifespan)


class ArtifactPayload(BaseModel):
    pipeline_id: str
    stage: str
    content: str
    title: str = ""


class PipelinePayload(BaseModel):
    pipeline_id: str
    idea: str
    artifacts: dict[str, str] = {}


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _markdown_to_storage(md: str) -> str:
    escaped = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    out = []
    for line in escaped.splitlines():
        if line.startswith("# "):
            out.append("<h1>" + line[2:] + "</h1>")
        elif line.startswith("## "):
            out.append("<h2>" + line[3:] + "</h2>")
        elif line.startswith("### "):
            out.append("<h3>" + line[4:] + "</h3>")
        elif line.startswith("- "):
            out.append("<li>" + line[2:] + "</li>")
        elif line.strip():
            out.append("<p>" + line + "</p>")
    return chr(10).join(out)


@app.post("/publish/artifact")
async def publish_artifact(payload: ArtifactPayload) -> dict[str, Any]:
    settings = get_settings()
    if not settings.CONFLUENCE_URL:
        raise HTTPException(status_code=503, detail="Confluence not configured")
    client = ConfluenceClient(settings)
    title = payload.title or "[APF] " + payload.stage.upper() + " -- " + payload.pipeline_id[:8]
    storage_body = _markdown_to_storage(payload.content)
    existing = await client.get_page_by_title(title)
    if existing:
        page_id = existing["id"]
        version = existing["version"]["number"] + 1
        page = await client.update_page(page_id, title, storage_body, version)
    else:
        page = await client.create_page(title, storage_body)
    return {"page_id": page.get("id"), "title": title, "pipeline_id": payload.pipeline_id}


@app.post("/publish/pipeline-summary")
async def publish_pipeline_summary(payload: PipelinePayload) -> dict[str, Any]:
    settings = get_settings()
    if not settings.CONFLUENCE_URL:
        raise HTTPException(status_code=503, detail="Confluence not configured")
    client = ConfluenceClient(settings)
    title = "[APF] Pipeline Summary -- " + payload.idea[:60]
    rows = "".join(
        "<tr><td>" + stage + "</td><td><p>" + content[:200] + "...</p></td></tr>"
        for stage, content in payload.artifacts.items()
    )
    body = ("<h1>Pipeline: " + payload.pipeline_id + "</h1>"
            "<p>Idea: " + payload.idea + "</p>"
            "<table><tbody><tr><th>Stage</th><th>Artifact</th></tr>" + rows + "</tbody></table>")
    page = await client.create_page(title, body)
    return {"page_id": page.get("id"), "title": title, "pipeline_id": payload.pipeline_id}
