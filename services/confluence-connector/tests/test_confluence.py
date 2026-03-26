import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture()
def settings():
    from apf_confluence.config import Settings
    return Settings(
        CONFLUENCE_URL='https://example.atlassian.net',
        CONFLUENCE_USER='user@example.com',
        CONFLUENCE_API_TOKEN='token',
        CONFLUENCE_SPACE_KEY='APF',
    )


@pytest.mark.asyncio
async def test_create_page(settings):
    from apf_confluence.client import ConfluenceClient
    client = ConfluenceClient(settings)
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {'id': '111', 'title': 'Test'}
    with patch('httpx.AsyncClient') as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http
        result = await client.create_page('Test', '<p>body</p>')
    assert result['id'] == '111'


@pytest.mark.asyncio
async def test_publish_artifact_endpoint(settings):
    from fastapi.testclient import TestClient
    with patch('apf_confluence.main.get_settings', return_value=settings):
        with patch('apf_confluence.main.ConfluenceClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get_page_by_title = AsyncMock(return_value=None)
            mock_instance.create_page = AsyncMock(return_value={'id': '222'})
            MockClient.return_value = mock_instance
            from apf_confluence.main import app
            client = TestClient(app)
            payload = {'pipeline_id': 'pipe-1', 'stage': 'prd', 'content': '# PRD heading'}
            resp = client.post('/publish/artifact', json=payload)
    assert resp.status_code == 200
    assert resp.json()['page_id'] == '222'


def test_health():
    from fastapi.testclient import TestClient
    from apf_confluence.main import app
    client = TestClient(app)
    assert client.get('/healthz').json() == {'status': 'ok'}
