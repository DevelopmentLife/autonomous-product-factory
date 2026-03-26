"""
Tests for apf_agent_core.validators — validate_artifact and ArtifactValidationError.
"""
from __future__ import annotations

import pytest

from apf_agent_core.artifacts import (
    ArtifactStatus,
    PRDArtifact,
    QAArtifact,
    DeveloperArtifact,
    ArchitectureArtifact,
    ReadmeArtifact,
)
from apf_agent_core.validators import ArtifactValidationError, validate_artifact


# ---------------------------------------------------------------------------
# ArtifactValidationError
# ---------------------------------------------------------------------------

class TestArtifactValidationError:
    def test_stores_agent_name(self):
        err = ArtifactValidationError("prd-agent", ["missing field"])
        assert err.agent_name == "prd-agent"

    def test_stores_errors_list(self):
        errors = ["error 1", "error 2"]
        err = ArtifactValidationError("prd-agent", errors)
        assert err.errors == errors

    def test_is_exception(self):
        err = ArtifactValidationError("prd-agent", ["oops"])
        assert isinstance(err, Exception)

    def test_str_representation_includes_agent_and_errors(self):
        err = ArtifactValidationError("prd-agent", ["field X required"])
        msg = str(err)
        assert "prd-agent" in msg
        assert "field X required" in msg


# ---------------------------------------------------------------------------
# validate_artifact — passing cases
# ---------------------------------------------------------------------------

class TestValidateArtifactPasses:
    def test_valid_prd_artifact(self):
        artifact = PRDArtifact(
            status=ArtifactStatus.COMPLETE,
            executive_summary="Test summary",
            target_users=["devs"],
            core_features=["auth"],
        )
        # Should not raise
        validate_artifact(artifact, PRDArtifact)

    def test_valid_prd_artifact_pending_status(self):
        """PENDING is a valid status — only FAILED triggers an error."""
        artifact = PRDArtifact(status=ArtifactStatus.PENDING)
        validate_artifact(artifact, PRDArtifact)

    def test_valid_prd_artifact_in_progress(self):
        artifact = PRDArtifact(status=ArtifactStatus.IN_PROGRESS)
        validate_artifact(artifact, PRDArtifact)

    def test_valid_qa_artifact(self):
        artifact = QAArtifact(
            status=ArtifactStatus.COMPLETE,
            coverage_pct=85.0,
            passed=True,
        )
        validate_artifact(artifact, QAArtifact)

    def test_valid_developer_artifact(self):
        artifact = DeveloperArtifact(
            status=ArtifactStatus.COMPLETE,
            files_created=["src/main.py"],
            coverage_pct=90.0,
            github_branch="feature/x",
        )
        validate_artifact(artifact, DeveloperArtifact)

    def test_valid_architecture_artifact(self):
        artifact = ArchitectureArtifact(
            status=ArtifactStatus.COMPLETE,
            services=["api", "worker"],
            tech_stack={"backend": "FastAPI"},
        )
        validate_artifact(artifact, ArchitectureArtifact)

    def test_minimal_artifact_all_defaults(self):
        """Artifact with all defaults (except agent_name) should pass."""
        artifact = PRDArtifact()
        validate_artifact(artifact, PRDArtifact)

    def test_readme_artifact(self):
        artifact = ReadmeArtifact(
            status=ArtifactStatus.COMPLETE,
            content="# README\n\nHello world.",
        )
        validate_artifact(artifact, ReadmeArtifact)


# ---------------------------------------------------------------------------
# validate_artifact — failing cases
# ---------------------------------------------------------------------------

class TestValidateArtifactFails:
    def test_wrong_type_raises(self):
        """Passing a QAArtifact where PRDArtifact is expected should fail."""
        artifact = QAArtifact(status=ArtifactStatus.COMPLETE)
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact(artifact, PRDArtifact)
        assert exc_info.value.agent_name == "qa-agent"
        assert any("Expected" in e for e in exc_info.value.errors)

    def test_failed_status_raises(self):
        artifact = PRDArtifact(status=ArtifactStatus.FAILED)
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact(artifact, PRDArtifact)
        assert any("FAILED" in e for e in exc_info.value.errors)

    def test_failed_qa_artifact_raises(self):
        artifact = QAArtifact(status=ArtifactStatus.FAILED)
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact(artifact, QAArtifact)
        assert exc_info.value.agent_name == "qa-agent"

    def test_error_contains_agent_name(self):
        artifact = PRDArtifact(status=ArtifactStatus.FAILED)
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact(artifact, PRDArtifact)
        assert exc_info.value.agent_name == "prd-agent"

    def test_wrong_type_errors_list_not_empty(self):
        artifact = DeveloperArtifact(status=ArtifactStatus.COMPLETE)
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact(artifact, QAArtifact)
        assert len(exc_info.value.errors) > 0

    def test_developer_artifact_against_architecture_schema(self):
        artifact = DeveloperArtifact(status=ArtifactStatus.COMPLETE)
        with pytest.raises(ArtifactValidationError):
            validate_artifact(artifact, ArchitectureArtifact)


# ---------------------------------------------------------------------------
# validate_artifact — edge cases
# ---------------------------------------------------------------------------

class TestValidateArtifactEdgeCases:
    def test_subclass_passes_parent_schema(self):
        """A concrete artifact should also pass validation against its own class."""
        artifact = PRDArtifact(
            status=ArtifactStatus.COMPLETE,
            core_features=["feat1", "feat2"],
        )
        validate_artifact(artifact, PRDArtifact)  # should not raise

    def test_large_metadata_dict_passes(self):
        artifact = PRDArtifact(
            status=ArtifactStatus.COMPLETE,
            metadata={f"key_{i}": f"value_{i}" for i in range(100)},
        )
        validate_artifact(artifact, PRDArtifact)

    def test_coverage_pct_boundary_zero(self):
        artifact = DeveloperArtifact(status=ArtifactStatus.COMPLETE, coverage_pct=0.0)
        validate_artifact(artifact, DeveloperArtifact)

    def test_coverage_pct_boundary_hundred(self):
        artifact = DeveloperArtifact(status=ArtifactStatus.COMPLETE, coverage_pct=100.0)
        validate_artifact(artifact, DeveloperArtifact)
