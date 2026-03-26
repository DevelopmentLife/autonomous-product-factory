import pytest


async def test_health_returns_ok(client):
    resp = await client.get('/healthz')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'


async def test_create_artifact_201(client, sample_payload):
    resp = await client.post('/api/v1/artifacts', json=sample_payload)
    assert resp.status_code == 201


async def test_create_artifact_returns_hash(client, sample_payload):
    resp = await client.post('/api/v1/artifacts', json=sample_payload)
    data = resp.json()
    assert 'content_hash' in data
    assert len(data['content_hash']) == 64


async def test_create_artifact_returns_version_1(client, sample_payload):
    resp = await client.post('/api/v1/artifacts', json=sample_payload)
    assert resp.json()['version'] == 1


async def test_get_artifact_metadata_200(client, sample_payload):
    create = await client.post('/api/v1/artifacts', json=sample_payload)
    artifact_id = create.json()['artifact_id']
    resp = await client.get(f'/api/v1/artifacts/{artifact_id}')
    assert resp.status_code == 200


async def test_get_artifact_metadata_404(client):
    resp = await client.get('/api/v1/artifacts/nonexistent-id')
    assert resp.status_code == 404


async def test_get_artifact_content_200(client, sample_payload):
    create = await client.post('/api/v1/artifacts', json=sample_payload)
    artifact_id = create.json()['artifact_id']
    resp = await client.get(f'/api/v1/artifacts/{artifact_id}/content')
    assert resp.status_code == 200
    assert b'PRD' in resp.content


async def test_list_pipeline_artifacts(client, sample_payload):
    await client.post('/api/v1/artifacts', json=sample_payload)
    resp = await client.get('/api/v1/pipelines/pipe-1/artifacts')
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_get_latest_artifact_for_stage(client, sample_payload):
    await client.post('/api/v1/artifacts', json=sample_payload)
    resp = await client.get('/api/v1/pipelines/pipe-1/artifacts/prd')
    assert resp.status_code == 200
    assert resp.json()['stage_name'] == 'prd'


async def test_versioning_creates_v2(client, sample_payload):
    await client.post('/api/v1/artifacts', json=sample_payload)
    r2 = await client.post('/api/v1/artifacts', json={**sample_payload, 'content': 'updated'})
    assert r2.json()['version'] == 2


async def test_delete_artifact_204(client, sample_payload):
    create = await client.post('/api/v1/artifacts', json=sample_payload)
    artifact_id = create.json()['artifact_id']
    resp = await client.delete(f'/api/v1/artifacts/{artifact_id}')
    assert resp.status_code == 204
