"""The SVG vocabulary the renderer may emit and the validator accepts.

The renderer builds output only from these constants and ``safety.validate_svg``
checks against them, so the two cannot drift apart. Anything absent here is
forbidden, including ``style``, ``on*`` handlers, ``script``, ``foreignObject``,
``image``, ``a``, and ``xlink:*``.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

SVG_NAMESPACE: Final = "http://www.w3.org/2000/svg"

_OBJECT = frozenset({"id", "data-object-id", "data-state"})
_PAINT = frozenset(
    {
        "stroke",
        "stroke-width",
        "stroke-dasharray",
        "stroke-linecap",
        "stroke-linejoin",
        "fill",
    }
)

ELEMENT_ATTRIBUTES: Final[Mapping[str, frozenset[str]]] = MappingProxyType(
    {
        "svg": frozenset(
            {"xmlns", "viewBox", "width", "height", "font-family", "font-size"}
        ),
        "metadata": frozenset(),
        "defs": frozenset(),
        # Symbol geometry is centered on the local origin, so overflow="visible"
        # is required or resvg clips the negative half.
        "symbol": frozenset({"id", "overflow"}),
        "marker": frozenset(
            {
                "id",
                "viewBox",
                "refX",
                "refY",
                "markerWidth",
                "markerHeight",
                "markerUnits",
                "orient",
                "overflow",
            }
        ),
        "g": _OBJECT | _PAINT | {"transform", "font-family", "font-size"},
        "line": _OBJECT
        | _PAINT
        | {"x1", "y1", "x2", "y2", "marker-start", "marker-end"},
        "circle": _OBJECT | _PAINT | {"cx", "cy", "r"},
        "polygon": _OBJECT | _PAINT | {"points"},
        # Only for renderer-owned marker geometry; never carries an object ID.
        "path": frozenset({"id", "d"}) | _PAINT,
        "use": _OBJECT | _PAINT | {"href", "transform"},
        "text": _OBJECT
        | {
            "data-recognized-text",
            "x",
            "y",
            "fill",
            "font-family",
            "font-size",
            "text-anchor",
            "transform",
        },
    }
)

ALLOWED_ELEMENTS: Final = frozenset(ELEMENT_ATTRIBUTES)

# ``href`` must be ``#id`` of a local ``symbol`` or ``marker``.
HREF_ATTRIBUTES: Final = frozenset({"href"})
HREF_TARGET_ELEMENTS: Final = frozenset({"symbol", "marker"})
# These must be exactly ``url(#id)`` of a local ``marker``.
URL_REFERENCE_ATTRIBUTES: Final = frozenset({"marker-start", "marker-end"})

# Page-space coordinates, checked against the viewBox plus the bounds margin.
# Coordinates inside ``symbol`` and ``marker`` are local and exempt.
COORDINATE_ATTRIBUTES: Final = frozenset(
    {"x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "points"}
)

GROUP_IDS: Final = (
    "pipes",
    "connections",
    "symbols",
    "dimensions",
    "callouts",
    "annotations",
    "unresolved",
)

OBJECT_ID_PREFIX: Final = "obj-"
LAYER_ID_PREFIX: Final = "layer-"
SYMBOL_ID_PREFIX: Final = "sym-"
MARKER_ID_PREFIX: Final = "marker-"
ID_PREFIXES: Final = (
    OBJECT_ID_PREFIX,
    LAYER_ID_PREFIX,
    SYMBOL_ID_PREFIX,
    MARKER_ID_PREFIX,
)

PREVIEW_ONLY_GROUP_IDS: Final = frozenset({"paper-overlay", "review-overlay"})

DATA_STATES: Final = frozenset({"machine", "confirmed", "unknown"})


def is_allowed_id(value: str) -> bool:
    """True for a group ID or an ID with a known prefix and a non-empty suffix."""
    if value in GROUP_IDS:
        return True
    return any(
        value.startswith(prefix) and len(value) > len(prefix) for prefix in ID_PREFIXES
    )
