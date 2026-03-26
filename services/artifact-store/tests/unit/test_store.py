import pytest
from apf_artifact_store.store import ArtifactStore, ArtifactNotFoundError


@pytest.fixture
async def store(tmp_path):
    s = ArtifactStore(str(tmp_path / 'data'))
    await s.initialize()
    return s


async def test_write_creates_file(store, tmp_path):
    record = await store.write('p1', 'prd', 'prd-agent', b'content here')
    fp = store.base_path / record.storage_key
    assert fp.exists()


async def test_write_returns_record_with_hash(store):
    record = await store.write('p1', 'prd', 'prd-agent', b'hello')
    import hashlib
    expected = hashlib.sha256(b'hello').hexdigest()
    assert record.content_hash == expected


async def test_read_returns_content(store):
    record = await store.write('p1', 'prd', 'prd-agent', b'test content')
    data = await store.read(record.artifact_id)
    assert data == b'test content'


async def test_get_record_returns_metadata(store):
    record = await store.write('p1', 'prd', 'prd-agent', b'data')
    fetched = store.get_record(record.artifact_id)
    assert fetched is not None
    assert fetched.pipeline_id == 'p1'


async def test_list_pipeline_returns_all_artifacts(store):
    await store.write('p1', 'prd', 'prd-agent', b'prd content')
    await store.write('p1', 'architect', 'arch-agent', b'arch content')
    await store.write('p2', 'prd', 'prd-agent', b'other pipeline')
    records = store.list_pipeline('p1')
    assert len(records) == 2


async def test_get_latest_returns_highest_version(store):
    await store.write('p1', 'prd', 'prd-agent', b'v1')
    await store.write('p1', 'prd', 'prd-agent', b'v2')
    latest = store.get_latest('p1', 'prd')
    assert latest is not None
    assert latest.version == 2


async def test_versioning_increments(store):
    r1 = await store.write('p1', 'prd', 'prd-agent', b'v1')
    r2 = await store.write('p1', 'prd', 'prd-agent', b'v2')
    assert r1.version == 1
    assert r2.version == 2


async def test_get_versions_sorted(store):
    await store.write('p1', 'prd', 'prd-agent', b'v1')
    await store.write('p1', 'prd', 'prd-agent', b'v2')
    versions = store.get_versions('p1', 'prd')
    assert [v.version for v in versions] == [1, 2]


async def test_delete_removes_record(store):
    record = await store.write('p1', 'prd', 'prd-agent', b'data')
    await store.delete(record.artifact_id)
    assert store.get_record(record.artifact_id) is None


async def test_delete_removes_file(store):
    record = await store.write('p1', 'prd', 'prd-agent', b'data')
    fp = store.base_path / record.storage_key
    await store.delete(record.artifact_id)
    assert not fp.exists()


async def test_read_nonexistent_raises(store):
    with pytest.raises(ArtifactNotFoundError):
        await store.read('nonexistent-id')
