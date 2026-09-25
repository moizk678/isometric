"""Issue codes and the exception raised when rendering or SVG validation fails."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class RenderIssueCode(StrEnum):
    # Inputs
    SCENE_INVALID = "SCENE_INVALID"
    VERSION_UNSUPPORTED = "VERSION_UNSUPPORTED"
    # SVG safety
    SVG_XML_INVALID = "SVG_XML_INVALID"
    SVG_ELEMENT_FORBIDDEN = "SVG_ELEMENT_FORBIDDEN"
    SVG_ATTRIBUTE_FORBIDDEN = "SVG_ATTRIBUTE_FORBIDDEN"
    SVG_EXTERNAL_REFERENCE = "SVG_EXTERNAL_REFERENCE"
    SVG_OUT_OF_BOUNDS = "SVG_OUT_OF_BOUNDS"
    SVG_SEMANTIC_MISMATCH = "SVG_SEMANTIC_MISMATCH"
    # Preview
    RASTERIZE_FAILED = "RASTERIZE_FAILED"


@dataclass(frozen=True)
class RenderIssue:
    code: RenderIssueCode
    path: str
    object_id: str | None
    message: str


class RenderError(ValueError):
    """Raised with every issue found while rendering, in a stable order."""

    issues: tuple[RenderIssue, ...]

    def __init__(self, issues: Iterable[RenderIssue]) -> None:
        self.issues = tuple(issues)
        if not self.issues:
            raise ValueError("RenderError requires at least one issue")
        lines = [
            f"{issue.code} at {issue.path}: {issue.message}" for issue in self.issues
        ]
        count = len(self.issues)
        noun = "issue" if count == 1 else "issues"
        super().__init__(f"{count} render {noun}:\n" + "\n".join(lines))

    @property
    def codes(self) -> tuple[RenderIssueCode, ...]:
        return tuple(issue.code for issue in self.issues)
