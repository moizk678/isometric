import copy
import hashlib
import json
import unittest
import xml.etree.ElementTree as ET
from typing import Any
from unittest import mock
from xml.sax.saxutils import escape

import isometric_pipeline.render.svg as svg_module
from isometric_pipeline.render.allowlist import (
    ELEMENT_ATTRIBUTES,
    GROUP_IDS,
    SVG_NAMESPACE,
)
from isometric_pipeline.render.errors import (
    RenderError,
    RenderIssue,
    RenderIssueCode,
)
from isometric_pipeline.render.style import PIPING_DEFAULT
from isometric_pipeline.render.svg import render_svg
from isometric_pipeline.render.types import (
    SymbolDefinition,
    SymbolLibrary,
    SymbolPort,
    SymbolPrimitive,
    UnresolvedItem,
)
from isometric_pipeline.render.versions import (
    RENDERER_VERSION,
    STYLE_PROFILE_VERSION,
    SYMBOL_LIBRARY_VERSION,
)
from isometric_pipeline.scene import DrawingScene

NS = f"{{{SVG_NAMESPACE}}}"
IDENTITY = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]


def uid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


LAYER, LAYER2 = uid(1), uid(2)
J1, J2, J3, J4, J5 = uid(11), uid(12), uid(13), uid(14), uid(15)
P1, P2, P3, P4 = uid(21), uid(22), uid(23), uid(24)
SYMBOL, NOTE, DIM, MARK = uid(31), uid(32), uid(33), uid(34)
REL, REL2 = uid(41), uid(42)


# Symbol library double built from packages/symbol-library/CONTRACT.md.


def _ports(*ports: tuple[str, float, float, bool]) -> tuple[SymbolPort, ...]:
    return tuple(SymbolPort(n, float(x), float(y), r) for n, x, y, r in ports)


def _line(a, b) -> SymbolPrimitive:
    return SymbolPrimitive("line", (a, b))


CONTRACT_LIBRARY = SymbolLibrary(
    SYMBOL_LIBRARY_VERSION,
    [
        SymbolDefinition(
            "ball_valve",
            "Ball valve",
            _ports(("inlet", -20, 0, True), ("outlet", 20, 0, True)),
            (
                SymbolPrimitive(
                    "polygon",
                    ((-20.0, -10.0), (-20.0, 10.0), (20.0, -10.0), (20.0, 10.0)),
                ),
                SymbolPrimitive("circle", ((0.0, 0.0),), radius=4.0, fill=True),
            ),
        ),
        SymbolDefinition(
            "elbow_fitting",
            "Elbow fitting",
            _ports(("a", -20, 0, True), ("b", 0, -20, True)),
            (_line((-20.0, 0.0), (0.0, 0.0)), _line((0.0, 0.0), (0.0, -20.0))),
        ),
        SymbolDefinition(
            "endpoint",
            "Endpoint",
            _ports(("pipe", 0, 0, True)),
            (_line((0.0, -6.0), (0.0, 6.0)),),
        ),
        SymbolDefinition(
            "tee_fitting",
            "Tee fitting",
            _ports(
                ("run_a", -20, 0, True),
                ("run_b", 20, 0, True),
                ("branch", 0, -20, True),
            ),
            (
                _line((-20.0, 0.0), (20.0, 0.0)),
                _line((0.0, 0.0), (0.0, -20.0)),
                SymbolPrimitive("circle", ((0.0, 0.0),), radius=3.0, fill=True),
            ),
        ),
        SymbolDefinition(
            "unknown",
            "Unknown",
            _ports(
                ("port_1", -20, 0, False),
                ("port_2", 0, -20, False),
                ("port_3", 20, 0, False),
                ("port_4", 0, 20, False),
            ),
            (
                SymbolPrimitive(
                    "polygon",
                    ((-12.0, -12.0), (12.0, -12.0), (12.0, 12.0), (-12.0, 12.0)),
                ),
            ),
        ),
    ],
)


def fake_load_symbol_library(version: str) -> SymbolLibrary:
    if version != SYMBOL_LIBRARY_VERSION:
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
    return CONTRACT_LIBRARY


# Inline scene builders.


def xy(x: float, y: float) -> dict[str, float]:
    return {"x": x, "y": y}


def evidence(points=((10.0, 10.0), (20.0, 10.0), (15.0, 20.0))) -> dict[str, Any]:
    return {
        "sourcePolygon": [xy(x, y) for x, y in points],
        "stage": "vectorize",
        "artifactId": "artifact",
        "observations": {"confidence": 0.9},
    }


def interp(state: str = "machine", *, evidence_list=None) -> dict[str, Any]:
    return {
        "state": state,
        "evidence": [evidence()] if evidence_list is None else evidence_list,
    }


def junction(id_: str, x: float, y: float, kind: str = "endpoint") -> dict[str, Any]:
    return {
        "type": "junction",
        "id": id_,
        "layerId": LAYER,
        "position": xy(x, y),
        "kind": kind,
        "interpretation": interp(),
    }


def pipe(id_: str, start: dict, end: dict, layer: str = LAYER) -> dict[str, Any]:
    """A pipe between two junction dicts, with its primitive on their positions."""
    return {
        "type": "pipe_segment",
        "id": id_,
        "layerId": layer,
        "startNodeId": start["id"],
        "endNodeId": end["id"],
        "primitive": {
            "kind": "line",
            "start": dict(start["position"]),
            "end": dict(end["position"]),
        },
        "interpretation": interp(),
    }


def symbol(
    symbol_id: str,
    ports: dict[str, str | None],
    anchor=(100.0, 100.0),
    rotation: float = 0.0,
) -> dict[str, Any]:
    return {
        "type": "symbol",
        "id": SYMBOL,
        "layerId": LAYER,
        "symbolId": symbol_id,
        "anchor": xy(*anchor),
        "rotationDegrees": rotation,
        "portNodeIds": ports,
        "interpretation": interp(),
    }


def annotation(normalized: str = "6in", recognized: str | None = None):
    return {
        "type": "annotation",
        "id": NOTE,
        "layerId": LAYER,
        "recognizedText": normalized if recognized is None else recognized,
        "normalizedText": normalized,
        "alternatives": [],
        "anchor": xy(100.0, 60.0),
        "interpretation": interp(),
    }


def dimension() -> dict[str, Any]:
    return {
        "type": "dimension",
        "id": DIM,
        "layerId": LAYER,
        "displayText": "100 mm",
        "witnessStart": xy(50.0, 80.0),
        "witnessEnd": xy(150.0, 80.0),
        "targetObjectIds": [],
        "interpretation": interp(),
    }


def mark(interpretation=None) -> dict[str, Any]:
    return {
        "type": "unknown_mark",
        "id": MARK,
        "layerId": LAYER,
        "sourceCropId": "crop-1",
        "candidateLabels": ["flange"],
        "interpretation": interpretation or interp(),
    }


def callout(to_id: str, id_: str = REL) -> dict[str, Any]:
    return {
        "id": id_,
        "type": "callout_targets",
        "fromId": NOTE,
        "toId": to_id,
        "interpretation": interp(),
    }


def route() -> list[dict[str, Any]]:
    a, b = junction(J1, 50.0, 100.0), junction(J2, 150.0, 100.0)
    return [a, b, pipe(P1, a, b)]


def scene(objects=None, relationships=(), **page: Any) -> DrawingScene:
    return DrawingScene.model_validate(
        {
            "schemaVersion": "1.0",
            "documentId": uid(901),
            "revisionId": uid(902),
            "profileId": "piping_isometric",
            "page": {
                "sourceWidthPx": 200,
                "sourceHeightPx": 200,
                "displayWidthPx": 200,
                "displayHeightPx": 200,
                "widthPx": 200,
                "heightPx": 200,
                "sourceToDisplay": IDENTITY,
                "displayToSource": IDENTITY,
                "sourceToPage": IDENTITY,
                "pageToSource": IDENTITY,
                **page,
            },
            "layers": [
                {
                    "id": LAYER,
                    "name": "piping",
                    "sourceColor": "#000000",
                    "renderColor": "#0000ff",
                },
                {
                    "id": LAYER2,
                    "name": "notes",
                    "sourceColor": "#ff0000",
                    "renderColor": "#cc0000",
                },
            ],
            "objects": route() if objects is None else list(objects),
            "relationships": list(relationships),
        }
    )


def everything_scene() -> DrawingScene:
    objects = route() + [
        symbol("ball_valve", {"inlet": J1, "outlet": None}, anchor=(70.0, 100.0)),
        annotation("NOTE 1"),
        dimension(),
        mark(),
    ]
    return scene(objects, [callout(J2)])


# Helpers over parsed output.


def render(value: DrawingScene):
    return render_svg(value, SYMBOL_LIBRARY_VERSION, STYLE_PROFILE_VERSION)


def parse(result) -> ET.Element:
    return ET.fromstring(result.svg)


def local(element: ET.Element) -> str:
    return element.tag.removeprefix(NS)


def group(root: ET.Element, group_id: str) -> ET.Element:
    for child in root:
        if local(child) == "g" and child.get("id") == group_id:
            return child
    raise AssertionError(f"group {group_id!r} not found")


def find_all(root: ET.Element, tag: str) -> list[ET.Element]:
    return list(root.iter(NS + tag))


def by_object_id(root: ET.Element, object_id: str) -> list[ET.Element]:
    return [e for e in root.iter() if e.get("data-object-id") == object_id]


class RenderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.object(
            svg_module, "load_symbol_library", fake_load_symbol_library
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class DeterminismTest(RenderTestCase):
    def test_double_render_is_byte_identical(self):
        first = render(everything_scene())
        second = render(everything_scene())
        self.assertEqual(first.svg, second.svg)
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(first.sha256, hashlib.sha256(first.svg).hexdigest())
        self.assertEqual(first.unresolved, second.unresolved)

    def test_input_object_order_does_not_change_output(self):
        value = everything_scene()
        shuffled = copy.deepcopy(value)
        shuffled.objects.reverse()
        shuffled.layers.reverse()
        self.assertEqual(render(value).svg, render(shuffled).svg)

    def test_output_is_utf8_with_lf_and_no_declaration(self):
        svg = render(everything_scene()).svg
        text = svg.decode("utf-8")
        self.assertNotIn("\r", text)
        self.assertTrue(text.endswith("</svg>\n"))
        self.assertTrue(text.startswith("<svg "))


class StructureTest(RenderTestCase):
    def test_only_allowlisted_elements_and_attributes(self):
        root = parse(render(everything_scene()))
        for element in root.iter():
            tag = local(element)
            self.assertIn(tag, ELEMENT_ATTRIBUTES)
            for name in element.attrib:
                self.assertIn(name, ELEMENT_ATTRIBUTES[tag], f"{name} on <{tag}>")

    def test_root_viewbox_and_group_order(self):
        root = parse(render(scene(route())))
        self.assertEqual(root.get("viewBox"), "0 0 200 200")
        children = list(root)
        self.assertEqual([local(c) for c in children[:2]], ["metadata", "defs"])
        self.assertEqual(tuple(c.get("id") for c in children[2:]), GROUP_IDS)

    def test_metadata_is_compact_json_in_fixed_order(self):
        result = render(everything_scene())
        root = parse(result)
        text = root.find(NS + "metadata").text
        self.assertEqual(
            text, json.dumps(result.metadata.to_json_object(), separators=(",", ":"))
        )
        self.assertEqual(
            list(json.loads(text)),
            [
                "schemaVersion",
                "documentId",
                "revisionId",
                "rendererVersion",
                "symbolLibraryVersion",
                "styleProfileVersion",
                "unresolvedCount",
            ],
        )
        self.assertEqual(result.metadata.renderer_version, RENDERER_VERSION)
        self.assertEqual(result.metadata.document_id, uid(901))
        self.assertEqual(result.metadata.unresolved_count, len(result.unresolved))
        self.assertNotIn("://", text)

    def test_pipes_are_grouped_by_sorted_layer_with_render_color(self):
        a, b, c = (
            junction(J1, 50.0, 100.0),
            junction(J2, 150.0, 100.0),
            junction(J3, 150.0, 20.0),
        )
        objects = [a, b, c, pipe(P2, b, c, layer=LAYER2), pipe(P1, a, b)]
        pipes = group(parse(render(scene(objects))), "pipes")
        layers = list(pipes)
        self.assertEqual(
            [g.get("id") for g in layers], [f"layer-{LAYER}", f"layer-{LAYER2}"]
        )
        self.assertEqual([g.get("stroke") for g in layers], ["#0000ff", "#cc0000"])
        self.assertEqual([e.get("data-object-id") for e in layers[0]], [P1])
        self.assertEqual([e.get("data-object-id") for e in layers[1]], [P2])

    def test_pipe_line_is_drawn_between_junction_positions(self):
        root = parse(render(scene(route())))
        (line,) = by_object_id(root, P1)
        self.assertEqual(local(line), "line")
        self.assertEqual(
            [line.get(k) for k in ("x1", "y1", "x2", "y2")],
            ["50", "100", "150", "100"],
        )
        self.assertEqual(line.get("id"), f"obj-{P1}")
        self.assertEqual(line.get("data-state"), "machine")

    def test_every_live_object_has_exactly_one_addressable_element(self):
        value = everything_scene()
        root = parse(render(value))
        for obj in value.objects:
            with self.subTest(type=obj.type):
                elements = by_object_id(root, obj.id)
                self.assertEqual(len(elements), 1)
                self.assertEqual(elements[0].get("id"), f"obj-{obj.id}")

    def test_rejected_object_is_omitted(self):
        objects = route() + [annotation("gone")]
        objects[3]["interpretation"] = interp("rejected")
        result = render(scene(objects))
        self.assertNotIn(NOTE, result.svg.decode("utf-8"))
        self.assertNotIn(b"gone", result.svg)


class JunctionTest(RenderTestCase):
    def test_structural_elbow_and_tee_emit_no_symbol(self):
        tee = junction(J1, 100.0, 100.0, "tee")
        left = junction(J2, 40.0, 100.0, "elbow")
        right = junction(J3, 160.0, 100.0)
        up = junction(J4, 100.0, 40.0)
        down = junction(J5, 40.0, 160.0)
        objects = [
            tee,
            left,
            right,
            up,
            down,
            pipe(P1, left, tee),
            pipe(P2, tee, right),
            pipe(P3, tee, up),
            pipe(P4, down, left),
        ]
        result = render(scene(objects))
        root = parse(result)
        self.assertNotIn(b"<use", result.svg)
        self.assertEqual(find_all(root, "use"), [])
        self.assertEqual(find_all(root, "symbol"), [])
        (elbow,) = by_object_id(root, J2)
        self.assertEqual(local(elbow), "g")
        self.assertEqual(len(elbow), 0)
        (dot,) = by_object_id(root, J1)
        self.assertEqual(local(dot), "circle")

    def test_unconnected_crossing_has_no_marker(self):
        west, east = junction(J1, 20.0, 100.0), junction(J2, 180.0, 100.0)
        north, south = junction(J3, 100.0, 20.0), junction(J4, 100.0, 180.0)
        objects = [
            west,
            east,
            north,
            south,
            pipe(P1, west, east),
            pipe(P2, north, south),
        ]
        root = parse(render(scene(objects)))
        at_crossing = [
            c
            for c in find_all(root, "circle")
            if (c.get("cx"), c.get("cy")) == ("100", "100")
        ]
        self.assertEqual(at_crossing, [])
        self.assertEqual(find_all(group(root, "connections"), "circle"), [])

    def test_connected_degree_four_junction_has_dot(self):
        center = junction(J5, 100.0, 100.0, "crossing")
        ends = [
            junction(J1, 20.0, 100.0),
            junction(J2, 180.0, 100.0),
            junction(J3, 100.0, 20.0),
            junction(J4, 100.0, 180.0),
        ]
        pipes = [
            pipe(p, end, center) for p, end in zip((P1, P2, P3, P4), ends, strict=True)
        ]
        root = parse(render(scene([center, *ends, *pipes])))
        dots = find_all(group(root, "connections"), "circle")
        self.assertEqual(len(dots), 1)
        (dot,) = dots
        self.assertEqual(dot.get("data-object-id"), J5)
        self.assertEqual((dot.get("cx"), dot.get("cy")), ("100", "100"))
        self.assertEqual(dot.get("r"), "3")
        self.assertEqual(dot.get("fill"), "#0000ff")

    def test_rejected_pipe_does_not_count_toward_degree(self):
        center = junction(J4, 100.0, 100.0, "tee")
        ends = [
            junction(J1, 20.0, 100.0),
            junction(J2, 180.0, 100.0),
            junction(J3, 100.0, 20.0),
        ]
        pipes = [
            pipe(p, end, center) for p, end in zip((P1, P2, P3), ends, strict=True)
        ]
        pipes[2]["interpretation"] = interp("rejected")
        root = parse(render(scene([center, *ends, *pipes])))
        self.assertEqual(find_all(group(root, "connections"), "circle"), [])

    def test_unknown_junction_gets_unresolved_ring(self):
        objects = route()
        objects[1]["kind"] = "unknown"
        result = render(scene(objects))
        root = parse(result)
        (ring,) = by_object_id(root, J2)
        self.assertIn(ring, list(group(root, "unresolved")))
        self.assertEqual(local(ring), "circle")
        self.assertEqual(ring.get("fill"), "none")
        self.assertEqual(ring.get("stroke"), PIPING_DEFAULT.unresolved_color)
        self.assertEqual(ring.get("r"), "5")
        self.assertEqual((ring.get("cx"), ring.get("cy")), ("150", "100"))
        self.assertEqual(result.unresolved, (UnresolvedItem("unknown_junction", J2),))
        self.assertEqual(result.metadata.unresolved_count, 1)


class SymbolTest(RenderTestCase):
    def tee_fitting_scene(self) -> DrawingScene:
        run_a, run_b = junction(J1, 80.0, 100.0), junction(J2, 120.0, 100.0)
        branch = junction(J3, 100.0, 80.0)
        west, east = junction(J4, 40.0, 100.0), junction(J5, 160.0, 100.0)
        objects = [
            run_a,
            run_b,
            branch,
            west,
            east,
            pipe(P1, west, run_a),
            pipe(P2, run_b, east),
            symbol("tee_fitting", {"run_a": J1, "run_b": J2, "branch": J3}),
        ]
        return scene(objects)

    def test_explicit_tee_fitting_emits_exactly_one_use(self):
        result = render(self.tee_fitting_scene())
        root = parse(result)
        uses = find_all(root, "use")
        self.assertEqual(len(uses), 1)
        (use,) = uses
        self.assertEqual(use.get("href"), "#sym-tee_fitting")
        self.assertEqual(use.get("data-object-id"), SYMBOL)
        self.assertEqual(use.get("transform"), "translate(100 100) rotate(0) scale(1)")
        defs = [s.get("id") for s in find_all(root, "symbol")]
        self.assertEqual(defs, ["sym-tee_fitting"])
        self.assertEqual(find_all(root, "symbol")[0].get("overflow"), "visible")
        self.assertEqual(find_all(group(root, "connections"), "circle"), [])

    def test_null_port_gets_ring_at_rotated_port_position(self):
        inlet, far = junction(J1, 100.0, 80.0), junction(J2, 100.0, 20.0)
        objects = [
            inlet,
            far,
            pipe(P1, far, inlet),
            symbol("ball_valve", {"inlet": J1, "outlet": None}, rotation=90.0),
        ]
        result = render(scene(objects))
        root = parse(result)
        (use,) = find_all(root, "use")
        self.assertEqual(use.get("transform"), "translate(100 100) rotate(90) scale(1)")
        rings = find_all(group(root, "unresolved"), "circle")
        self.assertEqual(len(rings), 1)
        (ring,) = rings
        # Outlet is at local (20, 0); clockwise 90 degrees lands below the anchor.
        self.assertEqual((ring.get("cx"), ring.get("cy")), ("100", "120"))
        self.assertEqual(ring.get("fill"), "none")
        self.assertIsNone(ring.get("data-object-id"))
        self.assertEqual(
            result.unresolved,
            (UnresolvedItem("unresolved_port", SYMBOL, "outlet"),),
        )

    def test_symbol_primitives_inherit_color_and_unfilled_shapes_have_none(self):
        objects = route() + [
            symbol("ball_valve", {"inlet": J1, "outlet": None}, anchor=(70.0, 100.0))
        ]
        root = parse(render(scene(objects)))
        (definition,) = find_all(root, "symbol")
        polygon, circle = list(definition)
        self.assertEqual(polygon.get("fill"), "none")
        self.assertIsNone(circle.get("fill"))
        self.assertIsNone(polygon.get("stroke"))
        (use,) = find_all(root, "use")
        self.assertEqual(use.get("stroke"), "#0000ff")
        self.assertEqual(use.get("fill"), "#0000ff")


class TextTest(RenderTestCase):
    def test_xml_metacharacters_cannot_inject_markup(self):
        normalized = '<script>alert("x")</script> & </text><g id="evil"/>'
        recognized = "a\"b<c>&d'e\n\r\tf"
        result = render(scene(route() + [annotation(normalized, recognized)]))
        root = parse(result)
        self.assertEqual(find_all(root, "script"), [])
        self.assertFalse([e for e in root.iter() if e.get("id") == "evil"])
        notes = list(group(root, "annotations"))
        self.assertEqual(len(notes), 1)
        (text,) = notes
        self.assertEqual(local(text), "text")
        self.assertEqual(len(text), 0)
        self.assertEqual(text.text, normalized)
        self.assertEqual(text.get("data-recognized-text"), recognized)
        self.assertIn(escape(normalized), result.svg.decode("utf-8"))

    def test_carriage_return_in_text_round_trips(self):
        text_value = "line 1\r\nline 2"
        root = parse(render(scene(route() + [annotation(text_value)])))
        (text,) = list(group(root, "annotations"))
        self.assertEqual(text.text, text_value)

    def test_dimension_has_arrow_markers_and_midpoint_text(self):
        root = parse(render(scene(route() + [dimension()])))
        (dim,) = by_object_id(root, DIM)
        line, text = list(dim)
        self.assertEqual(line.get("marker-start"), "url(#marker-arrow-start)")
        self.assertEqual(line.get("marker-end"), "url(#marker-arrow-end)")
        self.assertEqual((text.get("x"), text.get("y")), ("100", "80"))
        self.assertEqual(text.text, "100 mm")
        markers = [m.get("id") for m in find_all(root, "marker")]
        self.assertEqual(markers, ["marker-arrow-start", "marker-arrow-end"])

    def test_no_markers_without_dimensions(self):
        root = parse(render(scene(route())))
        self.assertEqual(find_all(root, "marker"), [])

    def test_callout_line_runs_from_annotation_to_target(self):
        objects = route() + [annotation()]
        root = parse(render(scene(objects, [callout(J1), callout(P1, id_=REL2)])))
        lines = find_all(group(root, "callouts"), "line")
        coords = [tuple(e.get(k) for k in ("x1", "y1", "x2", "y2")) for e in lines]
        self.assertEqual(
            coords, [("100", "60", "50", "100"), ("100", "60", "100", "100")]
        )

    def test_callout_to_rejected_target_is_skipped(self):
        objects = route() + [annotation()]
        objects[0]["interpretation"] = interp("rejected")
        root = parse(render(scene(objects, [callout(J1)])))
        self.assertEqual(list(group(root, "callouts")), [])


class UnknownMarkTest(RenderTestCase):
    def test_polygon_is_mapped_through_source_to_page_and_clamped(self):
        forward = [0.5, 0.0, 10.0, 0.0, 0.5, -4.0, 0.0, 0.0, 1.0]
        inverse = [2.0, 0.0, -20.0, 0.0, 2.0, 8.0, 0.0, 0.0, 1.0]
        polygon = evidence(((10.0, 4.0), (20.0, 10.0), (15.0, 20.0)))
        objects = route() + [mark(interp(evidence_list=[polygon]))]
        result = render(scene(objects, sourceToPage=forward, pageToSource=inverse))
        root = parse(result)
        (group_el,) = by_object_id(root, MARK)
        self.assertIn(group_el, list(group(root, "unresolved")))
        self.assertEqual(group_el.get("stroke-dasharray"), "4 2")
        self.assertEqual(group_el.get("fill"), "none")
        (poly,) = list(group_el)
        self.assertEqual(poly.get("points"), "15,0 20,1 17.5,6")
        self.assertEqual(result.unresolved, (UnresolvedItem("unknown_mark", MARK),))

    def test_mark_without_evidence_stays_addressable(self):
        objects = route() + [mark(interp("confirmed", evidence_list=[]))]
        root = parse(render(scene(objects)))
        (element,) = by_object_id(root, MARK)
        self.assertEqual(local(element), "g")
        self.assertEqual(len(element), 0)


class ErrorTest(RenderTestCase):
    def test_unknown_style_version(self):
        with self.assertRaises(RenderError) as caught:
            render_svg(scene(), SYMBOL_LIBRARY_VERSION, "piping-default@9.9.9")
        self.assertEqual(caught.exception.codes, (RenderIssueCode.VERSION_UNSUPPORTED,))

    def test_unknown_symbol_library_version(self):
        with self.assertRaises(RenderError) as caught:
            render_svg(scene(), "piping-symbols@9.9.9", STYLE_PROFILE_VERSION)
        self.assertEqual(caught.exception.codes, (RenderIssueCode.VERSION_UNSUPPORTED,))

    def test_invalid_scene_wraps_every_scene_issue(self):
        objects = route()
        objects[2]["primitive"]["start"] = xy(51.0, 100.0)
        objects.append(symbol("mystery_valve", {"inlet": J1}))
        with self.assertRaises(RenderError) as caught:
            render(scene(objects))
        error = caught.exception
        self.assertEqual(
            error.codes,
            (RenderIssueCode.SCENE_INVALID, RenderIssueCode.SCENE_INVALID),
        )
        self.assertIn("PIPE_ENDPOINT_MISMATCH", str(error))
        self.assertIn("UNKNOWN_REFERENCE", str(error))
        self.assertEqual(error.issues[0].path, "objects[2].primitive.start")
        self.assertEqual(error.issues[0].object_id, P1)


class NumberFormatTest(unittest.TestCase):
    def test_rounding_and_trailing_zeros(self):
        cases = [
            (1.0, "1"),
            (1.5, "1.5"),
            (-0.0004, "0"),
            (-0.0, "0"),
            (0.0, "0"),
            (100, "100"),
            (12.34567, "12.346"),
            (-2.5, "-2.5"),
            (0.1 + 0.2, "0.3"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(svg_module._num(value), expected)

    def test_non_finite_is_rejected(self):
        with self.assertRaises(ValueError):
            svg_module._num(float("nan"))


if __name__ == "__main__":
    unittest.main()
