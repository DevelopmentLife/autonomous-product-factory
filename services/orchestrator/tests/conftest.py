import pytest
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select


@pytest.fixture
async def app():
    os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'
    os.environ['APF_SECRET_KEY'] = 'test-secret-key-123'
    from apf_orchestrator.config import get_settings
    get_settings.cache_clear()
    from apf_orchestrator.main import create_app
    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        yield test_app
    try:
        engine = test_app.state.engine
        await engine.dispose()
    except Exception:
        pass


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        yield c


@pytest.fixture
async def auth_token(app):
    from apf_orchestrator.db import User
    from apf_orchestrator.core.auth import hash_password, create_access_token
    async with app.state.session_factory() as s:
        result = await s.execute(select(User).where(User.email == 'tester@apf.local'))
        if not result.scalar_one_or_none():
            s.add(User(id='tester-1', email='tester@apf.local',
                       hashed_password=hash_password('testpass'),
                       role='admin', is_active=True))
            await s.commit()
    settings = app.state.pipeline_engine.settings
    return create_access_token(
        {'sub': 'tester-1', 'email': 'tester@apf.local', 'role': 'admin'},
        settings.APF_SECRET_KEY, settings.APF_JWT_ALGORITHM, 60,
    )


@pytest.fixture
def auth_headers(auth_token):
    return {'Authorization': f'Bearer {auth_token}'}
