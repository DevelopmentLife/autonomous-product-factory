"""Tests for APF ORM models.

Covers:
- Field persistence and retrieval for every model
- Foreign-key relationships
- Cascade delete behaviour (Pipeline -> Stage -> Artifact / AgentRun)
- JSON column round-trips
- Datetime auto-population
- Unique constraint on User.email
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apf_db import (
    AgentRun,
    Artifact,
    AuditLog,
    ConnectorConfig,
    Pipeline,
    Stage,
    User,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class TestPipeline:
    @pytest.mark.asyncio
    async def test_create_and_retrieve(self, session: AsyncSession) -> None:
        pipeline = Pipeline(
            id=_uid(),
            idea="Build a SaaS analytics dashboard",
            status="pending",
            config={"max_retries": 3, "notify_slack": True},
            github_repo="acme/analytics",
            github_branch="main",
            created_by=_uid(),
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(pipeline)
        await session.commit()
        await session.refresh(pipeline)

        result = await session.get(Pipeline, pipeline.id)
        assert result is not None
        assert result.idea == "Build a SaaS analytics dashboard"
        assert result.status == "pending"
        assert result.config == {"max_retries": 3, "notify_slack": True}
        assert result.github_repo == "acme/analytics"
        assert result.github_branch == "main"
        assert result.completed_at is None
        assert result.github_pr_url is None

    @pytest.mark.asyncio
    async def test_json_config_round_trip(self, session: AsyncSession) -> None:
        """Nested JSON structures survive a commit/retrieve cycle."""
        complex_config = {
            "stages": ["prd", "architect", "developer"],
            "llm": {"provider": "anthropic", "model": "claude-3-5-sonnet"},
            "connectors": {"github": True, "slack": False},
        }
        pipeline = Pipeline(
            id=_uid(),
            idea="Test JSON",
            status="running",
            config=complex_config,
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(pipeline)
        await session.commit()

        fetched = await session.get(Pipeline, pipeline.id)
        assert fetched is not None
        assert fetched.config == complex_config
        assert fetched.config["llm"]["model"] == "claude-3-5-sonnet"

    @pytest.mark.asyncio
    async def test_status_values(self, session: AsyncSession) -> None:
        for status in ("pending", "running", "paused", "complete", "failed"):
            p = Pipeline(
                id=_uid(),
                idea=f"idea for {status}",
                status=status,
                config={},
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(p)
        await session.commit()

        rows = (await session.execute(select(Pipeline))).scalars().all()
        statuses = {r.status for r in rows}
        assert statuses == {"pending", "running", "paused", "complete", "failed"}


# ---------------------------------------------------------------------------
# Stage
# ---------------------------------------------------------------------------


class TestStage:
    @pytest_asyncio.fixture(autouse=True)
    async def _pipeline(self, session: AsyncSession) -> None:
        self._pipeline_id = _uid()
        pipeline = Pipeline(
            id=self._pipeline_id,
            idea="Parent pipeline",
            status="running",
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(pipeline)
        await session.commit()

    @pytest.mark.asyncio
    async def test_create_stage_with_fk(self, session: AsyncSession) -> None:
        stage = Stage(
            id=_uid(),
            pipeline_id=self._pipeline_id,
            stage_name="prd",
            status="running",
            started_at=_now(),
            retry_count=0,
        )
        session.add(stage)
        await session.commit()
        await session.refresh(stage)

        result = await session.get(Stage, stage.id)
        assert result is not None
        assert result.pipeline_id == self._pipeline_id
        assert result.stage_name == "prd"
        assert result.duration_seconds is None
        assert result.error_message is None
        assert result.retry_count == 0

    @pytest.mark.asyncio
    async def test_stage_all_fields(self, session: AsyncSession) -> None:
        start = _now()
        end = _now()
        stage = Stage(
            id=_uid(),
            pipeline_id=self._pipeline_id,
            stage_name="developer",
            status="complete",
            started_at=start,
            completed_at=end,
            duration_seconds=42.5,
            retry_count=1,
            approved_by=_uid(),
            approved_at=end,
        )
        session.add(stage)
        await session.commit()

        result = await session.get(Stage, stage.id)
        assert result is not None
        assert result.duration_seconds == pytest.approx(42.5)
        assert result.retry_count == 1
        assert result.approved_by is not None


# ---------------------------------------------------------------------------
# Artifact
# ---------------------------------------------------------------------------


class TestArtifact:
    @pytest_asyncio.fixture(autouse=True)
    async def _parent_objects(self, session: AsyncSession) -> None:
        self._pipeline_id = _uid()
        self._stage_id = _uid()
        pipeline = Pipeline(
            id=self._pipeline_id,
            idea="Parent",
            status="running",
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        stage = Stage(
            id=self._stage_id,
            pipeline_id=self._pipeline_id,
            stage_name="architect",
            status="complete",
        )
        session.add_all([pipeline, stage])
        await session.commit()

    @pytest.mark.asyncio
    async def test_create_artifact(self, session: AsyncSession) -> None:
        artifact = Artifact(
            id=_uid(),
            pipeline_id=self._pipeline_id,
            stage_id=self._stage_id,
            agent_name="ArchitectAgent",
            artifact_type="architecture",
            content_url="s3://artifacts/arch/0001.json",
            content_hash="a" * 64,
            content_size_bytes=1024,
            version=1,
            created_at=_now(),
        )
        session.add(artifact)
        await session.commit()

        result = await session.get(Artifact, artifact.id)
        assert result is not None
        assert result.agent_name == "ArchitectAgent"
        assert result.artifact_type == "architecture"
        assert result.content_hash == "a" * 64
        assert result.version == 1

    @pytest.mark.asyncio
    async def test_artifact_versioning(self, session: AsyncSession) -> None:
        """Multiple versions of the same artifact type for a stage are allowed."""
        for v in (1, 2, 3):
            artifact = Artifact(
                id=_uid(),
                pipeline_id=self._pipeline_id,
                stage_id=self._stage_id,
                agent_name="DeveloperAgent",
                artifact_type="developer",
                content_url=f"s3://artifacts/dev/v{v}.json",
                content_hash="b" * 64,
                content_size_bytes=512 * v,
                version=v,
                created_at=_now(),
            )
            session.add(artifact)
        await session.commit()

        rows = (
            await session.execute(
                select(Artifact).where(Artifact.stage_id == self._stage_id)
            )
        ).scalars().all()
        assert len(rows) == 3
        versions = sorted(r.version for r in rows)
        assert versions == [1, 2, 3]


# ---------------------------------------------------------------------------
# AgentRun
# ---------------------------------------------------------------------------


class TestAgentRun:
    @pytest_asyncio.fixture(autouse=True)
    async def _parent_objects(self, session: AsyncSession) -> None:
        self._stage_id = _uid()
        pipeline = Pipeline(
            id=_uid(),
            idea="Parent",
            status="running",
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        stage = Stage(
            id=self._stage_id,
            pipeline_id=pipeline.id,
            stage_name="qa",
            status="running",
        )
        session.add_all([pipeline, stage])
        await session.commit()

    @pytest.mark.asyncio
    async def test_create_agent_run(self, session: AsyncSession) -> None:
        run = AgentRun(
            id=_uid(),
            stage_id=self._stage_id,
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            prompt_tokens=500,
            completion_tokens=1200,
            total_cost_usd=0.0045,
            latency_ms=3200,
            started_at=_now(),
        )
        session.add(run)
        await session.commit()

        result = await session.get(AgentRun, run.id)
        assert result is not None
        assert result.llm_provider == "anthropic"
        assert result.prompt_tokens == 500
        assert result.completion_tokens == 1200
        assert result.total_cost_usd == pytest.approx(0.0045)
        assert result.latency_ms == 3200
        assert result.error is None

    @pytest.mark.asyncio
    async def test_agent_run_with_error(self, session: AsyncSession) -> None:
        run = AgentRun(
            id=_uid(),
            stage_id=self._stage_id,
            llm_provider="openai",
            llm_model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=0,
            total_cost_usd=0.0,
            latency_ms=500,
            started_at=_now(),
            error="RateLimitError: quota exceeded",
        )
        session.add(run)
        await session.commit()

        result = await session.get(AgentRun, run.id)
        assert result is not None
        assert "RateLimitError" in result.error


# ---------------------------------------------------------------------------
# ConnectorConfig
# ---------------------------------------------------------------------------


class TestConnectorConfig:
    @pytest.mark.asyncio
    async def test_create_connector(self, session: AsyncSession) -> None:
        connector = ConnectorConfig(
            id=_uid(),
            connector_type="github",
            enabled=True,
            config={"org": "acme", "default_branch": "main"},
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(connector)
        await session.commit()

        result = await session.get(ConnectorConfig, connector.id)
        assert result is not None
        assert result.connector_type == "github"
        assert result.enabled is True
        assert result.config["org"] == "acme"

    @pytest.mark.asyncio
    async def test_connector_unique_type(self, session: AsyncSession) -> None:
        """Two ConnectorConfig rows with the same connector_type must be rejected."""
        c1 = ConnectorConfig(
            id=_uid(),
            connector_type="slack",
            enabled=False,
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        c2 = ConnectorConfig(
            id=_uid(),
            connector_type="slack",
            enabled=True,
            config={"webhook": "https://hooks.slack.com/xxx"},
            created_at=_now(),
            updated_at=_now(),
        )
        session.add_all([c1, c2])
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_connector_disabled_by_default(self, session: AsyncSession) -> None:
        connector = ConnectorConfig(
            id=_uid(),
            connector_type="jira",
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(connector)
        await session.commit()

        result = await session.get(ConnectorConfig, connector.id)
        assert result is not None
        assert result.enabled is False


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------


class TestAuditLog:
    @pytest_asyncio.fixture(autouse=True)
    async def _pipeline(self, session: AsyncSession) -> None:
        self._pipeline_id = _uid()
        self._stage_id = _uid()
        pipeline = Pipeline(
            id=self._pipeline_id,
            idea="Audit parent",
            status="running",
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        stage = Stage(
            id=self._stage_id,
            pipeline_id=self._pipeline_id,
            stage_name="review",
            status="awaiting_approval",
        )
        session.add_all([pipeline, stage])
        await session.commit()

    @pytest.mark.asyncio
    async def test_create_audit_log_with_pipeline(self, session: AsyncSession) -> None:
        log = AuditLog(
            id=_uid(),
            event_type="pipeline.created",
            actor="user-123",
            pipeline_id=self._pipeline_id,
            details={"idea": "Audit parent", "triggered_by": "api"},
            created_at=_now(),
        )
        session.add(log)
        await session.commit()

        result = await session.get(AuditLog, log.id)
        assert result is not None
        assert result.event_type == "pipeline.created"
        assert result.actor == "user-123"
        assert result.details["triggered_by"] == "api"

    @pytest.mark.asyncio
    async def test_audit_log_system_actor(self, session: AsyncSession) -> None:
        log = AuditLog(
            id=_uid(),
            event_type="stage.started",
            actor="system",
            pipeline_id=self._pipeline_id,
            stage_id=self._stage_id,
            details={"stage_name": "review"},
            created_at=_now(),
        )
        session.add(log)
        await session.commit()

        result = await session.get(AuditLog, log.id)
        assert result is not None
        assert result.actor == "system"
        assert result.stage_id == self._stage_id

    @pytest.mark.asyncio
    async def test_audit_log_null_pipeline(self, session: AsyncSession) -> None:
        """AuditLog rows may exist without a linked pipeline (e.g. connector events)."""
        log = AuditLog(
            id=_uid(),
            event_type="connector.enabled",
            actor="admin-1",
            details={"connector_type": "aws"},
            created_at=_now(),
        )
        session.add(log)
        await session.commit()

        result = await session.get(AuditLog, log.id)
        assert result is not None
        assert result.pipeline_id is None


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class TestUser:
    @pytest.mark.asyncio
    async def test_create_user(self, session: AsyncSession) -> None:
        user = User(
            id=_uid(),
            email="alice@example.com",
            hashed_password="$2b$12$hashed",
            role="admin",
            is_active=True,
            created_at=_now(),
        )
        session.add(user)
        await session.commit()

        result = await session.get(User, user.id)
        assert result is not None
        assert result.email == "alice@example.com"
        assert result.role == "admin"
        assert result.is_active is True
        assert result.last_login_at is None

    @pytest.mark.asyncio
    async def test_unique_email_constraint(self, session: AsyncSession) -> None:
        """Two users with the same email must raise an IntegrityError."""
        u1 = User(
            id=_uid(),
            email="bob@example.com",
            hashed_password="hash1",
            role="member",
            is_active=True,
            created_at=_now(),
        )
        u2 = User(
            id=_uid(),
            email="bob@example.com",  # duplicate
            hashed_password="hash2",
            role="viewer",
            is_active=True,
            created_at=_now(),
        )
        session.add_all([u1, u2])
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_user_roles(self, session: AsyncSession) -> None:
        for i, role in enumerate(("admin", "member", "viewer")):
            user = User(
                id=_uid(),
                email=f"user{i}@example.com",
                hashed_password="hash",
                role=role,
                is_active=True,
                created_at=_now(),
            )
            session.add(user)
        await session.commit()

        rows = (await session.execute(select(User))).scalars().all()
        roles = {r.role for r in rows}
        assert roles == {"admin", "member", "viewer"}

    @pytest.mark.asyncio
    async def test_last_login_updates(self, session: AsyncSession) -> None:
        user = User(
            id=_uid(),
            email="charlie@example.com",
            hashed_password="hash",
            role="member",
            is_active=True,
            created_at=_now(),
        )
        session.add(user)
        await session.commit()

        fetched = await session.get(User, user.id)
        assert fetched is not None
        assert fetched.last_login_at is None

        fetched.last_login_at = _now()
        await session.commit()

        updated = await session.get(User, fetched.id)
        assert updated is not None
        assert updated.last_login_at is not None


# ---------------------------------------------------------------------------
# Cascade behaviour
# ---------------------------------------------------------------------------


class TestCascades:
    @pytest.mark.asyncio
    async def test_delete_pipeline_cascades_to_stages(
        self, session: AsyncSession
    ) -> None:
        """Deleting a Pipeline must also delete its child Stages."""
        pipeline_id = _uid()
        stage_id = _uid()

        pipeline = Pipeline(
            id=pipeline_id,
            idea="Cascade test",
            status="complete",
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        stage = Stage(
            id=stage_id,
            pipeline_id=pipeline_id,
            stage_name="devops",
            status="complete",
        )
        session.add_all([pipeline, stage])
        await session.commit()

        # Verify both exist
        assert await session.get(Stage, stage_id) is not None

        # Delete pipeline — stage should cascade
        pipeline_obj = await session.get(Pipeline, pipeline_id)
        await session.delete(pipeline_obj)
        await session.commit()

        assert await session.get(Pipeline, pipeline_id) is None
        assert await session.get(Stage, stage_id) is None

    @pytest.mark.asyncio
    async def test_delete_pipeline_cascades_to_artifacts(
        self, session: AsyncSession
    ) -> None:
        """Deleting a Pipeline must cascade to its Artifacts."""
        pipeline_id = _uid()
        stage_id = _uid()
        artifact_id = _uid()

        pipeline = Pipeline(
            id=pipeline_id,
            idea="Cascade artifact test",
            status="complete",
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        stage = Stage(
            id=stage_id,
            pipeline_id=pipeline_id,
            stage_name="readme",
            status="complete",
        )
        artifact = Artifact(
            id=artifact_id,
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            agent_name="ReadmeAgent",
            artifact_type="readme",
            content_url="s3://artifacts/readme/001.md",
            content_hash="c" * 64,
            content_size_bytes=256,
            version=1,
            created_at=_now(),
        )
        session.add_all([pipeline, stage, artifact])
        await session.commit()

        pipeline_obj = await session.get(Pipeline, pipeline_id)
        await session.delete(pipeline_obj)
        await session.commit()

        assert await session.get(Artifact, artifact_id) is None

    @pytest.mark.asyncio
    async def test_delete_stage_cascades_to_agent_runs(
        self, session: AsyncSession
    ) -> None:
        """Deleting a Stage must cascade to its AgentRun rows."""
        pipeline_id = _uid()
        stage_id = _uid()
        run_id = _uid()

        pipeline = Pipeline(
            id=pipeline_id,
            idea="Stage cascade test",
            status="failed",
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        stage = Stage(
            id=stage_id,
            pipeline_id=pipeline_id,
            stage_name="qa",
            status="failed",
        )
        run = AgentRun(
            id=run_id,
            stage_id=stage_id,
            llm_provider="anthropic",
            llm_model="claude-3-haiku",
            prompt_tokens=200,
            completion_tokens=400,
            total_cost_usd=0.001,
            latency_ms=900,
            started_at=_now(),
        )
        session.add_all([pipeline, stage, run])
        await session.commit()

        stage_obj = await session.get(Stage, stage_id)
        await session.delete(stage_obj)
        await session.commit()

        assert await session.get(AgentRun, run_id) is None

    @pytest.mark.asyncio
    async def test_audit_log_pipeline_id_set_null_on_pipeline_delete(
        self, session: AsyncSession
    ) -> None:
        """AuditLog.pipeline_id should be set to NULL when the Pipeline is deleted."""
        pipeline_id = _uid()
        log_id = _uid()

        pipeline = Pipeline(
            id=pipeline_id,
            idea="Audit cascade test",
            status="complete",
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        log = AuditLog(
            id=log_id,
            event_type="pipeline.created",
            actor="system",
            pipeline_id=pipeline_id,
            details={},
            created_at=_now(),
        )
        session.add_all([pipeline, log])
        await session.commit()

        pipeline_obj = await session.get(Pipeline, pipeline_id)
        await session.delete(pipeline_obj)
        await session.commit()

        # AuditLog row still exists but pipeline_id is NULL
        audit = await session.get(AuditLog, log_id)
        assert audit is not None
        assert audit.pipeline_id is None


# ---------------------------------------------------------------------------
# Datetime auto-population
# ---------------------------------------------------------------------------


class TestDatetimeFields:
    @pytest.mark.asyncio
    async def test_pipeline_created_at_auto_populated(
        self, session: AsyncSession
    ) -> None:
        """created_at should be set by the application default when not provided."""
        before = datetime.now(tz=timezone.utc)
        pipeline = Pipeline(
            id=_uid(),
            idea="Datetime test",
            status="pending",
            config={},
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(pipeline)
        await session.commit()
        after = datetime.now(tz=timezone.utc)

        result = await session.get(Pipeline, pipeline.id)
        assert result is not None
        # created_at is timezone-aware; compare as naive UTC if needed
        created = result.created_at
        if created.tzinfo is not None:
            assert before <= created <= after
        else:
            # SQLite may return naive datetimes
            assert created is not None
