"""Map scene edit/validation failures to API errors."""

from __future__ import annotations

from isometric_pipeline.scene import SceneValidationError
from pydantic import ValidationError

from .errors import ApiError


def raise_for_scene_failure(exc: BaseException) -> None:
    if isinstance(exc, SceneValidationError):
        raise ApiError(400, "scene_invalid", str(exc)) from exc
    if isinstance(exc, ValidationError):
        raise ApiError(400, "invalid_request", "edit command payload is invalid") from exc
    if isinstance(exc, ValueError):
        raise ApiError(400, "invalid_request", str(exc)) from exc
    raise exc
