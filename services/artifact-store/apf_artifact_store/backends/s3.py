"""AWS S3 / MinIO storage backend."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import ClientError

from apf_artifact_store.models import ArtifactNotFoundError


class S3Backend:
    """Store artifacts in an S3-compatible object store.

    Supports AWS S3 and MinIO (via ``endpoint_url``).
    """

    def __init__(
        self,
        bucket: str,
        region_name: str = "us-east-1",
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ) -> None:
        self._bucket = bucket
        kwargs: dict[str, Any] = {"region_name": region_name}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if aws_access_key_id:
            kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            kwargs["aws_secret_access_key"] = aws_secret_access_key

        self._client = boto3.client("s3", **kwargs)

    # ------------------------------------------------------------------
    # StorageBackend protocol implementation
    # ------------------------------------------------------------------

    async def write(self, key: str, content: bytes, content_type: str = "text/plain") -> str:
        """Upload *content* to S3 and return ``s3://{bucket}/{key}``."""
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return f"s3://{self._bucket}/{key}"

    async def read(self, key: str) -> bytes:
        """Download and return the object at *key*."""
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code in ("NoSuchKey", "404"):
                raise ArtifactNotFoundError(f"Artifact not found: {key!r}") from exc
            raise

    async def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise

    async def delete(self, key: str) -> None:
        if not await self.exists(key):
            raise ArtifactNotFoundError(f"Artifact not found: {key!r}")
        self._client.delete_object(Bucket=self._bucket, Key=key)

    async def list_prefix(self, prefix: str) -> list[str]:
        """List all object keys with the given prefix."""
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    async def check_health(self) -> bool:
        try:
            self._client.head_bucket(Bucket=self._bucket)
            return True
        except ClientError:
            return False
