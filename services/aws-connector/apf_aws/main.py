from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import get_settings
from .deployer import AWSDeployer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(title='APF AWS Connector', lifespan=lifespan)


class DeployRequest(BaseModel):
    pipeline_id: str
    image_tag: str = 'latest'
    task_definition: str = ''
    cluster: str = ''
    service: str = ''


class StatusRequest(BaseModel):
    cluster: str = ''
    service: str = ''


@app.get('/healthz')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/deploy')
async def deploy(payload: DeployRequest) -> dict[str, Any]:
    settings = get_settings()
    if not settings.AWS_ECS_CLUSTER and not payload.cluster:
        raise HTTPException(status_code=503, detail='AWS ECS not configured')
    deployer = AWSDeployer(settings)
    result = await deployer.deploy_service(
        task_definition=payload.task_definition or None,
        cluster=payload.cluster or None,
        service=payload.service or None,
    )
    return {**result, 'pipeline_id': payload.pipeline_id}


@app.post('/status')
async def deployment_status(payload: StatusRequest) -> dict[str, Any]:
    settings = get_settings()
    deployer = AWSDeployer(settings)
    return await deployer.get_deployment_status(
        cluster=payload.cluster or None,
        service=payload.service or None,
    )
