"""Versioned DrawingScene contract: models, validation, and serialization."""

from .errors import IssueCode, SceneIssue, SceneValidationError
from .models import SCENE_SCHEMA_VERSION, DrawingScene
from .serialization import dump_scene, load_scene
from .validation import SymbolCatalog, validate_scene
from .versioning import check_version

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
