import pytest, os
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def tmp_storage(tmp_path):
    return str(tmp_path / 'artifacts')


@pytest.fixture
async def app(tmp_storage):
    os.environ['LOCAL_STORAGE_PATH'] = tmp_storage
    from apf_artifact_store.config import get_settings
    get_settings.cache_clear()
    from apf_artifact_store.main import create_app
    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        yield test_app


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        yield c


@pytest.fixture
def sample_payload():
    return {'pipeline_id': 'pipe-1', 'stage_name': 'prd', 'agent_name': 'prd-agent',
            'content': '# PRD\n\nProduct requirements.', 'content_type': 'text/markdown'}
