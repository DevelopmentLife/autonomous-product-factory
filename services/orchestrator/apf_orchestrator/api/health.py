from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=['health'])


@router.get('/healthz')
async def healthz():
    return {'status': 'ok', 'version': '0.1.0'}


@router.get('/readyz')
async def readyz(request: Request):
    try:
        async with request.app.state.session_factory() as s:
            await s.execute(text('SELECT 1'))
        return {'status': 'ok', 'db': 'ok'}
    except Exception as exc:
        return JSONResponse(status_code=503, content={'status': 'error', 'detail': str(exc)})
