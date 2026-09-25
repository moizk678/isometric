"""Pure, deterministic rendering of a DrawingScene to SVG."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypeVar
from xml.sax.saxutils import escape

from ..scene import DrawingScene, SceneValidationError, validate_scene
from ..scene.models import (
    Annotation,
    Dimension,
    Junction,
    Layer,
    PipeSegment,
    SymbolObject,
    UnknownMark,
)
from .allowlist import (
    ELEMENT_ATTRIBUTES,
    GROUP_IDS,
    LAYER_ID_PREFIX,
    MARKER_ID_PREFIX,
    OBJECT_ID_PREFIX,
    SVG_NAMESPACE,
    SYMBOL_ID_PREFIX,
)
from .errors import RenderError, RenderIssue, RenderIssueCode
from .safety import validate_svg
from .style import StyleProfile, get_style_profile
from .symbols import load_symbol_library
from .types import (
    ExportMetadata,
    RenderResult,
    SymbolDefinition,
    SymbolLibrary,
    SymbolPrimitive,
    UnresolvedItem,
)
from .versions import RENDERER_VERSION

SceneObject = (
    PipeSegment | Junction | SymbolObject | Annotation | Dimension | UnknownMark
)
_T = TypeVar("_T", bound=SceneObject)
Point = tuple[float, float]
Attrs = Sequence[tuple[str, str | float]]

ARROW_START_ID = f"{MARKER_ID_PREFIX}arrow-start"
ARROW_END_ID = f"{MARKER_ID_PREFIX}arrow-end"

# XML parsers normalize raw CR to LF in text, and CR, LF, and TAB to spaces in
# attribute values, so these must be character references to round-trip.
_TEXT_ENTITIES = {"\r": "&#13;"}
_ATTR_ENTITIES = {'"': "&quot;", "\t": "&#9;", "\n": "&#10;", "\r": "&#13;"}


def render_svg(
    scene: DrawingScene, symbol_library_version: str, style_profile_version: str
) -> RenderResult:
    """Render ``scene`` to SVG bytes; identical inputs give identical bytes."""
    style = get_style_profile(style_profile_version)
    library = load_symbol_library(symbol_library_version)
    _validate(scene, library)
    view = _View.build(scene)

    unresolved_lines, unresolved = _unresolved(view, library, style)
    metadata = ExportMetadata(
        schema_version=scene.schema_version,
        document_id=scene.document_id,
        revision_id=scene.revision_id,
        renderer_version=RENDERER_VERSION,
        symbol_library_version=symbol_library_version,
        style_profile_version=style.version,
        unresolved_count=len(unresolved),
    )
    groups = {
        "pipes": _pipes(view, style),
        "connections": _connections(view, style),
        "symbols": _symbols(view, style),
        "dimensions": _dimensions(view, style),
        "callouts": _callouts(view, style),
        "annotations": _annotations(view, style),
        "unresolved": unresolved_lines,
    }

    page = scene.page
    lines = [
        "<"
        + _open_tag(
            "svg",
            [
                ("xmlns", SVG_NAMESPACE),
                ("viewBox", f"0 0 {_num(page.width_px)} {_num(page.height_px)}"),
                ("width", page.width_px),
                ("height", page.height_px),
            ],
        )
        + ">",
        _text("metadata", [], _metadata_json(metadata)),
        *_wrap("defs", [], _defs(view, library, style)),
    ]
    for group_id in GROUP_IDS:
        lines += _wrap("g", [("id", group_id)], groups[group_id])
    lines.append("</svg>")

    svg = ("\n".join(lines) + "\n").encode("utf-8")
    validate_svg(svg, scene, style)
    return RenderResult(
        svg=svg,
        sha256=hashlib.sha256(svg).hexdigest(),
        metadata=metadata,
        unresolved=unresolved,
    )


def _validate(scene: DrawingScene, library: SymbolLibrary) -> None:
    try:
        validate_scene(scene, catalog=library)
    except SceneValidationError as exc:
        raise RenderError(
            RenderIssue(
                code=RenderIssueCode.SCENE_INVALID,
                path=issue.path,
                object_id=issue.object_id,
                message=f"{issue.code}: {issue.message}",
            )
            for issue in exc.issues
        ) from exc


@dataclass(frozen=True)
class _View:
    scene: DrawingScene
    by_id: Mapping[str, SceneObject]
    live: tuple[SceneObject, ...]
    layers: Mapping[str, Layer]
    degree: Mapping[str, int]

    @classmethod
    def build(cls, scene: DrawingScene) -> _View:
        live = tuple(
            sorted(
                (o for o in scene.objects if o.interpretation.state != "rejected"),
                key=lambda o: o.id,
            )
        )
        degree: Counter[str] = Counter()
        for obj in live:
            if isinstance(obj, PipeSegment):
                degree[obj.start_node_id] += 1
                degree[obj.end_node_id] += 1
            elif isinstance(obj, SymbolObject):
                degree.update(
                    ref for ref in obj.port_node_ids.values() if ref is not None
                )
        return cls(
            scene=scene,
            by_id={o.id: o for o in scene.objects},
            live=live,
            layers={layer.id: layer for layer in scene.layers},
            degree=degree,
        )

    def live_of(self, kind: type[_T]) -> list[_T]:
        return [o for o in self.live if isinstance(o, kind)]

    def position(self, junction_id: str) -> Point:
        junction = self.by_id[junction_id]
        assert isinstance(junction, Junction)
        return junction.position.x, junction.position.y

    def color(self, obj: SceneObject) -> str:
        return self.layers[obj.layer_id].render_color

    def is_live(self, object_id: str) -> bool:
        obj = self.by_id.get(object_id)
        return obj is not None and obj.interpretation.state != "rejected"


# Groups


def _pipes(view: _View, style: StyleProfile) -> list[str]:
    pipes = view.live_of(PipeSegment)
    lines: list[str] = []
    for layer in sorted(view.scene.layers, key=lambda layer: layer.id):
        children = []
        for pipe in pipes:
            if pipe.layer_id != layer.id:
                continue
            (x1, y1), (x2, y2) = (
                view.position(pipe.start_node_id),
                view.position(pipe.end_node_id),
            )
            children.append(
                _empty(
                    "line",
                    [
                        *_object_attrs(pipe),
                        ("x1", x1),
                        ("y1", y1),
                        ("x2", x2),
                        ("y2", y2),
                    ],
                )
            )
        lines += _wrap(
            "g",
            [
                ("id", LAYER_ID_PREFIX + layer.id),
                ("stroke", layer.render_color),
                ("stroke-width", style.pipe_stroke_width),
                ("stroke-linecap", "round"),
                ("stroke-linejoin", "round"),
            ],
            children,
        )
    return lines


def _connections(view: _View, style: StyleProfile) -> list[str]:
    lines = []
    for junction in view.live_of(Junction):
        dot = [
            ("cx", junction.position.x),
            ("cy", junction.position.y),
            ("r", style.connection_marker_radius),
            ("fill", view.color(junction)),
        ]
        connected = view.degree.get(junction.id, 0) >= 3
        if junction.kind == "unknown":
            # The object element is the ring in the unresolved group.
            if connected:
                lines.append(_empty("circle", dot))
        elif connected:
            lines.append(_empty("circle", [*_object_attrs(junction), *dot]))
        else:
            lines.append(_empty("g", _object_attrs(junction)))
    return lines


def _symbols(view: _View, style: StyleProfile) -> list[str]:
    lines = []
    for symbol in view.live_of(SymbolObject):
        color = view.color(symbol)
        lines.append(
            _empty(
                "use",
                [
                    *_object_attrs(symbol),
                    ("href", f"#{SYMBOL_ID_PREFIX}{symbol.symbol_id}"),
                    ("transform", _symbol_transform(symbol, style)),
                    ("stroke", color),
                    ("stroke-width", style.symbol_stroke_width),
                    ("stroke-linecap", "round"),
                    ("stroke-linejoin", "round"),
                    ("fill", color),
                ],
            )
        )
    return lines


def _dimensions(view: _View, style: StyleProfile) -> list[str]:
    lines = []
    for dim in view.live_of(Dimension):
        start, end = dim.witness_start, dim.witness_end
        mid = _midpoint((start.x, start.y), (end.x, end.y))
        children = [
            _empty(
                "line",
                [
                    ("x1", start.x),
                    ("y1", start.y),
                    ("x2", end.x),
                    ("y2", end.y),
                    ("stroke", style.dimension_color),
                    ("stroke-width", style.dimension_stroke_width),
                    ("marker-start", f"url(#{ARROW_START_ID})"),
                    ("marker-end", f"url(#{ARROW_END_ID})"),
                ],
            ),
            _text(
                "text",
                [
                    ("x", mid[0]),
                    ("y", mid[1]),
                    *_font_attrs(style),
                    ("text-anchor", "middle"),
                ],
                dim.display_text,
            ),
        ]
        lines += _wrap("g", _object_attrs(dim), children)
    return lines


def _callouts(view: _View, style: StyleProfile) -> list[str]:
    lines = []
    relationships = sorted(view.scene.relationships, key=lambda rel: rel.id)
    for rel in relationships:
        if rel.type != "callout_targets" or rel.interpretation.state == "rejected":
            continue
        if not (view.is_live(rel.from_id) and view.is_live(rel.to_id)):
            continue
        source = view.by_id[rel.from_id]
        if not isinstance(source, Annotation):
            continue
        target = _reference_point(view, view.by_id[rel.to_id])
        if target is None:
            continue
        lines.append(
            _empty(
                "line",
                [
                    ("x1", source.anchor.x),
                    ("y1", source.anchor.y),
                    ("x2", target[0]),
                    ("y2", target[1]),
                    ("stroke", style.callout_color),
                    ("stroke-width", style.callout_stroke_width),
                ],
            )
        )
    return lines


def _annotations(view: _View, style: StyleProfile) -> list[str]:
    return [
        _text(
            "text",
            [
                *_object_attrs(note),
                ("data-recognized-text", note.recognized_text),
                ("x", note.anchor.x),
                ("y", note.anchor.y),
                *_font_attrs(style),
            ],
            note.normalized_text,
        )
        for note in view.live_of(Annotation)
    ]


def _unresolved(
    view: _View, library: SymbolLibrary, style: StyleProfile
) -> tuple[list[str], tuple[UnresolvedItem, ...]]:
    ring = [
        ("r", style.unresolved_marker_radius),
        ("stroke", style.unresolved_color),
        ("stroke-width", style.unresolved_stroke_width),
        ("fill", "none"),
    ]
    entries: list[tuple[tuple[str, str], list[str], UnresolvedItem]] = []
    for obj in view.live:
        if isinstance(obj, Junction) and obj.kind == "unknown":
            element = _empty(
                "circle",
                [
                    *_object_attrs(obj),
                    ("cx", obj.position.x),
                    ("cy", obj.position.y),
                    *ring,
                ],
            )
            item = UnresolvedItem(kind="unknown_junction", object_id=obj.id)
            entries.append(((obj.id, ""), [element], item))
        elif isinstance(obj, SymbolObject):
            definition = library.get(obj.symbol_id)
            assert definition is not None
            for port_name in sorted(obj.port_node_ids):
                if obj.port_node_ids[port_name] is not None:
                    continue
                x, y = _port_position(obj, definition, port_name, style)
                element = _empty("circle", [("cx", x), ("cy", y), *ring])
                item = UnresolvedItem(
                    kind="unresolved_port", object_id=obj.id, port=port_name
                )
                entries.append(((obj.id, port_name), [element], item))
        elif isinstance(obj, UnknownMark):
            polygons = [
                _empty("polygon", [("points", _points(points))])
                for points in _mark_polygons(view, obj)
            ]
            group = _wrap(
                "g",
                [
                    *_object_attrs(obj),
                    ("stroke", style.unresolved_color),
                    ("stroke-width", style.unresolved_stroke_width),
                    ("stroke-dasharray", style.unresolved_dasharray),
                    ("fill", "none"),
                ],
                polygons,
            )
            item = UnresolvedItem(kind="unknown_mark", object_id=obj.id)
            entries.append(((obj.id, ""), group, item))
    entries.sort(key=lambda entry: entry[0])
    lines = [line for _, element, _ in entries for line in element]
    return lines, tuple(item for _, _, item in entries)


# Definitions


def _defs(view: _View, library: SymbolLibrary, style: StyleProfile) -> list[str]:
    lines: list[str] = []
    if view.live_of(Dimension):
        lines += _arrow_marker(ARROW_START_ID, style, pointing_back=True)
        lines += _arrow_marker(ARROW_END_ID, style, pointing_back=False)
    used = sorted({symbol.symbol_id for symbol in view.live_of(SymbolObject)})
    for symbol_id in used:
        definition = library.get(symbol_id)
        assert definition is not None
        lines += _wrap(
            "symbol",
            [("id", SYMBOL_ID_PREFIX + symbol_id), ("overflow", "visible")],
            [_primitive(p) for p in definition.primitives],
        )
    return lines


def _arrow_marker(
    marker_id: str, style: StyleProfile, *, pointing_back: bool
) -> list[str]:
    size = style.arrow_size
    s, h = _num(size), _num(size / 2)
    tip = f"M{s} 0L0 {h}L{s} {s}Z" if pointing_back else f"M0 0L{s} {h}L0 {s}Z"
    return _wrap(
        "marker",
        [
            ("id", marker_id),
            ("viewBox", f"0 0 {s} {s}"),
            ("refX", 0.0 if pointing_back else size),
            ("refY", size / 2),
            ("markerWidth", size),
            ("markerHeight", size),
            ("markerUnits", "userSpaceOnUse"),
            ("orient", "auto"),
            ("overflow", "visible"),
        ],
        [_empty("path", [("d", tip), ("fill", style.dimension_color)])],
    )


def _primitive(primitive: SymbolPrimitive) -> str:
    # Stroke and filled color are inherited from the <use>, which carries the
    # layer color, so only unfilled shapes need an explicit fill.
    unfilled = [] if primitive.fill else [("fill", "none")]
    if primitive.kind == "line":
        (x1, y1), (x2, y2) = primitive.points
        return _empty("line", [("x1", x1), ("y1", y1), ("x2", x2), ("y2", y2)])
    if primitive.kind == "circle":
        (cx, cy) = primitive.points[0]
        return _empty(
            "circle", [("cx", cx), ("cy", cy), ("r", primitive.radius), *unfilled]
        )
    return _empty("polygon", [("points", _points(primitive.points)), *unfilled])


# Geometry


def _symbol_transform(symbol: SymbolObject, style: StyleProfile) -> str:
    # SVG rotate() is clockwise on screen because y grows downward, which is
    # the contract's meaning of positive rotationDegrees.
    return (
        f"translate({_num(symbol.anchor.x)} {_num(symbol.anchor.y)}) "
        f"rotate({_num(symbol.rotation_degrees)}) "
        f"scale({_num(style.symbol_scale)})"
    )


def _port_position(
    symbol: SymbolObject,
    definition: SymbolDefinition,
    port_name: str,
    style: StyleProfile,
) -> Point:
    port = definition.port(port_name)
    assert port is not None
    angle = math.radians(symbol.rotation_degrees)
    cos, sin = math.cos(angle), math.sin(angle)
    scale = style.symbol_scale
    return (
        symbol.anchor.x + scale * (port.x * cos - port.y * sin),
        symbol.anchor.y + scale * (port.x * sin + port.y * cos),
    )


def _mark_polygons(view: _View, mark: UnknownMark) -> list[list[Point]]:
    page = view.scene.page
    matrix = page.source_to_page
    polygons = []
    for evidence in mark.interpretation.evidence:
        points = []
        for source in evidence.source_polygon:
            mapped = _apply_homography(matrix, source.x, source.y)
            if mapped is not None:
                points.append(
                    (
                        min(max(mapped[0], 0.0), float(page.width_px)),
                        min(max(mapped[1], 0.0), float(page.height_px)),
                    )
                )
        if len(points) >= 3:
            polygons.append(points)
    return polygons


def _apply_homography(m: Sequence[float], x: float, y: float) -> Point | None:
    w = m[6] * x + m[7] * y + m[8]
    if w == 0:
        return None
    px = (m[0] * x + m[1] * y + m[2]) / w
    py = (m[3] * x + m[4] * y + m[5]) / w
    if not (math.isfinite(px) and math.isfinite(py)):
        return None
    return px, py


def _reference_point(view: _View, obj: SceneObject) -> Point | None:
    if isinstance(obj, Junction):
        return obj.position.x, obj.position.y
    if isinstance(obj, SymbolObject | Annotation):
        return obj.anchor.x, obj.anchor.y
    if isinstance(obj, PipeSegment):
        return _midpoint(
            view.position(obj.start_node_id), view.position(obj.end_node_id)
        )
    if isinstance(obj, Dimension):
        start, end = obj.witness_start, obj.witness_end
        return _midpoint((start.x, start.y), (end.x, end.y))
    polygons = _mark_polygons(view, obj)
    if not polygons:
        return None
    first = polygons[0]
    return (
        sum(x for x, _ in first) / len(first),
        sum(y for _, y in first) / len(first),
    )


def _midpoint(a: Point, b: Point) -> Point:
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


# Serialization


def _num(value: float) -> str:
    """Round to 3 decimals, strip trailing zeros, and write ``-0`` as ``0``."""
    if not math.isfinite(value):
        raise ValueError(f"cannot write non-finite number {value!r} to SVG")
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def _points(points: Sequence[Point]) -> str:
    return " ".join(f"{_num(x)},{_num(y)}" for x, y in points)


def _metadata_json(metadata: ExportMetadata) -> str:
    return json.dumps(
        metadata.to_json_object(), separators=(",", ":"), ensure_ascii=False
    )


def _object_attrs(obj: SceneObject) -> list[tuple[str, str]]:
    return [
        ("id", OBJECT_ID_PREFIX + obj.id),
        ("data-object-id", obj.id),
        ("data-state", obj.interpretation.state),
    ]


def _font_attrs(style: StyleProfile) -> list[tuple[str, str | float]]:
    return [
        ("fill", style.text_color),
        ("font-family", style.font_family),
        ("font-size", style.font_size),
    ]


def _open_tag(tag: str, attrs: Attrs) -> str:
    allowed = ELEMENT_ATTRIBUTES[tag]
    parts = [tag]
    for name, value in attrs:
        if name not in allowed:
            raise ValueError(f"attribute {name!r} is not allowed on <{tag}>")
        text = value if isinstance(value, str) else _num(value)
        parts.append(f'{name}="{escape(text, _ATTR_ENTITIES)}"')
    return " ".join(parts)


def _empty(tag: str, attrs: Attrs) -> str:
    return f"<{_open_tag(tag, attrs)}/>"


def _text(tag: str, attrs: Attrs, content: str) -> str:
    return f"<{_open_tag(tag, attrs)}>{escape(content, _TEXT_ENTITIES)}</{tag}>"


def _wrap(tag: str, attrs: Attrs, children: list[str]) -> list[str]:
    if not children:
        return [_empty(tag, attrs)]
    return [f"<{_open_tag(tag, attrs)}>", *children, f"</{tag}>"]
