"""Canonical JSON load/dump for DrawingScene."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from .errors import IssueCode, SceneIssue, SceneValidationError
from .models import DrawingScene
from .validation import SymbolCatalog, validate_scene
from .versioning import check_version


def _json_constant(name: str) -> float:
    if name == "NaN":
        return float("nan")
    if name == "Infinity":
        return float("inf")
    if name == "-Infinity":
        return float("-inf")
    raise ValueError(f"invalid JSON constant: {name!r}")


def _path_join(prefix: str, segment: str) -> str:
    if prefix == "$":
        return segment if segment.startswith("[") else f"$.{segment}"
    if segment.startswith("["):
        return f"{prefix}{segment}"
    return f"{prefix}.{segment}"


def _collect_non_finite(value: Any, *, path: str = "$") -> list[SceneIssue]:
    issues: list[SceneIssue] = []
    if isinstance(value, float):
        if not math.isfinite(value):
            issues.append(
                SceneIssue(
                    code=IssueCode.NON_FINITE_NUMBER,
                    path=path,
                    object_id=None,
                    message="number must be finite",
                )
            )
        return issues
    if isinstance(value, dict):
        for key, item in value.items():
            issues.extend(_collect_non_finite(item, path=_path_join(path, str(key))))
        return issues
    if isinstance(value, list):
        for index, item in enumerate(value):
            issues.extend(
                _collect_non_finite(item, path=_path_join(path, f"[{index}]"))
            )
    return issues


def _validation_error_to_scene_error(exc: ValidationError) -> SceneValidationError:
    issues = [
        SceneIssue(
            code=IssueCode.SCHEMA_INVALID,
            path=".".join(str(part) for part in error["loc"]) or "$",
            object_id=None,
            message=error["msg"],
        )
        for error in exc.errors()
    ]
    return SceneValidationError(issues)


def _normalize_negative_zero(value: Any) -> Any:
    if isinstance(value, float):
        if value == 0.0 and math.copysign(1.0, value) < 0:
            return 0.0
        return value
    if isinstance(value, dict):
        return {key: _normalize_negative_zero(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_negative_zero(item) for item in value]
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r}")
        result[key] = value
    return result


def _parse_error(message: str) -> SceneValidationError:
    return SceneValidationError(
        [
            SceneIssue(
                code=IssueCode.SCHEMA_INVALID,
                path="$",
                object_id=None,
                message=message,
            )
        ]
    )


def _parse_wire_data(data: str | bytes | Mapping[str, Any]) -> Any:
    if not isinstance(data, (str, bytes)):
        return data
    try:
        text = data.decode("utf-8") if isinstance(data, bytes) else data
        return json.loads(
            text,
            parse_constant=_json_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except RecursionError:
        raise _parse_error("JSON nesting is too deep") from None
    except ValueError as exc:
        raise _parse_error(f"invalid JSON: {exc}") from None


def load_scene(
    data: str | bytes | Mapping[str, Any],
    *,
    catalog: SymbolCatalog | None = None,
    endpoint_tolerance_px: float = 1e-6,
) -> DrawingScene:
    """Parse wire JSON (or a mapping), validate, and run scene invariants."""
    raw = _parse_wire_data(data)
    if not isinstance(raw, dict):
        raise _parse_error("scene document must be a JSON object")

    non_finite = _collect_non_finite(raw)
    if non_finite:
        raise SceneValidationError(non_finite)

    versioned = check_version(raw)
    try:
        scene = DrawingScene.model_validate(versioned)
    except ValidationError as exc:
        raise _validation_error_to_scene_error(exc) from None

    validate_scene(
        scene,
        catalog=catalog,
        endpoint_tolerance_px=endpoint_tolerance_px,
    )
    return scene


def dump_scene(scene: DrawingScene) -> str:
    """Serialize a scene to canonical JSON with a trailing newline."""
    payload = scene.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload = _normalize_negative_zero(payload)
    return (
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            allow_nan=False,
            ensure_ascii=False,
        )
        + "\n"
    )
