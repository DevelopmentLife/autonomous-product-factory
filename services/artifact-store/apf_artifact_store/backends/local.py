"""Local filesystem storage backend using aiofiles."""

from __future__ import annotations

import os
from pathlib import Path

import aiofiles
import aiofiles.os

from apf_artifact_store.models import ArtifactNotFoundError


class LocalFileSystemBackend:
    """Store artifacts on the local filesystem.

    Key format expected by callers::

        {pipeline_id}/{stage_name}/v{version}/{filename}

    The backend is content-type-agnostic; it stores raw bytes and the caller
    is responsible for the key structure.
    """

    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path)

    def _full_path(self, key: str) -> Path:
        # Prevent path traversal
        resolved = (self._base / key).resolve()
        if not str(resolved).startswith(str(self._base.resolve())):
            raise ValueError(f"Key {key!r} escapes the storage root")
        return resolved

    async def write(self, key: str, content: bytes, content_type: str = "text/plain") -> str:
        """Write *content* to *key* and return ``local://{key}``."""
        path = self._full_path(key)
        await aiofiles.os.makedirs(str(path.parent), exist_ok=True)
        async with aiofiles.open(path, "wb") as fh:
            await fh.write(content)
        return f"local://{key}"

    async def read(self, key: str) -> bytes:
        """Read and return the content stored at *key*."""
        path = self._full_path(key)
        if not path.exists():
            raise ArtifactNotFoundError(f"Artifact not found: {key!r}")
        async with aiofiles.open(path, "rb") as fh:
            return await fh.read()

    async def exists(self, key: str) -> bool:
        path = self._full_path(key)
        return path.exists()

    async def delete(self, key: str) -> None:
        path = self._full_path(key)
        if not path.exists():
            raise ArtifactNotFoundError(f"Artifact not found: {key!r}")
        await aiofiles.os.remove(str(path))

    async def list_prefix(self, prefix: str) -> list[str]:
        """Return all keys whose path starts with *prefix*."""
        search_root = self._full_path(prefix) if prefix else self._base
        # If the prefix points to an existing directory, walk it.
        # Otherwise, treat the last component as a filename prefix inside the
        # parent directory.
        if search_root.is_dir():
            base_dir = search_root
            file_prefix = ""
        else:
            base_dir = search_root.parent
            file_prefix = search_root.name

        keys: list[str] = []
        if not base_dir.exists():
            return keys

        for dirpath, _dirnames, filenames in os.walk(str(base_dir)):
            for filename in filenames:
                if file_prefix and not filename.startswith(file_prefix):
                    continue
                full = Path(dirpath) / filename
                # Return keys relative to storage root
                rel = full.relative_to(self._base)
                keys.append(str(rel).replace(os.sep, "/"))
        return keys

    async def check_health(self) -> bool:
        try:
            self._base.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False
