import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response


@pytest.fixture()
def settings():
    from apf_jira.config import Settings
    return Settings(
        JIRA_URL='https://example.atlassian.net',
        JIRA_USER='user@example.com',
        JIRA_API_TOKEN='token',
        JIRA_PROJECT_KEY='APF',
    )


@pytest.mark.asyncio
async def test_create_issue(settings):
    from apf_jira.client import JiraClient
    client = JiraClient(settings)
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {'key': 'APF-1', 'id': '10001'}
    with patch('httpx.AsyncClient') as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http
        result = await client.create_issue('Test', 'Description', labels=['apf'])
    assert result['key'] == 'APF-1'


@pytest.mark.asyncio
async def test_add_comment(settings):
    from apf_jira.client import JiraClient
    client = JiraClient(settings)
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {'id': '99'}
    with patch('httpx.AsyncClient') as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http
        result = await client.add_comment('APF-1', 'hello')
    assert result['id'] == '99'


@pytest.mark.asyncio
async def test_stage_started_endpoint(settings):
    from fastapi.testclient import TestClient
    with patch('apf_jira.main.get_settings', return_value=settings):
        with patch('apf_jira.main.JiraClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.create_issue = AsyncMock(return_value={'key': 'APF-2'})
            MockClient.return_value = mock_instance
            from apf_jira.main import app
            client = TestClient(app)
            resp = client.post('/notify/stage-started', json={
                'pipeline_id': 'pipe-1',
                'stage': 'prd',
                'idea': 'test idea',
            })
    assert resp.status_code == 200
    assert resp.json()['issue_key'] == 'APF-2'


def test_health():
    from fastapi.testclient import TestClient
    from apf_jira.main import app
    client = TestClient(app)
    assert client.get('/healthz').json() == {'status': 'ok'}
