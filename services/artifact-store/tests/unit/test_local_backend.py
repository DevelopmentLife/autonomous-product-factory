"""Unit tests for the LocalFileSystemBackend."""

from __future__ import annotations

import pytest
import pytest_asyncio

from apf_artifact_store.backends.local import LocalFileSystemBackend
from apf_artifact_store.models import ArtifactNotFoundError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def backend(tmp_path):
    """Return a LocalFileSystemBackend rooted in a temporary directory."""
    return LocalFileSystemBackend(base_path=str(tmp_path))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_creates_file(backend, tmp_path):
    key = "pipeline-1/stage-a/v1/artifact.txt"
    await backend.write(key, b"hello world")
    assert (tmp_path / key).exists()


@pytest.mark.asyncio
async def test_read_returns_content(backend):
    key = "pipeline-1/stage-a/v1/artifact.txt"
    content = b"test content"
    await backend.write(key, content)
    result = await backend.read(key)
    assert result == content


@pytest.mark.asyncio
async def test_exists_true_after_write(backend):
    key = "pipeline-1/stage-a/v1/artifact.txt"
    await backend.write(key, b"data")
    assert await backend.exists(key) is True


@pytest.mark.asyncio
async def test_exists_false_before_write(backend):
    key = "pipeline-1/stage-a/v1/nonexistent.txt"
    assert await backend.exists(key) is False


@pytest.mark.asyncio
async def test_delete_removes_file(backend, tmp_path):
    key = "pipeline-1/stage-a/v1/artifact.txt"
    await backend.write(key, b"data")
    await backend.delete(key)
    assert not (tmp_path / key).exists()


@pytest.mark.asyncio
async def test_list_prefix_returns_matching_keys(backend):
    keys = [
        "pipeline-1/stage-a/v1/artifact.txt",
        "pipeline-1/stage-a/v2/artifact.txt",
        "pipeline-1/stage-b/v1/artifact.txt",
        "pipeline-2/stage-a/v1/artifact.txt",
    ]
    for key in keys:
        await backend.write(key, b"data")

    results = await backend.list_prefix("pipeline-1/stage-a")
    assert sorted(results) == sorted([
        "pipeline-1/stage-a/v1/artifact.txt",
        "pipeline-1/stage-a/v2/artifact.txt",
    ])


@pytest.mark.asyncio
async def test_write_nested_key_creates_directories(backend, tmp_path):
    key = "a/b/c/d/e/deep.txt"
    await backend.write(key, b"deep content")
    assert (tmp_path / key).exists()
    result = await backend.read(key)
    assert result == b"deep content"


@pytest.mark.asyncio
async def test_read_nonexistent_raises_artifact_not_found(backend):
    with pytest.raises(ArtifactNotFoundError):
        await backend.read("no/such/key.txt")


@pytest.mark.asyncio
async def test_write_returns_local_url(backend):
    key = "pipeline-1/stage-a/v1/artifact.txt"
    url = await backend.write(key, b"data")
    assert url == f"local://{key}"


@pytest.mark.asyncio
async def test_delete_nonexistent_raises_artifact_not_found(backend):
    with pytest.raises(ArtifactNotFoundError):
        await backend.delete("no/such/key.txt")


@pytest.mark.asyncio
async def test_list_prefix_empty_when_no_match(backend):
    await backend.write("pipeline-1/stage-a/v1/artifact.txt", b"data")
    results = await backend.list_prefix("pipeline-99")
    assert results == []
