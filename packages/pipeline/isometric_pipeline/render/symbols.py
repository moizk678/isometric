"""Loading of the versioned piping symbol library."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .errors import RenderError, RenderIssue, RenderIssueCode
from .types import (
    SymbolAllowedAttachments,
    SymbolDefinition,
    SymbolLibrary,
    SymbolPort,
    SymbolPrimitive,
)
from .versions import CLASSIFIER_SYMBOL_LIBRARY_VERSION, SYMBOL_LIBRARY_VERSION

__all__ = ["SymbolLibrary", "load_symbol_library"]

_SYMBOL_LIBRARY_DIR = Path(__file__).resolve().parents[3] / "symbol-library"
_SYMBOL_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_COORD_MIN = -24.0
_COORD_MAX = 24.0
_TOP_LEVEL_KEYS = frozenset({"version", "units", "symbols"})
_SYMBOL_KEYS_V10 = frozenset({"id", "label", "ports", "primitives"})
_SYMBOL_KEYS_V11 = _SYMBOL_KEYS_V10 | frozenset(
    {"aliases", "anchor", "allowedAttachments"}
)
_PORT_KEYS = frozenset({"name", "x", "y", "required"})
_PRIMITIVE_KEYS = frozenset({"kind", "points", "fill"})
_CIRCLE_EXTRA_KEYS = frozenset({"r"})
_ANCHOR_KEYS = frozenset({"x", "y"})
_ATTACHMENTS_KEYS = frozenset({"nodeKinds", "minIncidentEdges", "maxIncidentEdges"})

_VERSION_FILES: dict[str, str] = {
    SYMBOL_LIBRARY_VERSION: "piping-symbols-1.0.0.json",
    CLASSIFIER_SYMBOL_LIBRARY_VERSION: "piping-symbols-1.1.0.json",
}


def load_symbol_library(version: str) -> SymbolLibrary:
    """Load a bundled library or raise ``RenderError`` ``VERSION_UNSUPPORTED``."""
    filename = _VERSION_FILES.get(version)
    if filename is None:
        raise RenderError(
            [
                RenderIssue(
                    RenderIssueCode.VERSION_UNSUPPORTED,
                    "symbol_library_version",
                    None,
                    f"unsupported symbol library version {version!r}",
                )
            ]
        )

    path = _SYMBOL_LIBRARY_DIR / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    extended = version == CLASSIFIER_SYMBOL_LIBRARY_VERSION
    return _parse_library(payload, version, extended_metadata=extended)


def _parse_library(
    payload: Any, expected_version: str, *, extended_metadata: bool
) -> SymbolLibrary:
    if not isinstance(payload, dict):
        raise ValueError("symbol library root must be an object")
    _reject_unknown_keys(payload, _TOP_LEVEL_KEYS, "symbol library")

    file_version = payload["version"]
    if file_version != expected_version:
        raise RenderError(
            [
                RenderIssue(
                    RenderIssueCode.VERSION_UNSUPPORTED,
                    "version",
                    None,
                    (
                        f"library file version {file_version!r} does not match "
                        f"requested {expected_version!r}"
                    ),
                )
            ]
        )

    units = payload["units"]
    if units != "px":
        raise ValueError(f"unsupported symbol library units {units!r}")

    raw_symbols = payload["symbols"]
    if not isinstance(raw_symbols, list):
        raise ValueError("symbols must be an array")

    symbols = [
        _parse_symbol(entry, index, extended_metadata=extended_metadata)
        for index, entry in enumerate(raw_symbols)
    ]
    ids = [symbol.id for symbol in symbols]
    if ids != sorted(ids):
        raise ValueError("symbols must be sorted by id")

    return SymbolLibrary(expected_version, symbols)


def _parse_symbol(
    entry: Any, index: int, *, extended_metadata: bool
) -> SymbolDefinition:
    path = f"symbols[{index}]"
    if not isinstance(entry, dict):
        raise ValueError(f"{path} must be an object")
    allowed_keys = _SYMBOL_KEYS_V11 if extended_metadata else _SYMBOL_KEYS_V10
    _reject_unknown_keys(entry, allowed_keys, path)

    symbol_id = entry["id"]
    if not isinstance(symbol_id, str) or not _SYMBOL_ID_RE.fullmatch(symbol_id):
        raise ValueError(f"{path}.id is invalid")

    label = entry["label"]
    if not isinstance(label, str):
        raise ValueError(f"{path}.label must be a string")

    aliases: tuple[str, ...] = ()
    anchor_x = 0.0
    anchor_y = 0.0
    allowed_attachments: SymbolAllowedAttachments | None = None
    if extended_metadata:
        raw_aliases = entry.get("aliases", [])
        if not isinstance(raw_aliases, list):
            raise ValueError(f"{path}.aliases must be an array")
        aliases = tuple(str(a) for a in raw_aliases)
        anchor_raw = entry.get("anchor", {"x": 0, "y": 0})
        if not isinstance(anchor_raw, dict):
            raise ValueError(f"{path}.anchor must be an object")
        _reject_unknown_keys(anchor_raw, _ANCHOR_KEYS, f"{path}.anchor")
        anchor_x = _finite_number(anchor_raw["x"], f"{path}.anchor.x")
        anchor_y = _finite_number(anchor_raw["y"], f"{path}.anchor.y")
        _check_coord(anchor_x, f"{path}.anchor.x")
        _check_coord(anchor_y, f"{path}.anchor.y")
        attach_raw = entry.get(
            "allowedAttachments",
            {"nodeKinds": [], "minIncidentEdges": None, "maxIncidentEdges": None},
        )
        if not isinstance(attach_raw, dict):
            raise ValueError(f"{path}.allowedAttachments must be an object")
        _reject_unknown_keys(
            attach_raw, _ATTACHMENTS_KEYS, f"{path}.allowedAttachments"
        )
        kinds_raw = attach_raw["nodeKinds"]
        if not isinstance(kinds_raw, list):
            raise ValueError(f"{path}.allowedAttachments.nodeKinds must be an array")
        min_edges = attach_raw["minIncidentEdges"]
        max_edges = attach_raw["maxIncidentEdges"]
        allowed_attachments = SymbolAllowedAttachments(
            node_kinds=frozenset(str(k) for k in kinds_raw),
            min_incident_edges=int(min_edges) if min_edges is not None else None,
            max_incident_edges=int(max_edges) if max_edges is not None else None,
        )

    raw_ports = entry["ports"]
    if not isinstance(raw_ports, list):
        raise ValueError(f"{path}.ports must be an array")
    ports = tuple(
        _parse_port(port, f"{path}.ports[{port_index}]")
        for port_index, port in enumerate(raw_ports)
    )
    port_names = [port.name for port in ports]
    if len(port_names) != len(set(port_names)):
        raise ValueError(f"{path}.ports contains duplicate names")

    raw_primitives = entry["primitives"]
    if not isinstance(raw_primitives, list):
        raise ValueError(f"{path}.primitives must be an array")
    primitives = tuple(
        _parse_primitive(primitive, f"{path}.primitives[{prim_index}]")
        for prim_index, primitive in enumerate(raw_primitives)
    )

    return SymbolDefinition(
        id=symbol_id,
        label=label,
        ports=ports,
        primitives=primitives,
        aliases=aliases,
        anchor_x=anchor_x,
        anchor_y=anchor_y,
        allowed_attachments=allowed_attachments,
    )


def _parse_port(entry: Any, path: str) -> SymbolPort:
    if not isinstance(entry, dict):
        raise ValueError(f"{path} must be an object")
    _reject_unknown_keys(entry, _PORT_KEYS, path)

    name = entry["name"]
    if not isinstance(name, str):
        raise ValueError(f"{path}.name must be a string")

    x = _finite_number(entry["x"], f"{path}.x")
    y = _finite_number(entry["y"], f"{path}.y")
    _check_coord(x, f"{path}.x")
    _check_coord(y, f"{path}.y")

    required = entry["required"]
    if not isinstance(required, bool):
        raise ValueError(f"{path}.required must be a boolean")

    return SymbolPort(name=name, x=x, y=y, required=required)


def _parse_primitive(entry: Any, path: str) -> SymbolPrimitive:
    if not isinstance(entry, dict):
        raise ValueError(f"{path} must be an object")

    kind = entry.get("kind")
    if kind == "circle":
        allowed = _PRIMITIVE_KEYS | _CIRCLE_EXTRA_KEYS
    else:
        allowed = _PRIMITIVE_KEYS
    _reject_unknown_keys(entry, allowed, path)

    if kind not in ("line", "circle", "polygon"):
        raise ValueError(f"{path}.kind must be line, circle, or polygon")

    fill = entry["fill"]
    if not isinstance(fill, bool):
        raise ValueError(f"{path}.fill must be a boolean")

    points = _parse_points(entry["points"], path)
    radius: float | None = None

    if kind == "line":
        if len(points) != 2:
            raise ValueError(f"{path}.points must have exactly 2 points for a line")
    elif kind == "polygon":
        if len(points) < 3:
            raise ValueError(f"{path}.points must have at least 3 points for a polygon")
    else:
        if len(points) != 1:
            raise ValueError(f"{path}.points must have exactly 1 point for a circle")
        radius = _finite_number(entry["r"], f"{path}.r")
        if radius <= 0:
            raise ValueError(f"{path}.r must be greater than 0")
        center_x, center_y = points[0]
        _check_coord(center_x - radius, f"{path} circle extent")
        _check_coord(center_x + radius, f"{path} circle extent")
        _check_coord(center_y - radius, f"{path} circle extent")
        _check_coord(center_y + radius, f"{path} circle extent")

    for point_index, (x, y) in enumerate(points):
        _check_coord(x, f"{path}.points[{point_index}][0]")
        _check_coord(y, f"{path}.points[{point_index}][1]")

    return SymbolPrimitive(kind=kind, points=points, radius=radius, fill=fill)


def _parse_points(raw: Any, path: str) -> tuple[tuple[float, float], ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{path}.points must be an array")
    points: list[tuple[float, float]] = []
    for index, point in enumerate(raw):
        point_path = f"{path}.points[{index}]"
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(f"{point_path} must be a pair of numbers")
        x = _finite_number(point[0], f"{point_path}[0]")
        y = _finite_number(point[1], f"{point_path}[1]")
        points.append((x, y))
    return tuple(points)


def _finite_number(value: Any, path: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{path} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{path} must be finite")
    return number


def _check_coord(value: float, path: str) -> None:
    if value < _COORD_MIN or value > _COORD_MAX:
        raise ValueError(f"{path} must be within [{_COORD_MIN}, {_COORD_MAX}]")


def _reject_unknown_keys(
    entry: dict[str, Any], allowed: frozenset[str], path: str
) -> None:
    unknown = sorted(set(entry) - allowed)
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"{path} has unknown keys: {joined}")
