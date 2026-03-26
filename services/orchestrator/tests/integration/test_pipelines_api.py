import pytest


async def test_health_endpoint(client):
    resp = await client.get('/healthz')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'


async def test_create_pipeline_requires_auth(client):
    resp = await client.post('/api/v1/pipelines', json={'idea': 'build something'})
    assert resp.status_code == 401


async def test_create_pipeline_201(client, auth_headers):
    resp = await client.post('/api/v1/pipelines', json={'idea': 'build a todo app'}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert 'id' in data
    assert data['status'] == 'running'


async def test_get_pipeline_200(client, auth_headers):
    create = await client.post('/api/v1/pipelines', json={'idea': 'test'}, headers=auth_headers)
    pipeline_id = create.json()['id']
    resp = await client.get(f'/api/v1/pipelines/{pipeline_id}', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()['id'] == pipeline_id


async def test_get_pipeline_404(client, auth_headers):
    resp = await client.get('/api/v1/pipelines/nonexistent-id', headers=auth_headers)
    assert resp.status_code == 404


async def test_list_pipelines_returns_structure(client, auth_headers):
    resp = await client.get('/api/v1/pipelines', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert 'items' in data and 'total' in data


async def test_list_pipelines_paginated(client, auth_headers):
    for i in range(3):
        await client.post('/api/v1/pipelines', json={'idea': f'idea {i}'}, headers=auth_headers)
    resp = await client.get('/api/v1/pipelines?page=1&size=2', headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()['items']) <= 2


async def test_cancel_pipeline(client, auth_headers):
    create = await client.post('/api/v1/pipelines', json={'idea': 'cancel me'}, headers=auth_headers)
    pipeline_id = create.json()['id']
    resp = await client.delete(f'/api/v1/pipelines/{pipeline_id}', headers=auth_headers)
    assert resp.status_code == 200
