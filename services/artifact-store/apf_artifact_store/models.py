from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4
import hashlib


class ArtifactRecord(BaseModel):
    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    pipeline_id: str
    stage_name: str
    agent_name: str
    content_type: str = 'text/plain'
    content_hash: str
    size_bytes: int
    version: int = 1
    storage_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class ArtifactNotFoundError(Exception):
    pass
