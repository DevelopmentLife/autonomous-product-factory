"""Initial schema — create all APF tables.

Revision ID: 0001
Revises:
Create Date: 2026-03-23 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # pipelines
    # ------------------------------------------------------------------
    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("idea", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("current_stage", sa.String(64), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("github_repo", sa.String(255), nullable=True),
        sa.Column("github_branch", sa.String(255), nullable=True),
        sa.Column("github_pr_url", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
    )
    op.create_index("ix_pipelines_status", "pipelines", ["status"])
    op.create_index("ix_pipelines_created_by", "pipelines", ["created_by"])
    op.create_index(
        "ix_pipelines_status_created_at", "pipelines", ["status", "created_at"]
    )
    op.create_index(
        "ix_pipelines_created_by_status", "pipelines", ["created_by", "status"]
    )

    # ------------------------------------------------------------------
    # stages
    # ------------------------------------------------------------------
    op.create_table(
        "stages",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "pipeline_id",
            sa.String(36),
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage_name", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_stages_pipeline_id", "stages", ["pipeline_id"])
    op.create_index("ix_stages_status", "stages", ["status"])
    op.create_index(
        "ix_stages_pipeline_id_stage_name", "stages", ["pipeline_id", "stage_name"]
    )
    op.create_index(
        "ix_stages_pipeline_id_status", "stages", ["pipeline_id", "status"]
    )

    # ------------------------------------------------------------------
    # artifacts
    # ------------------------------------------------------------------
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "pipeline_id",
            sa.String(36),
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stage_id",
            sa.String(36),
            sa.ForeignKey("stages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(128), nullable=False),
        sa.Column("artifact_type", sa.String(64), nullable=False),
        sa.Column("content_url", sa.String(1024), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content_size_bytes", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_artifacts_pipeline_id", "artifacts", ["pipeline_id"])
    op.create_index("ix_artifacts_stage_id", "artifacts", ["stage_id"])
    op.create_index("ix_artifacts_artifact_type", "artifacts", ["artifact_type"])
    op.create_index(
        "ix_artifacts_pipeline_id_artifact_type",
        "artifacts",
        ["pipeline_id", "artifact_type"],
    )
    op.create_index(
        "ix_artifacts_stage_id_version", "artifacts", ["stage_id", "version"]
    )

    # ------------------------------------------------------------------
    # agent_runs
    # ------------------------------------------------------------------
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "stage_id",
            sa.String(36),
            sa.ForeignKey("stages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("llm_provider", sa.String(64), nullable=False),
        sa.Column("llm_model", sa.String(128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_cost_usd", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_agent_runs_stage_id", "agent_runs", ["stage_id"])
    op.create_index(
        "ix_agent_runs_stage_id_started_at", "agent_runs", ["stage_id", "started_at"]
    )

    # ------------------------------------------------------------------
    # connector_configs
    # ------------------------------------------------------------------
    op.create_table(
        "connector_configs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("connector_type", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_connector_configs_connector_type",
        "connector_configs",
        ["connector_type"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # audit_log
    # ------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(36), nullable=False),
        sa.Column(
            "pipeline_id",
            sa.String(36),
            sa.ForeignKey("pipelines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "stage_id",
            sa.String(36),
            sa.ForeignKey("stages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])
    op.create_index("ix_audit_log_actor", "audit_log", ["actor"])
    op.create_index("ix_audit_log_pipeline_id", "audit_log", ["pipeline_id"])
    op.create_index("ix_audit_log_stage_id", "audit_log", ["stage_id"])
    op.create_index(
        "ix_audit_log_pipeline_id_created_at",
        "audit_log",
        ["pipeline_id", "created_at"],
    )
    op.create_index(
        "ix_audit_log_actor_event_type", "audit_log", ["actor", "event_type"]
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("audit_log")
    op.drop_table("connector_configs")
    op.drop_table("agent_runs")
    op.drop_table("artifacts")
    op.drop_table("stages")
    op.drop_table("pipelines")
    op.drop_table("users")
