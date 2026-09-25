"""Safety and semantic validation of rendered SVG bytes.

``validate_svg`` accepts only the vocabulary in ``allowlist.py``. It parses with
expat and refuses DOCTYPE, entity, notation, and processing-instruction events
before expat acts on them, so entity expansion and external fetches never run.
Every issue is collected: first per element in document order, then the
scene-level mismatches.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from xml.parsers import expat

from ..scene import DrawingScene
from .allowlist import (
    ALLOWED_ELEMENTS,
    COORDINATE_ATTRIBUTES,
    DATA_STATES,
    ELEMENT_ATTRIBUTES,
    HREF_ATTRIBUTES,
    HREF_TARGET_ELEMENTS,
    OBJECT_ID_PREFIX,
    PREVIEW_ONLY_GROUP_IDS,
    SVG_NAMESPACE,
    URL_REFERENCE_ATTRIBUTES,
    is_allowed_id,
)
from .errors import RenderError, RenderIssue, RenderIssueCode
from .style import StyleProfile

_Problem = tuple[RenderIssueCode, str]

_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_SEPARATOR = re.compile(r"[\s,]+")
_LOCAL_HREF = re.compile(r"#([A-Za-z0-9_-]+)")
_LOCAL_URL = re.compile(r"url\(#([A-Za-z0-9_-]+)\)")
_TRANSFORM_LIST = re.compile(r"(?:\s*(?:translate|rotate|scale)\s*\([^()]*\)\s*)+")
_TRANSFORM = re.compile(r"(translate|rotate|scale)\s*\(([^()]*)\)")
_TRANSFORM_ARITY = {"translate": (1, 2), "rotate": (1, 3), "scale": (1, 2)}
_PATH_DATA = re.compile(r"[MmLlHhVvZzAaCcSsQqTt0-9eE.,+\-\s]*")
# Paint is parsed as CSS, where an escape such as "\75 rl(" still spells url(.
_PAINT = re.compile(r"none|#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?")
_PAINT_ATTRIBUTES = frozenset({"fill", "stroke"})

_URL_TARGET_ELEMENTS = frozenset({"marker"})
_LOCAL_CONTAINERS = frozenset({"symbol", "marker"})
_Y_COORDINATES = frozenset({"y", "y1", "y2", "cy"})
_NUMBER_ATTRIBUTES = frozenset(
    {
        "r",
        "stroke-width",
        "refX",
        "refY",
        "markerWidth",
        "markerHeight",
        "width",
        "height",
        "font-size",
    }
)
_NON_NEGATIVE = _NUMBER_ATTRIBUTES - {"refX", "refY"}
_LENGTH_ATTRIBUTES = frozenset({"width", "height", "font-size"})

# The renderer rounds to 3 decimals, so a drawn endpoint may be up to 0.0005
# from the junction; the slack absorbs float error in the comparison itself.
_ENDPOINT_TOLERANCE = 0.001 + 1e-9


def validate_svg(svg: bytes, scene: DrawingScene, style: StyleProfile) -> None:
    """Raise ``RenderError`` if ``svg`` is unsafe or does not match ``scene``."""
    elements = _parse(svg)
    issues = _Checker(elements, scene, style).run()
    if issues:
        raise RenderError(issues)


# Parsing


class _Rejected(Exception):
    """A construct refused inside an expat handler, aborting the parse."""


@dataclass(frozen=True)
class _Element:
    name: str
    attributes: tuple[tuple[str, str], ...]
    path: str
    local: bool
    """Inside a ``symbol`` or ``marker``, so coordinates are symbol-local."""
    in_marker: bool
    forbidden: str | None
    """Why the element itself is not allowed, or None."""
    hidden: bool
    """Inside a forbidden element; reported once through that ancestor."""

    def get(self, name: str) -> str | None:
        for key, value in self.attributes:
            if key == name:
                return value
        return None


@dataclass
class _Frame:
    element: _Element
    counts: dict[str, int] = field(default_factory=dict)


class _TreeBuilder:
    def __init__(self) -> None:
        self.elements: list[_Element] = []
        self._stack: list[_Frame] = []

    def start(self, name: str, attributes: list[str]) -> None:
        parent = self._stack[-1] if self._stack else None
        if parent is None:
            path, local, in_marker, hidden = f"/{name}", False, False, False
        else:
            above = parent.element
            index = parent.counts.get(name, 0) + 1
            parent.counts[name] = index
            path = f"{above.path}/{name}[{index}]"
            local = above.local or above.name in _LOCAL_CONTAINERS
            in_marker = above.in_marker or above.name == "marker"
            hidden = above.hidden or above.forbidden is not None
        forbidden = _structure_problem(
            name, is_root=parent is None, in_marker=in_marker
        )
        element = _Element(
            name=name,
            attributes=tuple(zip(attributes[::2], attributes[1::2], strict=True)),
            path=path,
            local=local,
            in_marker=in_marker,
            forbidden=forbidden,
            hidden=hidden,
        )
        self.elements.append(element)
        self._stack.append(_Frame(element))

    def end(self, _name: str) -> None:
        self._stack.pop()


def _structure_problem(name: str, *, is_root: bool, in_marker: bool) -> str | None:
    if name not in ALLOWED_ELEMENTS:
        return f"element <{name}> is not allowed"
    if is_root and name != "svg":
        return f"root element must be <svg>, not <{name}>"
    if not is_root and name == "svg":
        return "nested <svg> is not allowed"
    if name == "path" and not in_marker:
        return "<path> is only allowed inside a <marker>"
    return None


def _refuse(construct: str) -> Callable[..., None]:
    def handler(*_args: object) -> None:
        raise _Rejected(f"{construct} is not allowed")

    return handler


def _check_xml_declaration(
    _version: str, encoding: str | None, _standalone: int
) -> None:
    if encoding is not None and encoding.upper() != "UTF-8":
        raise _Rejected(f"encoding {encoding!r} is not allowed; use UTF-8")


def _parse(svg: bytes) -> list[_Element]:
    parser = expat.ParserCreate()
    parser.ordered_attributes = True
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.StartDoctypeDeclHandler = _refuse("DOCTYPE declaration")
    parser.EntityDeclHandler = _refuse("ENTITY declaration")
    parser.UnparsedEntityDeclHandler = _refuse("ENTITY declaration")
    parser.NotationDeclHandler = _refuse("NOTATION declaration")
    parser.ExternalEntityRefHandler = _refuse("external entity reference")
    parser.ProcessingInstructionHandler = _refuse("processing instruction")
    parser.XmlDeclHandler = _check_xml_declaration
    builder = _TreeBuilder()
    parser.StartElementHandler = builder.start
    parser.EndElementHandler = builder.end
    try:
        parser.Parse(svg, True)
    except _Rejected as exc:
        line, column = parser.CurrentLineNumber, parser.CurrentColumnNumber
        message = f"{exc} (line {line}, column {column})"
    except expat.ExpatError as exc:
        message = str(exc)
    else:
        return builder.elements
    raise RenderError(
        [
            RenderIssue(
                code=RenderIssueCode.SVG_XML_INVALID,
                path="/",
                object_id=None,
                message=message,
            )
        ]
    )


# Numbers


def _number(text: str) -> float | None:
    """A finite number in plain decimal or exponent form, else None."""
    if not _NUMBER.fullmatch(text):
        return None
    value = float(text)
    return value if math.isfinite(value) else None


def _numbers(text: str) -> list[float] | None:
    stripped = text.strip()
    if not stripped:
        return []
    values = [_number(token) for token in _SEPARATOR.split(stripped)]
    if any(value is None for value in values):
        return None
    return [value for value in values if value is not None]


def _show(value: str) -> str:
    shown = repr(value)
    return shown if len(shown) <= 60 else shown[:57] + "..."


# Checks


class _Checker:
    def __init__(
        self, elements: list[_Element], scene: DrawingScene, style: StyleProfile
    ) -> None:
        self.elements = elements
        self.visible = [element for element in elements if not element.hidden]
        self.scene = scene
        self.width = float(scene.page.width_px)
        self.height = float(scene.page.height_px)
        self.margin = style.bounds_margin
        self.issues: list[RenderIssue] = []
        self.targets: dict[str, str] = {}
        for element in self.visible:
            element_id = element.get("id")
            if element.forbidden is None and element_id is not None:
                self.targets.setdefault(element_id, element.name)
        self._seen_ids: set[str] = set()

    def run(self) -> list[RenderIssue]:
        for element in self.visible:
            self._check_element(element)
        if self.elements[0].forbidden is None:
            self._check_view_box(self.elements[0])
            self._check_objects()
        return self.issues

    def _report(
        self, code: RenderIssueCode, element: _Element | None, message: str
    ) -> None:
        self.issues.append(
            RenderIssue(
                code=code,
                path="/svg" if element is None else element.path,
                object_id=None if element is None else element.get("data-object-id"),
                message=message,
            )
        )

    # Per element

    def _check_element(self, element: _Element) -> None:
        if element.forbidden is not None:
            self._report(
                RenderIssueCode.SVG_ELEMENT_FORBIDDEN, element, element.forbidden
            )
            return
        if element.path == "/svg" and element.get("xmlns") is None:
            self._report(
                RenderIssueCode.SVG_XML_INVALID,
                element,
                f"root <svg> must declare xmlns={SVG_NAMESPACE!r}",
            )
        for name, value in element.attributes:
            problem = self._attribute_problem(element, name, value)
            if problem is not None:
                code, message = problem
                self._report(code, element, message)

    def _attribute_problem(
        self, element: _Element, name: str, value: str
    ) -> _Problem | None:
        if name not in ELEMENT_ATTRIBUTES[element.name]:
            return (
                RenderIssueCode.SVG_ATTRIBUTE_FORBIDDEN,
                f"attribute {name!r} is not allowed on <{element.name}>",
            )
        if name in HREF_ATTRIBUTES:
            return self._reference_problem(
                element, name, value, _LOCAL_HREF, HREF_TARGET_ELEMENTS
            )
        if name in URL_REFERENCE_ATTRIBUTES:
            return self._reference_problem(
                element, name, value, _LOCAL_URL, _URL_TARGET_ELEMENTS
            )
        if not name.startswith("data-") and "url(" in value.lower():
            return (
                RenderIssueCode.SVG_EXTERNAL_REFERENCE,
                f"{name}={_show(value)} may not contain url()",
            )
        if name in _PAINT_ATTRIBUTES and not _PAINT.fullmatch(value):
            return (
                RenderIssueCode.SVG_ATTRIBUTE_FORBIDDEN,
                f"{name}={_show(value)} must be 'none' or a #hex color",
            )
        if name == "xmlns" and value != SVG_NAMESPACE:
            return (
                RenderIssueCode.SVG_XML_INVALID,
                f"xmlns must be {SVG_NAMESPACE!r}, not {_show(value)}",
            )
        if name == "id":
            return self._id_problem(element, value)
        if name == "data-state" and value not in DATA_STATES:
            return (
                RenderIssueCode.SVG_ATTRIBUTE_FORBIDDEN,
                f"data-state {_show(value)} is not one of {sorted(DATA_STATES)}",
            )
        if name in COORDINATE_ATTRIBUTES:
            return self._coordinate_problem(element, name, value)
        if name == "transform":
            return self._transform_problem(element, value)
        if name in _NUMBER_ATTRIBUTES:
            return _number_problem(name, value)
        if name == "viewBox":
            values = _numbers(value)
            if values is None or len(values) != 4:
                return (
                    RenderIssueCode.SVG_OUT_OF_BOUNDS,
                    f"viewBox={_show(value)} must be 4 finite numbers",
                )
        if name == "stroke-dasharray" and value != "none":
            values = _numbers(value)
            if not values or any(number < 0 for number in values):
                return (
                    RenderIssueCode.SVG_OUT_OF_BOUNDS,
                    f"stroke-dasharray={_show(value)} must be non-negative "
                    "finite numbers",
                )
        if name == "d":
            return _path_data_problem(value)
        return None

    def _reference_problem(
        self,
        element: _Element,
        name: str,
        value: str,
        pattern: re.Pattern[str],
        targets: frozenset[str],
    ) -> _Problem | None:
        code = RenderIssueCode.SVG_EXTERNAL_REFERENCE
        if element.local:
            # Also rules out reference cycles through symbols and markers.
            return code, f"{name} is not allowed inside <symbol> or <marker>"
        match = pattern.fullmatch(value)
        if match is None:
            return code, f"{name}={_show(value)} is not a local #id reference"
        kinds = " or ".join(f"<{kind}>" for kind in sorted(targets))
        if self.targets.get(match[1]) not in targets:
            return code, f"{name}={_show(value)} does not name a local {kinds}"
        return None

    def _id_problem(self, element: _Element, value: str) -> _Problem | None:
        if value in PREVIEW_ONLY_GROUP_IDS:
            return (
                RenderIssueCode.SVG_ELEMENT_FORBIDDEN,
                f"preview-only group {value!r} is not allowed in an export",
            )
        if not is_allowed_id(value):
            return (
                RenderIssueCode.SVG_ATTRIBUTE_FORBIDDEN,
                f"id {_show(value)} is not a group ID or a known prefix",
            )
        if value in self._seen_ids:
            return RenderIssueCode.SVG_ATTRIBUTE_FORBIDDEN, f"duplicate id {value!r}"
        self._seen_ids.add(value)
        if value.startswith(OBJECT_ID_PREFIX):
            object_id = element.get("data-object-id")
            if object_id != value[len(OBJECT_ID_PREFIX) :]:
                return (
                    RenderIssueCode.SVG_SEMANTIC_MISMATCH,
                    f"id {value!r} does not match data-object-id {object_id!r}",
                )
        return None

    def _coordinate_problem(
        self, element: _Element, name: str, value: str
    ) -> _Problem | None:
        code = RenderIssueCode.SVG_OUT_OF_BOUNDS
        if name == "points":
            values = _numbers(value)
            if not values or len(values) % 2:
                return code, f"points={_show(value)} must be pairs of finite numbers"
            points = list(zip(values[::2], values[1::2], strict=True))
        else:
            number = _number(value)
            if number is None:
                return code, f"{name}={_show(value)} is not a finite number"
            points = [(0.0, number) if name in _Y_COORDINATES else (number, 0.0)]
        if element.local:
            return None
        for x, y in points:
            if not self._inside(x, y):
                return (
                    code,
                    f"{name}={_show(value)} lies outside the viewBox plus the "
                    f"{self.margin:g} px margin",
                )
        return None

    def _transform_problem(self, element: _Element, value: str) -> _Problem | None:
        if not _TRANSFORM_LIST.fullmatch(value):
            return (
                RenderIssueCode.SVG_ATTRIBUTE_FORBIDDEN,
                f"transform={_show(value)} may only use translate, rotate, and scale",
            )
        for position, match in enumerate(_TRANSFORM.finditer(value)):
            kind, arguments = match[1], match[2].strip()
            tokens = _SEPARATOR.split(arguments) if arguments else []
            if len(tokens) not in _TRANSFORM_ARITY[kind]:
                return (
                    RenderIssueCode.SVG_ATTRIBUTE_FORBIDDEN,
                    f"{kind}() in transform={_show(value)} has {len(tokens)} arguments",
                )
            numbers = _numbers(arguments)
            if numbers is None:
                return (
                    RenderIssueCode.SVG_OUT_OF_BOUNDS,
                    f"transform={_show(value)} has a non-finite number",
                )
            # Only a leading translate or rotation center is in page space.
            if element.local or position > 0:
                continue
            if kind == "translate":
                point = (numbers[0], numbers[1] if len(numbers) == 2 else 0.0)
            elif kind == "rotate" and len(numbers) == 3:
                point = (numbers[1], numbers[2])
            else:
                continue
            if not self._inside(*point):
                return (
                    RenderIssueCode.SVG_OUT_OF_BOUNDS,
                    f"transform={_show(value)} lies outside the viewBox plus the "
                    f"{self.margin:g} px margin",
                )
        return None

    def _inside(self, x: float, y: float) -> bool:
        low = -self.margin
        return (
            low <= x <= self.width + self.margin
            and low <= y <= self.height + self.margin
        )

    # Against the scene

    def _check_view_box(self, root: _Element) -> None:
        value = root.get("viewBox")
        expected = [0.0, 0.0, self.width, self.height]
        if value is None:
            self._report(
                RenderIssueCode.SVG_SEMANTIC_MISMATCH, root, "root <svg> has no viewBox"
            )
            return
        values = _numbers(value)
        if values is not None and len(values) == 4 and values != expected:
            self._report(
                RenderIssueCode.SVG_SEMANTIC_MISMATCH,
                root,
                f"viewBox={_show(value)} must be "
                f"'0 0 {self.width:g} {self.height:g}' for this page",
            )

    def _check_objects(self) -> None:
        expected = {
            obj.id: obj
            for obj in self.scene.objects
            if obj.interpretation.state != "rejected"
        }
        found: dict[str, _Element] = {}
        for element in self.visible:
            object_id = element.get("data-object-id")
            if element.forbidden is None and object_id is not None:
                found.setdefault(object_id, element)
        for object_id in sorted(expected.keys() - found.keys()):
            self.issues.append(
                RenderIssue(
                    code=RenderIssueCode.SVG_SEMANTIC_MISMATCH,
                    path="/svg",
                    object_id=object_id,
                    message="scene object has no element with this data-object-id",
                )
            )
        for object_id in sorted(found.keys() - expected.keys()):
            self._report(
                RenderIssueCode.SVG_SEMANTIC_MISMATCH,
                found[object_id],
                f"data-object-id {object_id!r} is not a non-rejected scene object",
            )
        self._check_pipe_lines(expected, found)

    def _check_pipe_lines(self, expected: dict, found: dict[str, _Element]) -> None:
        positions = {
            obj.id: (obj.position.x, obj.position.y)
            for obj in self.scene.objects
            if obj.type == "junction"
        }
        pipes = {
            object_id: obj
            for object_id, obj in expected.items()
            if obj.type == "pipe_segment"
        }
        drawn: set[str] = set()
        for element in self.visible:
            object_id = element.get("data-object-id")
            if element.name != "line" or object_id not in pipes:
                continue
            drawn.add(object_id)
            pipe = pipes[object_id]
            start = positions.get(pipe.start_node_id)
            end = positions.get(pipe.end_node_id)
            if start is None or end is None:
                continue
            raw = [element.get(name) or "" for name in ("x1", "y1", "x2", "y2")]
            if not all(raw):
                self._report(
                    RenderIssueCode.SVG_SEMANTIC_MISMATCH,
                    element,
                    "pipe <line> must set x1, y1, x2, and y2",
                )
                continue
            drawn_at = _numbers(" ".join(raw))
            if drawn_at is None or len(drawn_at) != 4:
                continue  # Already reported as SVG_OUT_OF_BOUNDS.
            if not (_close(drawn_at, start + end) or _close(drawn_at, end + start)):
                self._report(
                    RenderIssueCode.SVG_SEMANTIC_MISMATCH,
                    element,
                    f"pipe endpoints {drawn_at} do not match junctions at "
                    f"{start} and {end}",
                )
        for object_id in sorted((pipes.keys() & found.keys()) - drawn):
            self._report(
                RenderIssueCode.SVG_SEMANTIC_MISMATCH,
                found[object_id],
                "pipe segment is not drawn as a <line>",
            )


def _close(actual: list[float], expected: tuple[float, ...]) -> bool:
    return all(
        abs(value - target) <= _ENDPOINT_TOLERANCE
        for value, target in zip(actual, expected, strict=True)
    )


def _number_problem(name: str, value: str) -> _Problem | None:
    text = value
    if name in _LENGTH_ATTRIBUTES and text.endswith("px"):
        text = text[:-2]
    number = _number(text)
    if number is None or (name in _NON_NEGATIVE and number < 0):
        qualifier = "non-negative " if name in _NON_NEGATIVE else ""
        return (
            RenderIssueCode.SVG_OUT_OF_BOUNDS,
            f"{name}={_show(value)} is not a {qualifier}finite number",
        )
    return None


def _path_data_problem(value: str) -> _Problem | None:
    if not _PATH_DATA.fullmatch(value):
        return (
            RenderIssueCode.SVG_ATTRIBUTE_FORBIDDEN,
            f"path data {_show(value)} has characters outside path commands",
        )
    for token in _NUMBER.findall(value):
        if not math.isfinite(float(token)):
            return (
                RenderIssueCode.SVG_OUT_OF_BOUNDS,
                f"path data {_show(value)} has a non-finite number",
            )
    return None
