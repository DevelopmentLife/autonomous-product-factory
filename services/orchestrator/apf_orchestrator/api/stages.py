from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from ..db import Stage
from ..deps import get_db, get_current_user, get_engine

router = APIRouter(prefix='/api/v1/pipelines', tags=['stages'])


@router.get('/{pipeline_id}/stages')
async def list_stages(pipeline_id: str, db=Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Stage).where(Stage.pipeline_id == pipeline_id))
    return [_s(s) for s in result.scalars().all()]


@router.post('/{pipeline_id}/stages/{stage_name}/approve')
async def approve_stage(pipeline_id: str, stage_name: str, body: dict,
                         engine=Depends(get_engine), db=Depends(get_db), cu=Depends(get_current_user)):
    result = await db.execute(select(Stage).where(Stage.pipeline_id == pipeline_id, Stage.stage_name == stage_name))
    stage = result.scalar_one_or_none()
    if not stage:
        raise HTTPException(404, 'Stage not found')
    await engine.approve_stage(pipeline_id, stage.id, body.get('approved', True), cu['id'])
    return {'stage_name': stage_name, 'approved': body.get('approved', True)}


def _s(s):
    return {'id': s.id, 'pipeline_id': s.pipeline_id, 'stage_name': s.stage_name,
            'status': s.status, 'retry_count': s.retry_count, 'error_message': s.error_message,
            'started_at': s.started_at.isoformat() if s.started_at else None,
            'completed_at': s.completed_at.isoformat() if s.completed_at else None}
