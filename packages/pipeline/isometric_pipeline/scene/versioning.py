"""Schema version checks and migrations for DrawingScene wire data."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

from .errors import IssueCode, SceneIssue, SceneValidationError
from .models import SCENE_SCHEMA_VERSION

Migration = Callable[[dict[str, Any]], dict[str, Any]]

_SUPPORTED_MAJOR = int(SCENE_SCHEMA_VERSION.split(".")[0])
_SUPPORTED_MINOR = int(SCENE_SCHEMA_VERSION.split(".")[1])

MIGRATIONS: dict[tuple[int, int], Migration] = {}


def _version_unsupported(
    version: str, message: str | None = None
) -> SceneValidationError:
    detail = message or f"unsupported schema version {version!r}"
    return SceneValidationError(
        [
            SceneIssue(
                code=IssueCode.VERSION_UNSUPPORTED,
                path="schemaVersion",
                object_id=None,
                message=detail,
            )
        ]
    )


def _parse_supported(version: str) -> tuple[int, int] | None:
    parts = version.split(".")
    if len(parts) != 2:
        return None
    try:
        major = int(parts[0], 10)
        minor = int(parts[1], 10)
    except ValueError:
        return None
    if major != _SUPPORTED_MAJOR or minor > _SUPPORTED_MINOR:
        return None
    return major, minor


def is_supported_version(version: str) -> bool:
    """True when this code can read ``version`` (same major, minor not newer)."""
    return _parse_supported(version) is not None


def check_version(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate ``schemaVersion``, migrate if needed, return data for Pydantic."""
    data = copy.deepcopy(dict(raw))
    version = data.get("schemaVersion")
    if version is None:
        raise SceneValidationError(
            [
                SceneIssue(
                    code=IssueCode.SCHEMA_INVALID,
                    path="schemaVersion",
                    object_id=None,
                    message="field required",
                )
            ]
        )
    if not isinstance(version, str):
        raise SceneValidationError(
            [
                SceneIssue(
                    code=IssueCode.SCHEMA_INVALID,
                    path="schemaVersion",
                    object_id=None,
                    message="must be a string",
                )
            ]
        )

    parsed = _parse_supported(version)
    if parsed is None:
        raise _version_unsupported(version)

    migrate = MIGRATIONS.get(parsed)
    if migrate is not None:
        data = migrate(data)

    return data
