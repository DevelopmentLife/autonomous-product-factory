from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from .artifacts import BaseArtifact, ArtifactStatus


class ArtifactValidationError(Exception):
    """Raised when an artifact fails semantic or schema validation."""

    def __init__(self, agent_name: str, errors: list[str]) -> None:
        self.agent_name = agent_name
        self.errors = errors
        super().__init__(
            f"Artifact from '{agent_name}' failed validation: {'; '.join(errors)}"
        )


def validate_artifact(artifact: BaseArtifact, schema_class: type[BaseArtifact]) -> None:
    """
    Validate that *artifact* conforms to *schema_class*.

    Checks performed:
    1. ``isinstance`` — artifact must be an instance of schema_class.
    2. Round-trip Pydantic re-validation via ``schema_class.model_validate``.
    3. Status must not be FAILED.

    Raises ``ArtifactValidationError`` on any failure.
    """
    errors: list[str] = []

    # 1. Type check
    if not isinstance(artifact, schema_class):
        errors.append(
            f"Expected instance of {schema_class.__name__}, "
            f"got {type(artifact).__name__}"
        )
        # Cannot proceed with further checks if the type is wrong
        raise ArtifactValidationError(
            getattr(artifact, "agent_name", "unknown"), errors
        )

    # 2. Pydantic re-validation (catches any field-level issues)
    try:
        schema_class.model_validate(artifact.model_dump())
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(l) for l in err["loc"])
            errors.append(f"{loc}: {err['msg']}")

    # 3. Status check
    if artifact.status == ArtifactStatus.FAILED:
        errors.append("artifact status is FAILED")

    if errors:
        raise ArtifactValidationError(artifact.agent_name, errors)
