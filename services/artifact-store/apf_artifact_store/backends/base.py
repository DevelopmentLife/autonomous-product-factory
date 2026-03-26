"""Abstract storage backend protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    async def write(self, key: str, content: bytes, content_type: str = "text/plain") -> str:
        """Write content and return the URL/key."""
        ...

    async def read(self, key: str) -> bytes:
        """Read content by key."""
        ...

    async def exists(self, key: str) -> bool:
        """Return True if the key exists in storage."""
        ...

    async def delete(self, key: str) -> None:
        """Delete the object at key."""
        ...

    async def list_prefix(self, prefix: str) -> list[str]:
        """List all keys with the given prefix."""
        ...

    async def check_health(self) -> bool:
        """Return True if the backend is reachable."""
        ...
