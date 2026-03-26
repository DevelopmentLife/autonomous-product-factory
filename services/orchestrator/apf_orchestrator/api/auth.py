from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from ..db import User
from ..core.auth import verify_password, create_access_token
from ..deps import get_db, get_current_user
from ..config import get_settings

router = APIRouter(prefix='/api/v1/auth', tags=['auth'])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


@router.post('/login', response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    settings = get_settings()
    result = await db.execute(select(User).where(User.email == form.username, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    token = create_access_token(
        {'sub': user.id, 'email': user.email, 'role': user.role},
        settings.APF_SECRET_KEY, settings.APF_JWT_ALGORITHM, settings.APF_JWT_EXPIRE_MINUTES,
    )
    return TokenResponse(access_token=token)


@router.get('/whoami')
async def whoami(current_user=Depends(get_current_user)):
    return current_user
