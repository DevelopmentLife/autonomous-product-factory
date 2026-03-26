from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(prefix='/api/v1', tags=['artifacts'])


class CreateArtifactRequest(BaseModel):
    pipeline_id: str
    stage_name: str
    agent_name: str
    content: str
    content_type: str = 'text/plain'


@router.post('/artifacts', status_code=201)
async def create_artifact(body: CreateArtifactRequest, request: Request):
    store = request.app.state.store
    settings = request.app.state.settings
    content_bytes = body.content.encode('utf-8')
    max_bytes = settings.MAX_ARTIFACT_SIZE_MB * 1024 * 1024
    if len(content_bytes) > max_bytes:
        raise HTTPException(413, 'Artifact exceeds size limit')
    record = await store.write(body.pipeline_id, body.stage_name, body.agent_name,
                               content_bytes, body.content_type)
    return record.model_dump(mode='json')


@router.get('/artifacts/{artifact_id}')
async def get_artifact_metadata(artifact_id: str, request: Request):
    record = request.app.state.store.get_record(artifact_id)
    if not record:
        raise HTTPException(404, 'Artifact not found')
    return record.model_dump(mode='json')


@router.get('/artifacts/{artifact_id}/content')
async def get_artifact_content(artifact_id: str, request: Request):
    store = request.app.state.store
    record = store.get_record(artifact_id)
    if not record:
        raise HTTPException(404, 'Artifact not found')
    try:
        content = await store.read(artifact_id)
    except KeyError:
        raise HTTPException(404, 'Artifact content missing')
    return Response(content=content, media_type=record.content_type)


@router.get('/pipelines/{pipeline_id}/artifacts')
async def list_pipeline_artifacts(pipeline_id: str, request: Request):
    records = request.app.state.store.list_pipeline(pipeline_id)
    return [r.model_dump(mode='json') for r in records]


@router.get('/pipelines/{pipeline_id}/artifacts/{stage_name}')
async def get_latest_artifact(pipeline_id: str, stage_name: str, request: Request):
    record = request.app.state.store.get_latest(pipeline_id, stage_name)
    if not record:
        raise HTTPException(404, 'No artifact found for this stage')
    return record.model_dump(mode='json')


@router.get('/pipelines/{pipeline_id}/artifacts/{stage_name}/versions')
async def get_artifact_versions(pipeline_id: str, stage_name: str, request: Request):
    records = request.app.state.store.get_versions(pipeline_id, stage_name)
    return [r.model_dump(mode='json') for r in records]


@router.delete('/artifacts/{artifact_id}', status_code=204)
async def delete_artifact(artifact_id: str, request: Request):
    store = request.app.state.store
    if not store.get_record(artifact_id):
        raise HTTPException(404, 'Artifact not found')
    await store.delete(artifact_id)
    return None
