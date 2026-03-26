"""Unit tests for the S3Backend using moto mocks."""

from __future__ import annotations

import boto3
import pytest
import pytest_asyncio

from apf_artifact_store.backends.s3 import S3Backend
from apf_artifact_store.models import ArtifactNotFoundError

BUCKET = "test-artifacts"
REGION = "us-east-1"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Ensure boto3 never touches real AWS credentials."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


@pytest_asyncio.fixture
async def s3_backend():
    """Create a moto-mocked S3 bucket and return an S3Backend pointed at it."""
    from moto import mock_aws

    with mock_aws():
        # Create the bucket before the backend so head_bucket works
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket=BUCKET)

        backend = S3Backend(
            bucket=BUCKET,
            region_name=REGION,
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        yield backend


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_uploads_to_s3(s3_backend):
    key = "pipeline-1/stage-a/v1/artifact.txt"
    url = await s3_backend.write(key, b"hello s3", content_type="text/plain")
    assert url == f"s3://{BUCKET}/{key}"
    assert await s3_backend.exists(key) is True


@pytest.mark.asyncio
async def test_read_downloads_from_s3(s3_backend):
    key = "pipeline-1/stage-a/v1/artifact.txt"
    content = b"s3 content"
    await s3_backend.write(key, content)
    result = await s3_backend.read(key)
    assert result == content


@pytest.mark.asyncio
async def test_read_missing_key_raises_error(s3_backend):
    with pytest.raises(ArtifactNotFoundError):
        await s3_backend.read("no/such/key.txt")


@pytest.mark.asyncio
async def test_delete_removes_object(s3_backend):
    key = "pipeline-1/stage-a/v1/artifact.txt"
    await s3_backend.write(key, b"data")
    await s3_backend.delete(key)
    assert await s3_backend.exists(key) is False


@pytest.mark.asyncio
async def test_list_prefix_returns_objects(s3_backend):
    keys = [
        "pipeline-1/stage-a/v1/artifact.txt",
        "pipeline-1/stage-a/v2/artifact.txt",
        "pipeline-1/stage-b/v1/artifact.txt",
        "pipeline-2/stage-a/v1/artifact.txt",
    ]
    for key in keys:
        await s3_backend.write(key, b"data")

    results = await s3_backend.list_prefix("pipeline-1/stage-a")
    assert sorted(results) == sorted([
        "pipeline-1/stage-a/v1/artifact.txt",
        "pipeline-1/stage-a/v2/artifact.txt",
    ])


@pytest.mark.asyncio
async def test_delete_nonexistent_raises_error(s3_backend):
    with pytest.raises(ArtifactNotFoundError):
        await s3_backend.delete("no/such/key.txt")


@pytest.mark.asyncio
async def test_exists_false_before_write(s3_backend):
    assert await s3_backend.exists("not/there.txt") is False


@pytest.mark.asyncio
async def test_health_check_returns_true(s3_backend):
    assert await s3_backend.check_health() is True
