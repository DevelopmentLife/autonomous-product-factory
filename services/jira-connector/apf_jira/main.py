from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .client import JiraClient
from .config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(title='APF Jira Connector', lifespan=lifespan)


class StagePayload(BaseModel):
    pipeline_id: str
    stage: str
    idea: str
    status: str = 'pending'


class PipelinePayload(BaseModel):
    pipeline_id: str
    idea: str
    pr_url: str = ''


@app.get('/healthz')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/notify/stage-started')
async def stage_started(payload: StagePayload) -> dict[str, Any]:
    settings = get_settings()
    if not settings.JIRA_URL:
        raise HTTPException(status_code=503, detail='Jira not configured')
    client = JiraClient(settings)
    nl = chr(10)
    desc = 'Pipeline: ' + payload.pipeline_id + nl + 'Stage: ' + payload.stage + nl + 'Status: ' + payload.status
    issue = await client.create_issue(
        summary='[APF] ' + payload.stage.upper() + ' -- ' + payload.idea[:80],
        description=desc,
        issue_type='Task',
        labels=['apf', payload.stage],
    )
    return {'issue_key': issue.get('key'), 'pipeline_id': payload.pipeline_id}


@app.post('/notify/pipeline-complete')
async def pipeline_complete(payload: PipelinePayload) -> dict[str, Any]:
    settings = get_settings()
    if not settings.JIRA_URL:
        raise HTTPException(status_code=503, detail='Jira not configured')
    client = JiraClient(settings)
    nl = chr(10)
    desc = 'Pipeline: ' + payload.pipeline_id + nl + 'PR: ' + payload.pr_url + nl + 'All stages completed successfully.'
    issue = await client.create_issue(
        summary='[APF] Pipeline complete -- ' + payload.idea[:80],
        description=desc,
        issue_type='Story',
        labels=['apf', 'pipeline-complete'],
    )
    return {'issue_key': issue.get('key'), 'pipeline_id': payload.pipeline_id}
