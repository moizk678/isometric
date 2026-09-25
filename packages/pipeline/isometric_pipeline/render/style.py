"""Versioned style profiles that fix every visual constant of an export."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .errors import RenderError, RenderIssue, RenderIssueCode
from .versions import STYLE_PROFILE_VERSION


@dataclass(frozen=True)
class StyleProfile:
    """Visual constants for one style profile version. Lengths are page pixels.

    Attributes:
        version: Registry key, for example ``"piping-default@1.0.0"``.
        pipe_stroke_width: Width of pipe ``<line>`` elements.
        symbol_stroke_width: Stroke width applied to symbol ``<use>`` elements.
        dimension_stroke_width: Width of dimension witness lines.
        callout_stroke_width: Width of callout leader lines.
        unresolved_stroke_width: Width of unresolved rings and unknown-mark
            polygons.
        unresolved_dasharray: ``stroke-dasharray`` of unknown-mark polygons.
        font_family: ``font-family`` written on every ``<text>``. The preview
            loads only the bundled Liberation Sans, which this list names.
        font_size: ``font-size`` of annotation and dimension text.
        connection_marker_radius: Radius of the filled dot drawn at a junction
            of degree 3 or more.
        unresolved_marker_radius: Radius of the open ring drawn for an unknown
            junction or an unresolved symbol port.
        arrow_size: Length and width of the dimension arrowhead markers.
        symbol_scale: Uniform scale from symbol-local to page pixels. Must stay
            1.0 while symbol ports are defined at +/-20 local pixels to match
            scene junction spacing.
        bounds_margin: How far a numeric coordinate may lie outside the
            ``viewBox`` before the validator reports ``SVG_OUT_OF_BOUNDS``.
        text_color: Fill of annotation and dimension text.
        dimension_color: Stroke of dimension witness lines and arrowheads.
        callout_color: Stroke of callout leader lines.
        unresolved_color: Stroke of everything in the ``unresolved`` group.
        background_color: Preview canvas color. The export has no background.
    """

    version: str
    pipe_stroke_width: float
    symbol_stroke_width: float
    dimension_stroke_width: float
    callout_stroke_width: float
    unresolved_stroke_width: float
    unresolved_dasharray: str
    font_family: str
    font_size: float
    connection_marker_radius: float
    unresolved_marker_radius: float
    arrow_size: float
    symbol_scale: float
    bounds_margin: float
    text_color: str
    dimension_color: str
    callout_color: str
    unresolved_color: str
    background_color: str


PIPING_DEFAULT = StyleProfile(
    version=STYLE_PROFILE_VERSION,
    pipe_stroke_width=2.0,
    symbol_stroke_width=1.5,
    dimension_stroke_width=0.75,
    callout_stroke_width=0.75,
    unresolved_stroke_width=1.0,
    unresolved_dasharray="4 2",
    font_family="Arial, Helvetica, 'Liberation Sans', sans-serif",
    font_size=12.0,
    connection_marker_radius=3.0,
    unresolved_marker_radius=5.0,
    arrow_size=6.0,
    symbol_scale=1.0,
    bounds_margin=16.0,
    text_color="#1a1a1a",
    dimension_color="#1a1a1a",
    callout_color="#1a1a1a",
    unresolved_color="#d93025",
    background_color="#ffffff",
)

STYLE_PROFILES: Mapping[str, StyleProfile] = MappingProxyType(
    {PIPING_DEFAULT.version: PIPING_DEFAULT}
)


def get_style_profile(version: str) -> StyleProfile:
    """Return the registered profile or raise ``VERSION_UNSUPPORTED``."""
    profile = STYLE_PROFILES.get(version)
    if profile is None:
        raise RenderError(
            [
                RenderIssue(
                    code=RenderIssueCode.VERSION_UNSUPPORTED,
                    path="styleProfileVersion",
                    object_id=None,
                    message=f"unsupported style profile version {version!r}",
                )
            ]
        )
    return profile
