import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from ..db import ConnectorConfig
from ..deps import get_db, get_current_user

router = APIRouter(prefix='/api/v1/connectors', tags=['connectors'])
CONNECTOR_TYPES = ['github', 'slack', 'jira', 'confluence', 'aws']


@router.get('')
async def list_connectors(db=Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(ConnectorConfig))
    configs = {c.connector_type: c for c in result.scalars().all()}
    return [{'type': t, 'enabled': configs[t].enabled if t in configs else False,
             'config': configs[t].config if t in configs else {}} for t in CONNECTOR_TYPES]


@router.put('/{connector_type}')
async def upsert_connector(connector_type: str, body: dict,
                            db=Depends(get_db), _=Depends(get_current_user)):
    if connector_type not in CONNECTOR_TYPES:
        raise HTTPException(400, f'Unknown connector: {connector_type}')
    result = await db.execute(select(ConnectorConfig).where(ConnectorConfig.connector_type == connector_type))
    c = result.scalar_one_or_none()
    now = datetime.utcnow()
    if c:
        c.enabled = body.get('enabled', c.enabled)
        c.config = body.get('config', c.config)
        c.updated_at = now
    else:
        c = ConnectorConfig(id=str(uuid.uuid4()), connector_type=connector_type,
                            enabled=body.get('enabled', False), config=body.get('config', {}),
                            created_at=now, updated_at=now)
        db.add(c)
    await db.commit()
    return {'type': connector_type, 'enabled': c.enabled}


@router.delete('/{connector_type}')
async def disable_connector(connector_type: str, db=Depends(get_db), _=Depends(get_current_user)):
    if connector_type not in CONNECTOR_TYPES:
        raise HTTPException(400, f'Unknown connector: {connector_type}')
    await db.execute(update(ConnectorConfig).where(
        ConnectorConfig.connector_type == connector_type).values(enabled=False))
    await db.commit()
    return {'type': connector_type, 'enabled': False}
