import pytest


async def test_list_connectors_returns_all_types(client, auth_headers):
    resp = await client.get('/api/v1/connectors', headers=auth_headers)
    assert resp.status_code == 200
    types = {c['type'] for c in resp.json()}
    assert {'github', 'slack', 'jira', 'confluence', 'aws'} == types


async def test_enable_slack_connector(client, auth_headers):
    resp = await client.put('/api/v1/connectors/slack',
                             json={'enabled': True, 'config': {'channel': '#apf'}},
                             headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()['enabled'] is True


async def test_disable_connector(client, auth_headers):
    await client.put('/api/v1/connectors/jira', json={'enabled': True}, headers=auth_headers)
    resp = await client.delete('/api/v1/connectors/jira', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()['enabled'] is False


async def test_unknown_connector_type_400(client, auth_headers):
    resp = await client.put('/api/v1/connectors/unknown', json={'enabled': True}, headers=auth_headers)
    assert resp.status_code == 400
