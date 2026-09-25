"""Versioned DrawingScene contract: models, validation, and serialization."""

from .errors import IssueCode, SceneIssue, SceneValidationError
from .models import SCENE_SCHEMA_VERSION, DrawingScene


def _is_missing(exc: ModuleNotFoundError, module: str) -> bool:
    return exc.name == f"{__name__}.{module}"


# TODO(w3-review): remove these wave-1 import guards.
try:
    from .validation import SymbolCatalog, validate_scene
except ModuleNotFoundError as exc:
    if not _is_missing(exc, "validation"):
        raise
try:
    from .versioning import check_version
except ModuleNotFoundError as exc:
    if not _is_missing(exc, "versioning"):
        raise
try:
    from .serialization import dump_scene, load_scene
except ModuleNotFoundError as exc:
    if not _is_missing(exc, "serialization"):
        raise

__all__ = [
    "SCENE_SCHEMA_VERSION",
    "DrawingScene",
    "IssueCode",
    "SceneIssue",
    "SceneValidationError",
    "SymbolCatalog",
    "check_version",
    "dump_scene",
    "load_scene",
    "validate_scene",
]
