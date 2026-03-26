import asyncio, json, os
from pathlib import Path
from datetime import datetime
from .models import ArtifactRecord, compute_hash


class ArtifactNotFoundError(KeyError):
    pass


class ArtifactStore:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self._records: dict[str, ArtifactRecord] = {}
        self._lock = asyncio.Lock()

    async def initialize(self):
        self.base_path.mkdir(parents=True, exist_ok=True)
        index_path = self.base_path / '_index.json'
        if index_path.exists():
            try:
                data = json.loads(index_path.read_text())
                self._records = {k: ArtifactRecord(**v) for k, v in data.items()}
            except Exception:
                self._records = {}

    async def _save_index(self):
        index_path = self.base_path / '_index.json'
        index_path.write_text(
            json.dumps({k: v.model_dump(mode='json') for k, v in self._records.items()}, default=str)
        )

    def _next_version(self, pipeline_id: str, stage_name: str) -> int:
        existing = [r for r in self._records.values()
                    if r.pipeline_id == pipeline_id and r.stage_name == stage_name]
        return len(existing) + 1

    async def write(self, pipeline_id: str, stage_name: str, agent_name: str,
                    content: bytes, content_type: str = 'text/plain') -> ArtifactRecord:
        async with self._lock:
            version = self._next_version(pipeline_id, stage_name)
            content_hash = compute_hash(content)
            storage_key = f'{pipeline_id}/{stage_name}/v{version}/artifact'
            file_path = self.base_path / storage_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
            record = ArtifactRecord(
                pipeline_id=pipeline_id, stage_name=stage_name, agent_name=agent_name,
                content_type=content_type, content_hash=content_hash,
                size_bytes=len(content), version=version, storage_key=storage_key,
            )
            self._records[record.artifact_id] = record
            await self._save_index()
            return record

    async def read(self, artifact_id: str) -> bytes:
        record = self._records.get(artifact_id)
        if not record:
            raise ArtifactNotFoundError(f'Artifact {artifact_id} not found')
        file_path = self.base_path / record.storage_key
        if not file_path.exists():
            raise ArtifactNotFoundError(f'Artifact file missing: {record.storage_key}')
        return file_path.read_bytes()

    def get_record(self, artifact_id: str) -> ArtifactRecord | None:
        return self._records.get(artifact_id)

    def list_pipeline(self, pipeline_id: str) -> list[ArtifactRecord]:
        return [r for r in self._records.values() if r.pipeline_id == pipeline_id]

    def get_latest(self, pipeline_id: str, stage_name: str) -> ArtifactRecord | None:
        matches = [r for r in self._records.values()
                   if r.pipeline_id == pipeline_id and r.stage_name == stage_name]
        return max(matches, key=lambda r: r.version, default=None)

    def get_versions(self, pipeline_id: str, stage_name: str) -> list[ArtifactRecord]:
        matches = [r for r in self._records.values()
                   if r.pipeline_id == pipeline_id and r.stage_name == stage_name]
        return sorted(matches, key=lambda r: r.version)

    async def delete(self, artifact_id: str) -> None:
        async with self._lock:
            record = self._records.pop(artifact_id, None)
            if record:
                fp = self.base_path / record.storage_key
                if fp.exists():
                    fp.unlink()
                await self._save_index()
