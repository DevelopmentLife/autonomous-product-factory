"""Global application state — backend + registry singletons.

Both are initialised during the FastAPI lifespan and accessed via the
getter functions below.  Tests can replace them via the setters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apf_artifact_store.backends.base import StorageBackend
    from apf_artifact_store.models import ArtifactRegistry

_backend: "StorageBackend | None" = None
_registry: "ArtifactRegistry | None" = None


def set_backend(backend: "StorageBackend") -> None:
    global _backend
    _backend = backend


def get_backend() -> "StorageBackend":
    if _backend is None:
        raise RuntimeError("Storage backend has not been initialised")
    return _backend


def set_registry(registry: "ArtifactRegistry") -> None:
    global _registry
    _registry = registry


def get_registry() -> "ArtifactRegistry":
    if _registry is None:
        raise RuntimeError("Artifact registry has not been initialised")
    return _registry
