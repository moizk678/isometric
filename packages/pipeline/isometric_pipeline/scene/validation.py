"""Cross-object invariants that a JSON Schema cannot express.

``validate_scene`` runs every check, including the schema version, and raises
one ``SceneValidationError`` holding all issues. Checks run in a fixed pass order and each pass walks the
scene in document order, so the issue order is stable for a given scene.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel

from .errors import IssueCode, SceneIssue, SceneValidationError
from .models import (
    Annotation,
    Dimension,
    DrawingScene,
    Interpretation,
    Junction,
    Layer,
    PagePoint,
    PipeSegment,
    Relationship,
    SourcePoint,
    SymbolObject,
)
from .versioning import is_supported_version

INVERSE_TOLERANCE = 1e-9

_CONNECTIVITY_TYPES = frozenset({"pipe_segment", "junction", "symbol"})
_RELATIONSHIP_SOURCE_TYPES = {
    "annotates": "annotation",
    "callout_targets": "annotation",
    "measures": "dimension",
}
_TRANSFORM_PAIRS = (
    ("sourceToDisplay", "displayToSource"),
    ("sourceToPage", "pageToSource"),
)


class SymbolCatalog(Protocol):
    def port_names(self, symbol_id: str) -> frozenset[str] | None:
        """Port names of a symbol, or ``None`` when the symbol is unknown."""
        ...

    def required_ports(self, symbol_id: str) -> frozenset[str]: ...


@dataclass(frozen=True)
class _Entry:
    kind: Literal["layer", "object", "relationship"]
    value: Any
    path: str


class _Collector:
    def __init__(self) -> None:
        self.issues: list[SceneIssue] = []

    def add(
        self, code: IssueCode, path: str, object_id: str | None, message: str
    ) -> None:
        self.issues.append(SceneIssue(code, path, object_id, message))


def validate_scene(
    scene: DrawingScene,
    *,
    catalog: SymbolCatalog | None = None,
    endpoint_tolerance_px: float = 1e-6,
) -> None:
    """Raise ``SceneValidationError`` with every invariant the scene violates."""
    if not (math.isfinite(endpoint_tolerance_px) and endpoint_tolerance_px >= 0):
        raise ValueError(
            f"endpoint_tolerance_px must be finite and >= 0, "
            f"got {endpoint_tolerance_px}"
        )
    out = _Collector()
    if not is_supported_version(scene.schema_version):
        out.add(
            IssueCode.VERSION_UNSUPPORTED,
            "schemaVersion",
            None,
            f"unsupported schema version {scene.schema_version!r}",
        )
    _check_values(scene, out)
    _check_transforms(scene, out)
    index = _index_ids(scene, out)
    _check_references(scene, index, out)
    _check_pipes(scene, index, endpoint_tolerance_px, out)
    if catalog is not None:
        _check_symbols(scene, catalog, out)
    _check_evidence(scene, out)
    _check_relationships(scene, index, out)
    if out.issues:
        raise SceneValidationError(out.issues)


# Numbers, coordinates, and text


def _check_values(scene: DrawingScene, out: _Collector) -> None:
    page = scene.page
    for path, owner, value in _walk(scene, "", None):
        if isinstance(value, float):
            if not math.isfinite(value):
                out.add(
                    IssueCode.NON_FINITE_NUMBER, path, owner, f"{value} is not finite"
                )
        elif isinstance(value, str):
            bad = _first_invalid_xml_char(value)
            if bad is not None:
                out.add(
                    IssueCode.TEXT_INVALID_CHARACTER,
                    path,
                    owner,
                    f"contains XML-invalid character U+{ord(bad):04X}",
                )
        elif isinstance(value, PagePoint):
            _check_bounds(
                value, page.width_px, page.height_px, "page", path, owner, out
            )
        elif isinstance(value, SourcePoint):
            _check_bounds(
                value,
                page.source_width_px,
                page.source_height_px,
                "source",
                path,
                owner,
                out,
            )


def _walk(value: Any, path: str, owner: str | None) -> Iterator[tuple[str, Any, Any]]:
    """Yield ``(path, owner_id, value)`` for every node, parents before children."""
    yield path, owner, value
    if isinstance(value, BaseModel):
        if isinstance(value, Layer | Relationship) or hasattr(value, "layer_id"):
            owner = value.id
        for name, field in type(value).model_fields.items():
            child = getattr(value, name)
            if child is not None:
                alias = field.alias or name
                yield from _walk(child, f"{path}.{alias}" if path else alias, owner)
    elif isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{path}[{json.dumps(key, ensure_ascii=False)}]"
            yield f"{key_path}(key)", owner, key
            yield from _walk(child, key_path, owner)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from _walk(child, f"{path}[{i}]", owner)


def _check_bounds(
    point: PagePoint | SourcePoint,
    width: int,
    height: int,
    space: str,
    path: str,
    owner: str | None,
    out: _Collector,
) -> None:
    x, y = point.x, point.y
    if not (math.isfinite(x) and math.isfinite(y)):
        return
    if not (0 <= x <= width and 0 <= y <= height):
        out.add(
            IssueCode.COORDINATE_OUT_OF_BOUNDS,
            path,
            owner,
            f"({x}, {y}) is outside the {width}x{height} {space} area",
        )


def _first_invalid_xml_char(text: str) -> str | None:
    for char in text:
        code = ord(char)
        if not (
            code in (0x9, 0xA, 0xD)
            or 0x20 <= code <= 0xD7FF
            or 0xE000 <= code <= 0xFFFD
            or 0x10000 <= code <= 0x10FFFF
        ):
            return char
    return None


# Transforms


def _check_transforms(scene: DrawingScene, out: _Collector) -> None:
    page = scene.page
    matrices = {
        "sourceToDisplay": page.source_to_display,
        "displayToSource": page.display_to_source,
        "sourceToPage": page.source_to_page,
        "pageToSource": page.page_to_source,
    }
    for forward_name, inverse_name in _TRANSFORM_PAIRS:
        usable = True
        for name in (forward_name, inverse_name):
            matrix = matrices[name]
            if len(matrix) != 9 or not all(math.isfinite(v) for v in matrix):
                usable = False
            elif _determinant(matrix) == 0:
                out.add(
                    IssueCode.TRANSFORM_SINGULAR,
                    f"page.{name}",
                    None,
                    "determinant is zero",
                )
                usable = False
        if not usable:
            continue
        product = _multiply(matrices[forward_name], matrices[inverse_name])
        if not _is_scaled_identity(product):
            out.add(
                IssueCode.TRANSFORM_INVERSE_MISMATCH,
                f"page.{inverse_name}",
                None,
                f"{forward_name} x {inverse_name} is not the identity "
                f"within {INVERSE_TOLERANCE}",
            )


def _determinant(m: Sequence[float]) -> float:
    return (
        m[0] * (m[4] * m[8] - m[5] * m[7])
        - m[1] * (m[3] * m[8] - m[5] * m[6])
        + m[2] * (m[3] * m[7] - m[4] * m[6])
    )


def _multiply(a: Sequence[float], b: Sequence[float]) -> list[float]:
    return [
        sum(a[row * 3 + k] * b[k * 3 + col] for k in range(3))
        for row in range(3)
        for col in range(3)
    ]


def _is_scaled_identity(m: Sequence[float]) -> bool:
    scale = m[8]
    if not math.isfinite(scale) or scale == 0:
        return False
    for i, value in enumerate(m):
        expected = 1.0 if i in (0, 4, 8) else 0.0
        normalized = value / scale
        if not math.isfinite(normalized):
            return False
        if abs(normalized - expected) > INVERSE_TOLERANCE:
            return False
    return True


# IDs and references


def _index_ids(scene: DrawingScene, out: _Collector) -> dict[str, _Entry]:
    index: dict[str, _Entry] = {}
    groups: tuple[tuple[str, Literal["layer", "object", "relationship"], list], ...] = (
        ("layers", "layer", scene.layers),
        ("objects", "object", scene.objects),
        ("relationships", "relationship", scene.relationships),
    )
    for field, kind, items in groups:
        for i, item in enumerate(items):
            path = f"{field}[{i}].id"
            first = index.get(item.id)
            if first is not None:
                out.add(
                    IssueCode.DUPLICATE_ID,
                    path,
                    item.id,
                    f"ID is already used at {first.path}",
                )
            else:
                index[item.id] = _Entry(kind, item, path)
    return index


def _resolve(
    ref: str,
    expected: Literal["layer", "object", "junction"],
    path: str,
    owner: str,
    index: dict[str, _Entry],
    out: _Collector,
) -> Any:
    entry = index.get(ref)
    if entry is None:
        out.add(IssueCode.UNKNOWN_REFERENCE, path, owner, f"{ref} does not exist")
        return None
    if expected == "layer":
        ok = entry.kind == "layer"
    elif expected == "object":
        ok = entry.kind == "object"
    else:
        ok = entry.kind == "object" and isinstance(entry.value, Junction)
    if not ok:
        actual = entry.value.type if entry.kind == "object" else entry.kind
        out.add(
            IssueCode.WRONG_REFERENCE_TYPE,
            path,
            owner,
            f"{ref} is a {actual}, expected a {expected}",
        )
        return None
    return entry.value


def _check_references(
    scene: DrawingScene, index: dict[str, _Entry], out: _Collector
) -> None:
    for i, obj in enumerate(scene.objects):
        base = f"objects[{i}]"
        _resolve(obj.layer_id, "layer", f"{base}.layerId", obj.id, index, out)
        if isinstance(obj, PipeSegment):
            for alias, ref in (
                ("startNodeId", obj.start_node_id),
                ("endNodeId", obj.end_node_id),
            ):
                _resolve(ref, "junction", f"{base}.{alias}", obj.id, index, out)
        elif isinstance(obj, SymbolObject):
            for port, ref in obj.port_node_ids.items():
                if ref is not None:
                    path = f"{base}.portNodeIds[{json.dumps(port, ensure_ascii=False)}]"
                    _resolve(ref, "junction", path, obj.id, index, out)
        elif isinstance(obj, Annotation):
            if obj.target_object_id is not None:
                _resolve(
                    obj.target_object_id,
                    "object",
                    f"{base}.targetObjectId",
                    obj.id,
                    index,
                    out,
                )
        elif isinstance(obj, Dimension):
            for j, ref in enumerate(obj.target_object_ids):
                path = f"{base}.targetObjectIds[{j}]"
                _resolve(ref, "object", path, obj.id, index, out)


# Pipes


def _check_pipes(
    scene: DrawingScene,
    index: dict[str, _Entry],
    tolerance: float,
    out: _Collector,
) -> None:
    for i, obj in enumerate(scene.objects):
        if not isinstance(obj, PipeSegment):
            continue
        base = f"objects[{i}]"
        start, end = obj.primitive.start, obj.primitive.end
        if obj.start_node_id == obj.end_node_id:
            out.add(
                IssueCode.PIPE_DEGENERATE,
                f"{base}.endNodeId",
                obj.id,
                "pipe starts and ends at the same node",
            )
        elif _distance(start, end) <= tolerance:
            out.add(
                IssueCode.PIPE_DEGENERATE,
                f"{base}.primitive",
                obj.id,
                "pipe has zero length",
            )
        for alias, ref, point in (
            ("start", obj.start_node_id, start),
            ("end", obj.end_node_id, end),
        ):
            entry = index.get(ref)
            if entry is None or not isinstance(entry.value, Junction):
                continue
            node = entry.value.position
            gap = _distance(point, node)
            if math.isfinite(gap) and gap > tolerance:
                out.add(
                    IssueCode.PIPE_ENDPOINT_MISMATCH,
                    f"{base}.primitive.{alias}",
                    obj.id,
                    f"endpoint is {gap} px from junction {ref} (tolerance {tolerance})",
                )


def _distance(a: PagePoint, b: PagePoint) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


# Symbols


def _check_symbols(
    scene: DrawingScene, catalog: SymbolCatalog, out: _Collector
) -> None:
    for i, obj in enumerate(scene.objects):
        if not isinstance(obj, SymbolObject):
            continue
        base = f"objects[{i}]"
        names = catalog.port_names(obj.symbol_id)
        if names is None:
            out.add(
                IssueCode.UNKNOWN_REFERENCE,
                f"{base}.symbolId",
                obj.id,
                f"symbol {obj.symbol_id!r} is not in the catalog",
            )
            continue
        for port in obj.port_node_ids:
            if port not in names:
                out.add(
                    IssueCode.SYMBOL_PORT_UNKNOWN_NAME,
                    f"{base}.portNodeIds[{json.dumps(port, ensure_ascii=False)}](key)",
                    obj.id,
                    f"{obj.symbol_id!r} has no port {port!r}",
                )
        for port in sorted(catalog.required_ports(obj.symbol_id)):
            if port not in obj.port_node_ids:
                out.add(
                    IssueCode.SYMBOL_REQUIRED_PORT_MISSING,
                    f"{base}.portNodeIds",
                    obj.id,
                    f"required port {port!r} is missing",
                )


# Evidence


def _check_evidence(scene: DrawingScene, out: _Collector) -> None:
    owners: list[tuple[str, str, Interpretation]] = [
        (f"objects[{i}].interpretation", obj.id, obj.interpretation)
        for i, obj in enumerate(scene.objects)
    ]
    owners += [
        (f"relationships[{i}].interpretation", rel.id, rel.interpretation)
        for i, rel in enumerate(scene.relationships)
    ]
    for path, owner, interpretation in owners:
        if interpretation.state == "machine" and not interpretation.evidence:
            out.add(
                IssueCode.MACHINE_EVIDENCE_MISSING,
                f"{path}.evidence",
                owner,
                "machine interpretation has no evidence",
            )


# Relationships


def _check_relationships(
    scene: DrawingScene, index: dict[str, _Entry], out: _Collector
) -> None:
    measured: set[tuple[str, str]] = set()
    for i, rel in enumerate(scene.relationships):
        base = f"relationships[{i}]"
        source = _resolve(rel.from_id, "object", f"{base}.fromId", rel.id, index, out)
        target = _resolve(rel.to_id, "object", f"{base}.toId", rel.id, index, out)
        if (
            source is not None
            and target is not None
            and source.type in _CONNECTIVITY_TYPES
            and target.type in _CONNECTIVITY_TYPES
        ):
            out.add(
                IssueCode.RELATIONSHIP_CONNECTIVITY_FORBIDDEN,
                base,
                rel.id,
                f"{rel.type} between a {source.type} and a {target.type} would "
                "encode connectivity; use junction node IDs instead",
            )
            continue
        if source is None:
            continue
        required = _RELATIONSHIP_SOURCE_TYPES[rel.type]
        if source.type != required:
            out.add(
                IssueCode.RELATIONSHIP_INVALID_ENDPOINTS,
                f"{base}.fromId",
                rel.id,
                f"{rel.type} must come from a {required}, not a {source.type}",
            )
            continue
        if rel.type == "measures" and target is not None:
            measured.add((source.id, target.id))
            if target.id not in source.target_object_ids:
                out.add(
                    IssueCode.DIMENSION_TARGET_MISMATCH,
                    f"{base}.toId",
                    rel.id,
                    f"{target.id} is not in targetObjectIds of dimension {source.id}",
                )

    for i, obj in enumerate(scene.objects):
        if not isinstance(obj, Dimension):
            continue
        for j, ref in enumerate(obj.target_object_ids):
            entry = index.get(ref)
            if entry is None or entry.kind != "object":
                continue
            if (obj.id, ref) not in measured:
                out.add(
                    IssueCode.DIMENSION_TARGET_MISMATCH,
                    f"objects[{i}].targetObjectIds[{j}]",
                    obj.id,
                    f"no measures relationship from this dimension to {ref}",
                )
