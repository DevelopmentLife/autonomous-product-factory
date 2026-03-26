from fastapi import APIRouter, Request
router = APIRouter()


@router.get('/healthz')
async def healthz():
    return {'status': 'ok', 'version': '0.1.0'}


@router.get('/readyz')
async def readyz(request: Request):
    store = request.app.state.store
    if store.base_path.exists():
        return {'status': 'ok', 'storage': 'ok'}
    return {'status': 'error', 'storage': 'path not found'}
