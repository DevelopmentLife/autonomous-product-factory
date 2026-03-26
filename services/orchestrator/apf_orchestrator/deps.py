from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from .core.auth import decode_token
from .config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')


async def get_db(request: Request):
    async with request.app.state.session_factory() as session:
        yield session


async def get_current_user(token: str = Depends(oauth2_scheme)):
    settings = get_settings()
    try:
        payload = decode_token(token, settings.APF_SECRET_KEY, settings.APF_JWT_ALGORITHM)
        uid = payload.get('sub')
        if not uid:
            raise HTTPException(status_code=401, detail='Invalid token')
        return {'id': uid, 'email': payload.get('email'), 'role': payload.get('role')}
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid token')


def get_engine(request: Request):
    return request.app.state.pipeline_engine
