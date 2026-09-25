"""Deterministic SVG export, SVG safety validation, and PNG preview."""

from .errors import RenderError, RenderIssue, RenderIssueCode
from .preview import rasterize_preview
from .safety import validate_svg
from .style import STYLE_PROFILES, StyleProfile, get_style_profile
from .svg import render_svg
from .symbols import load_symbol_library
from .types import (
    ExportMetadata,
    PreviewResult,
    RenderResult,
    SymbolDefinition,
    SymbolLibrary,
    SymbolPort,
    SymbolPrimitive,
    UnresolvedItem,
)
from .versions import (
    RASTERIZER,
    RENDERER_VERSION,
    STYLE_PROFILE_VERSION,
    SYMBOL_LIBRARY_VERSION,
)

__all__ = [
    "RASTERIZER",
    "RENDERER_VERSION",
    "STYLE_PROFILES",
    "STYLE_PROFILE_VERSION",
    "SYMBOL_LIBRARY_VERSION",
    "ExportMetadata",
    "PreviewResult",
    "RenderError",
    "RenderIssue",
    "RenderIssueCode",
    "RenderResult",
    "StyleProfile",
    "SymbolDefinition",
    "SymbolLibrary",
    "SymbolPort",
    "SymbolPrimitive",
    "UnresolvedItem",
    "get_style_profile",
    "load_symbol_library",
    "rasterize_preview",
    "render_svg",
    "validate_svg",
]
