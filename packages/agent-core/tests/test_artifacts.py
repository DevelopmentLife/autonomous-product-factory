"""
Tests for apf_agent_core.artifacts — all 11 artifact classes.
"""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from apf_agent_core.artifacts import (
    ArtifactStatus,
    BaseArtifact,
    PRDArtifact,
    ArchitectureArtifact,
    MarketArtifact,
    UXArtifact,
    EngineeringArtifact,
    DeveloperArtifact,
    QAArtifact,
    RegressionArtifact,
    ReviewArtifact,
    DevOpsArtifact,
    ReadmeArtifact,
)


# ---------------------------------------------------------------------------
# ArtifactStatus enum
# ---------------------------------------------------------------------------

class TestArtifactStatus:
    def test_values(self):
        assert ArtifactStatus.PENDING == "pending"
        assert ArtifactStatus.IN_PROGRESS == "in_progress"
        assert ArtifactStatus.COMPLETE == "complete"
        assert ArtifactStatus.FAILED == "failed"

    def test_is_str_enum(self):
        assert isinstance(ArtifactStatus.COMPLETE, str)

    def test_all_four_members(self):
        members = {s.value for s in ArtifactStatus}
        assert members == {"pending", "in_progress", "complete", "failed"}


# ---------------------------------------------------------------------------
# BaseArtifact
# ---------------------------------------------------------------------------

class TestBaseArtifact:
    def test_cannot_instantiate_without_agent_name(self):
        """BaseArtifact.agent_name has no default — must be provided."""
        with pytest.raises(Exception):
            BaseArtifact()  # type: ignore[call-arg]

    def test_defaults(self):
        a = BaseArtifact(agent_name="test-agent")
        assert a.status == ArtifactStatus.PENDING
        assert a.raw_content == ""
        assert a.metadata == {}
        assert isinstance(a.artifact_id, str) and len(a.artifact_id) == 36  # UUID4
        assert isinstance(a.created_at, datetime)
        assert isinstance(a.updated_at, datetime)

    def test_unique_artifact_ids(self):
        a1 = BaseArtifact(agent_name="x")
        a2 = BaseArtifact(agent_name="x")
        assert a1.artifact_id != a2.artifact_id

    def test_model_dump(self):
        a = BaseArtifact(agent_name="test-agent", status=ArtifactStatus.COMPLETE)
        d = a.model_dump()
        assert d["agent_name"] == "test-agent"
        assert d["status"] == ArtifactStatus.COMPLETE

    def test_model_dump_json(self):
        a = BaseArtifact(agent_name="test-agent")
        raw = a.model_dump_json()
        data = json.loads(raw)
        assert data["agent_name"] == "test-agent"
        assert data["status"] == "pending"

    def test_model_validate_round_trip(self):
        a = BaseArtifact(agent_name="round-trip", status=ArtifactStatus.IN_PROGRESS)
        restored = BaseArtifact.model_validate(a.model_dump())
        assert restored.agent_name == a.agent_name
        assert restored.status == ArtifactStatus.IN_PROGRESS
        assert restored.artifact_id == a.artifact_id


# ---------------------------------------------------------------------------
# PRDArtifact
# ---------------------------------------------------------------------------

class TestPRDArtifact:
    def test_default_agent_name(self):
        a = PRDArtifact()
        assert a.agent_name == "prd-agent"

    def test_field_defaults(self):
        a = PRDArtifact()
        assert a.executive_summary == ""
        assert a.target_users == []
        assert a.core_features == []
        assert a.success_metrics == []
        assert a.out_of_scope == []

    def test_populate_fields(self):
        a = PRDArtifact(
            executive_summary="Build X",
            target_users=["devs", "designers"],
            core_features=["auth", "billing"],
            success_metrics=["100 users in month 1"],
            out_of_scope=["mobile"],
        )
        assert a.executive_summary == "Build X"
        assert "devs" in a.target_users
        assert "auth" in a.core_features

    def test_serialization(self):
        a = PRDArtifact(core_features=["feat1"])
        d = a.model_dump()
        assert d["core_features"] == ["feat1"]
        assert d["agent_name"] == "prd-agent"

    def test_deserialization(self):
        d = {
            "agent_name": "prd-agent",
            "executive_summary": "Test",
            "target_users": ["user1"],
            "core_features": [],
            "success_metrics": [],
            "out_of_scope": [],
        }
        a = PRDArtifact.model_validate(d)
        assert a.executive_summary == "Test"
        assert a.target_users == ["user1"]


# ---------------------------------------------------------------------------
# ArchitectureArtifact
# ---------------------------------------------------------------------------

class TestArchitectureArtifact:
    def test_default_agent_name(self):
        assert ArchitectureArtifact().agent_name == "architect-agent"

    def test_field_defaults(self):
        a = ArchitectureArtifact()
        assert a.services == []
        assert a.tech_stack == {}
        assert a.architecture_diagram == ""

    def test_populate(self):
        a = ArchitectureArtifact(
            services=["api", "worker"],
            tech_stack={"backend": "FastAPI", "db": "PostgreSQL"},
            architecture_diagram="API --> Worker",
        )
        assert "api" in a.services
        assert a.tech_stack["backend"] == "FastAPI"

    def test_round_trip(self):
        a = ArchitectureArtifact(services=["svc1"])
        restored = ArchitectureArtifact.model_validate(a.model_dump())
        assert restored.services == ["svc1"]


# ---------------------------------------------------------------------------
# MarketArtifact
# ---------------------------------------------------------------------------

class TestMarketArtifact:
    def test_default_agent_name(self):
        assert MarketArtifact().agent_name == "market-agent"

    def test_field_defaults(self):
        a = MarketArtifact()
        assert a.market_size == ""
        assert a.competitors == []
        assert a.differentiators == []
        assert a.recommended_features == []

    def test_competitors_structure(self):
        a = MarketArtifact(
            competitors=[{"name": "Acme", "strengths": "Big brand", "weaknesses": "Slow"}]
        )
        assert a.competitors[0]["name"] == "Acme"

    def test_round_trip(self):
        a = MarketArtifact(market_size="$1B TAM", differentiators=["speed"])
        r = MarketArtifact.model_validate(a.model_dump())
        assert r.market_size == "$1B TAM"


# ---------------------------------------------------------------------------
# UXArtifact
# ---------------------------------------------------------------------------

class TestUXArtifact:
    def test_default_agent_name(self):
        assert UXArtifact().agent_name == "ux-agent"

    def test_field_defaults(self):
        a = UXArtifact()
        assert a.cli_commands == []
        assert a.dashboard_screens == []
        assert a.user_flows == []

    def test_populate(self):
        a = UXArtifact(
            cli_commands=["apf init", "apf run"],
            dashboard_screens=["Pipeline Status", "Artifact Viewer"],
        )
        assert "apf init" in a.cli_commands

    def test_round_trip(self):
        a = UXArtifact(user_flows=["onboarding"])
        r = UXArtifact.model_validate(a.model_dump())
        assert r.user_flows == ["onboarding"]


# ---------------------------------------------------------------------------
# EngineeringArtifact
# ---------------------------------------------------------------------------

class TestEngineeringArtifact:
    def test_default_agent_name(self):
        assert EngineeringArtifact().agent_name == "engineering-agent"

    def test_field_defaults(self):
        a = EngineeringArtifact()
        assert a.tech_stack == {}
        assert a.phases == []
        assert a.milestones == []

    def test_phases_structure(self):
        a = EngineeringArtifact(
            phases=[{"name": "Phase 1", "duration_weeks": 2, "tasks": ["setup CI"]}]
        )
        assert a.phases[0]["name"] == "Phase 1"

    def test_round_trip(self):
        a = EngineeringArtifact(milestones=["MVP"])
        r = EngineeringArtifact.model_validate(a.model_dump())
        assert r.milestones == ["MVP"]


# ---------------------------------------------------------------------------
# DeveloperArtifact
# ---------------------------------------------------------------------------

class TestDeveloperArtifact:
    def test_default_agent_name(self):
        assert DeveloperArtifact().agent_name == "developer-agent"

    def test_field_defaults(self):
        a = DeveloperArtifact()
        assert a.files_created == []
        assert a.files_modified == []
        assert a.tests_written == []
        assert a.coverage_pct == 0.0
        assert a.github_branch == ""
        assert a.github_pr_url == ""

    def test_populate(self):
        a = DeveloperArtifact(
            files_created=["src/main.py"],
            coverage_pct=82.5,
            github_branch="feature/apf-core",
            github_pr_url="https://github.com/org/repo/pull/1",
        )
        assert a.coverage_pct == 82.5
        assert "src/main.py" in a.files_created

    def test_round_trip(self):
        a = DeveloperArtifact(coverage_pct=75.0, github_branch="main")
        r = DeveloperArtifact.model_validate(a.model_dump())
        assert r.coverage_pct == 75.0


# ---------------------------------------------------------------------------
# QAArtifact
# ---------------------------------------------------------------------------

class TestQAArtifact:
    def test_default_agent_name(self):
        assert QAArtifact().agent_name == "qa-agent"

    def test_field_defaults(self):
        a = QAArtifact()
        assert a.bugs == []
        assert a.test_results == {}
        assert a.coverage_pct == 0.0
        assert a.critical_bug_count == 0
        assert a.high_bug_count == 0
        assert a.passed is False

    def test_populate(self):
        a = QAArtifact(
            bugs=[{"id": "BUG-1", "severity": "high", "description": "Crash on startup"}],
            test_results={"total": 50, "passed": 48, "failed": 2},
            coverage_pct=88.0,
            critical_bug_count=0,
            high_bug_count=1,
            passed=False,
        )
        assert a.high_bug_count == 1
        assert a.coverage_pct == 88.0
        assert a.passed is False

    def test_round_trip(self):
        a = QAArtifact(passed=True, coverage_pct=95.0)
        r = QAArtifact.model_validate(a.model_dump())
        assert r.passed is True


# ---------------------------------------------------------------------------
# RegressionArtifact
# ---------------------------------------------------------------------------

class TestRegressionArtifact:
    def test_default_agent_name(self):
        assert RegressionArtifact().agent_name == "regression-agent"

    def test_field_defaults(self):
        a = RegressionArtifact()
        assert a.bugs_fixed == []
        assert a.files_modified == []

    def test_populate(self):
        a = RegressionArtifact(
            bugs_fixed=["BUG-1: fixed null pointer"],
            files_modified=["src/main.py"],
        )
        assert "BUG-1: fixed null pointer" in a.bugs_fixed

    def test_round_trip(self):
        a = RegressionArtifact(bugs_fixed=["BUG-2"])
        r = RegressionArtifact.model_validate(a.model_dump())
        assert r.bugs_fixed == ["BUG-2"]


# ---------------------------------------------------------------------------
# ReviewArtifact
# ---------------------------------------------------------------------------

class TestReviewArtifact:
    def test_default_agent_name(self):
        assert ReviewArtifact().agent_name == "review-agent"

    def test_field_defaults(self):
        a = ReviewArtifact()
        assert a.approved is False
        assert a.comments == []
        assert a.security_issues == []
        assert a.coverage_pct == 0.0

    def test_populate(self):
        a = ReviewArtifact(
            approved=True,
            comments=[{"file": "main.py", "line": 10, "comment": "Use constant"}],
            security_issues=[],
            coverage_pct=91.0,
        )
        assert a.approved is True
        assert len(a.comments) == 1

    def test_round_trip(self):
        a = ReviewArtifact(approved=True, coverage_pct=90.0)
        r = ReviewArtifact.model_validate(a.model_dump())
        assert r.approved is True


# ---------------------------------------------------------------------------
# DevOpsArtifact
# ---------------------------------------------------------------------------

class TestDevOpsArtifact:
    def test_default_agent_name(self):
        assert DevOpsArtifact().agent_name == "devops-agent"

    def test_field_defaults(self):
        a = DevOpsArtifact()
        assert a.deployment_url == ""
        assert a.pipeline_url == ""
        assert a.environment == ""

    def test_populate(self):
        a = DevOpsArtifact(
            deployment_url="https://app.example.com",
            pipeline_url="https://ci.example.com/pipelines/1",
            environment="production",
        )
        assert a.environment == "production"

    def test_round_trip(self):
        a = DevOpsArtifact(environment="staging")
        r = DevOpsArtifact.model_validate(a.model_dump())
        assert r.environment == "staging"


# ---------------------------------------------------------------------------
# ReadmeArtifact
# ---------------------------------------------------------------------------

class TestReadmeArtifact:
    def test_default_agent_name(self):
        assert ReadmeArtifact().agent_name == "readme-agent"

    def test_field_defaults(self):
        a = ReadmeArtifact()
        assert a.content == ""

    def test_populate(self):
        a = ReadmeArtifact(content="# My Project\n\nAwesome project.")
        assert "# My Project" in a.content

    def test_round_trip(self):
        a = ReadmeArtifact(content="# README")
        r = ReadmeArtifact.model_validate(a.model_dump())
        assert r.content == "# README"


# ---------------------------------------------------------------------------
# Cross-cutting: metadata dict is independent per instance
# ---------------------------------------------------------------------------

class TestArtifactIsolation:
    def test_metadata_not_shared(self):
        a1 = PRDArtifact()
        a2 = PRDArtifact()
        a1.metadata["key"] = "value"
        assert "key" not in a2.metadata

    def test_list_fields_not_shared(self):
        a1 = PRDArtifact()
        a2 = PRDArtifact()
        a1.core_features.append("feat")
        assert "feat" not in a2.core_features
