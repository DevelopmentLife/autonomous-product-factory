import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ..core.auth import decode_token
from ..config import get_settings

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self._conns: dict = {}

    async def connect(self, pid: str, ws: WebSocket):
        await ws.accept()
        self._conns.setdefault(pid, []).append(ws)

    def disconnect(self, pid: str, ws: WebSocket):
        conns = self._conns.get(pid, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, pid: str, msg: dict):
        for ws in list(self._conns.get(pid, [])):
            try:
                await ws.send_json(msg)
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket('/ws/pipelines/{pipeline_id}')
async def pipeline_ws(pipeline_id: str, websocket: WebSocket, token: str = Query(...)):
    settings = get_settings()
    try:
        decode_token(token, settings.APF_SECRET_KEY, settings.APF_JWT_ALGORITHM)
    except Exception:
        await websocket.close(code=4001)
        return
    await manager.connect(pipeline_id, websocket)
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({'type': 'ping'})
    except WebSocketDisconnect:
        manager.disconnect(pipeline_id, websocket)
    except Exception:
        manager.disconnect(pipeline_id, websocket)
