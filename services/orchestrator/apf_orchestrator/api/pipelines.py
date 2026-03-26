from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update
from datetime import datetime
from ..db import Pipeline
from ..deps import get_db, get_current_user, get_engine

router = APIRouter(prefix='/api/v1/pipelines', tags=['pipelines'])


class CreatePipelineRequest(BaseModel):
    idea: str
    config: dict = {}


@router.post('', status_code=201)
async def create_pipeline(body: CreatePipelineRequest, current_user=Depends(get_current_user), engine=Depends(get_engine)):
    pipeline_id = await engine.create_and_start(body.idea, body.config, current_user['id'])
    return {'id': pipeline_id, 'status': 'running', 'idea': body.idea}


@router.get('')
async def list_pipelines(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                          db=Depends(get_db), current_user=Depends(get_current_user)):
    offset = (page - 1) * size
    result = await db.execute(select(Pipeline).order_by(Pipeline.created_at.desc()).offset(offset).limit(size))
    pipelines = result.scalars().all()
    total = (await db.execute(select(func.count(Pipeline.id)))).scalar()
    return {'items': [_p(p) for p in pipelines], 'total': total, 'page': page, 'size': size}


@router.get('/{pipeline_id}')
async def get_pipeline(pipeline_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail='Pipeline not found')
    return _p(p)


@router.delete('/{pipeline_id}')
async def cancel_pipeline(pipeline_id: str, engine=Depends(get_engine), current_user=Depends(get_current_user)):
    await engine.cancel(pipeline_id)
    return {'id': pipeline_id, 'status': 'cancelled'}


@router.post('/{pipeline_id}/pause')
async def pause_pipeline(pipeline_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    await db.execute(update(Pipeline).where(Pipeline.id == pipeline_id).values(status='paused', updated_at=datetime.utcnow()))
    await db.commit()
    return {'id': pipeline_id, 'status': 'paused'}


@router.post('/{pipeline_id}/resume')
async def resume_pipeline(pipeline_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    await db.execute(update(Pipeline).where(Pipeline.id == pipeline_id).values(status='running', updated_at=datetime.utcnow()))
    await db.commit()
    return {'id': pipeline_id, 'status': 'running'}


def _p(p: Pipeline) -> dict:
    return {
        'id': p.id, 'idea': p.idea, 'status': p.status,
        'current_stage': p.current_stage, 'github_pr_url': p.github_pr_url,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None,
    }
