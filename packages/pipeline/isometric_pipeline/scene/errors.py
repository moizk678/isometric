"""Issue codes and the exception raised when a scene violates the contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class IssueCode(StrEnum):
    # Structure and version
    SCHEMA_INVALID = "SCHEMA_INVALID"
    VERSION_UNSUPPORTED = "VERSION_UNSUPPORTED"
    # Numbers and coordinates
    NON_FINITE_NUMBER = "NON_FINITE_NUMBER"
    COORDINATE_OUT_OF_BOUNDS = "COORDINATE_OUT_OF_BOUNDS"
    # Transforms
    TRANSFORM_SINGULAR = "TRANSFORM_SINGULAR"
    TRANSFORM_INVERSE_MISMATCH = "TRANSFORM_INVERSE_MISMATCH"
    # IDs and references
    DUPLICATE_ID = "DUPLICATE_ID"
    UNKNOWN_REFERENCE = "UNKNOWN_REFERENCE"
    WRONG_REFERENCE_TYPE = "WRONG_REFERENCE_TYPE"
    # Pipes
    PIPE_ENDPOINT_MISMATCH = "PIPE_ENDPOINT_MISMATCH"
    PIPE_DEGENERATE = "PIPE_DEGENERATE"
    # Symbols
    SYMBOL_PORT_UNKNOWN_NAME = "SYMBOL_PORT_UNKNOWN_NAME"
    SYMBOL_REQUIRED_PORT_MISSING = "SYMBOL_REQUIRED_PORT_MISSING"
    # Evidence and text
    MACHINE_EVIDENCE_MISSING = "MACHINE_EVIDENCE_MISSING"
    TEXT_INVALID_CHARACTER = "TEXT_INVALID_CHARACTER"
    # Relationships
    RELATIONSHIP_CONNECTIVITY_FORBIDDEN = "RELATIONSHIP_CONNECTIVITY_FORBIDDEN"
    RELATIONSHIP_INVALID_ENDPOINTS = "RELATIONSHIP_INVALID_ENDPOINTS"
    DIMENSION_TARGET_MISMATCH = "DIMENSION_TARGET_MISMATCH"


@dataclass(frozen=True)
class SceneIssue:
    code: IssueCode
    path: str
    object_id: str | None
    message: str


class SceneValidationError(ValueError):
    """Raised with every issue found in a scene, in a stable order."""

    issues: tuple[SceneIssue, ...]

    def __init__(self, issues: Iterable[SceneIssue]) -> None:
        self.issues = tuple(issues)
        if not self.issues:
            raise ValueError("SceneValidationError requires at least one issue")
        lines = [
            f"{issue.code} at {issue.path}: {issue.message}" for issue in self.issues
        ]
        count = len(self.issues)
        noun = "issue" if count == 1 else "issues"
        super().__init__(f"{count} scene {noun}:\n" + "\n".join(lines))

    @property
    def codes(self) -> tuple[IssueCode, ...]:
        return tuple(issue.code for issue in self.issues)
