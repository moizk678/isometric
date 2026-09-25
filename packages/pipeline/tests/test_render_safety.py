import unittest
from typing import Any

from isometric_pipeline.render.allowlist import SVG_NAMESPACE
from isometric_pipeline.render.errors import RenderError, RenderIssueCode
from isometric_pipeline.render.safety import validate_svg
from isometric_pipeline.render.style import PIPING_DEFAULT
from isometric_pipeline.scene import DrawingScene

Code = RenderIssueCode
IDENTITY = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]


def uid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


LAYER = uid(1)
J1, J2 = uid(11), uid(12)
PIPE = uid(21)
SYMBOL, NOTE, DIM, MARK = uid(31), uid(32), uid(33), uid(34)
EXTRA = uid(99)


def interp(state: str = "machine") -> dict[str, Any]:
    evidence = {
        "sourcePolygon": [xy(10.0, 10.0), xy(20.0, 10.0), xy(15.0, 20.0)],
        "stage": "vectorize",
        "artifactId": "artifact",
        "observations": {},
    }
    return {"state": state, "evidence": [evidence]}


def xy(x: float, y: float) -> dict[str, float]:
    return {"x": x, "y": y}


def obj(type_: str, id_: str, state: str = "machine", **fields: Any) -> dict:
    return {
        "type": type_,
        "id": id_,
        "layerId": LAYER,
        "interpretation": interp(state),
        **fields,
    }


def one_pipe_scene() -> DrawingScene:
    """One pipe between two junctions, plus a symbol, text, and a rejected mark."""
    page = {
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
    }
    objects = [
        obj("junction", J1, position=xy(50.0, 100.0), kind="endpoint"),
        obj("junction", J2, position=xy(150.0, 100.0), kind="endpoint"),
        obj(
            "pipe_segment",
            PIPE,
            startNodeId=J1,
            endNodeId=J2,
            primitive={
                "kind": "line",
                "start": xy(50.0, 100.0),
                "end": xy(150.0, 100.0),
            },
        ),
        obj(
            "symbol",
            SYMBOL,
            symbolId="endpoint",
            anchor=xy(150.0, 100.0),
            rotationDegrees=0.0,
            portNodeIds={"pipe": J2},
        ),
        obj(
            "annotation",
            NOTE,
            recognizedText="6in",
            normalizedText="6 in",
            alternatives=[],
            anchor=xy(100.0, 60.0),
        ),
        obj(
            "dimension",
            DIM,
            displayText="100 mm",
            witnessStart=xy(50.0, 80.0),
            witnessEnd=xy(150.0, 80.0),
            targetObjectIds=[PIPE],
        ),
        obj("unknown_mark", MARK, "rejected", sourceCropId="c", candidateLabels=[]),
    ]
    return DrawingScene.model_validate(
        {
            "schemaVersion": "1.0",
            "documentId": uid(901),
            "revisionId": uid(902),
            "profileId": "piping_isometric",
            "page": page,
            "layers": [
                {
                    "id": LAYER,
                    "name": "piping",
                    "sourceColor": "#000000",
                    "renderColor": "#0000ff",
                }
            ],
            "objects": objects,
            "relationships": [],
        }
    )


SCENE = one_pipe_scene()


def tagged(id_: str) -> str:
    return f'id="obj-{id_}" data-object-id="{id_}" data-state="machine"'


BASE = "\n".join(
    [
        f'<svg xmlns="{SVG_NAMESPACE}" viewBox="0 0 200 200" width="200"'
        ' height="200" font-size="12">',
        '<metadata>{"schemaVersion":"1.0","unresolvedCount":0}</metadata>',
        "<defs>",
        '<marker id="marker-arrow" viewBox="-6 -6 12 12" refX="0" refY="0"'
        ' markerWidth="6" markerHeight="6" markerUnits="userSpaceOnUse"'
        ' orient="auto-start-reverse" overflow="visible">'
        '<path d="M-6 -3 L0 0 L-6 3 z" fill="#1a1a1a"/></marker>',
        '<symbol id="sym-endpoint" overflow="visible">'
        '<circle cx="0" cy="-4" r="4" fill="none"/></symbol>',
        "</defs>",
        f'<g id="pipes"><g id="layer-{LAYER}" stroke="#0000ff" stroke-width="2">',
        f'<line {tagged(PIPE)} x1="50" y1="100" x2="150" y2="100"/>',
        "</g></g>",
        f'<g id="connections"><g {tagged(J1)}/><g {tagged(J2)}/></g>',
        f'<g id="symbols"><use {tagged(SYMBOL)} href="#sym-endpoint"'
        ' transform="translate(150 100) rotate(0) scale(1)"'
        ' stroke="#0000ff" stroke-width="1.5"/></g>',
        f'<g id="dimensions"><g {tagged(DIM)} stroke="#1a1a1a">',
        '<line x1="50" y1="80" x2="150" y2="80" stroke-width="0.75"'
        ' marker-start="url(#marker-arrow)" marker-end="url(#marker-arrow)"/>',
        '<text x="100" y="76" text-anchor="middle" fill="#1a1a1a">100 mm</text>',
        "</g></g>",
        '<g id="callouts"/>',
        f'<g id="annotations"><text {tagged(NOTE)} data-recognized-text="6in"'
        ' x="100" y="60" fill="#1a1a1a">6 in &lt;b&gt;</text></g>',
        '<g id="unresolved"/>',
        "</svg>",
        "",
    ]
)


def mutate(old: str, new: str) -> bytes:
    if old not in BASE:
        raise AssertionError(f"{old!r} is not in the base SVG")
    return BASE.replace(old, new, 1).encode()


def insert(markup: str) -> bytes:
    return mutate('<g id="unresolved"/>', f'<g id="unresolved"/>{markup}')


class SafetyTestCase(unittest.TestCase):
    def issues(self, svg: bytes):
        try:
            validate_svg(svg, SCENE, PIPING_DEFAULT)
        except RenderError as exc:
            return exc.issues
        return ()

    def assertCodes(self, svg: bytes, *expected: RenderIssueCode):
        self.assertEqual([issue.code for issue in self.issues(svg)], list(expected))

    def assertValid(self, svg: bytes) -> None:
        self.assertIsNone(validate_svg(svg, SCENE, PIPING_DEFAULT))


class ValidSvgTest(SafetyTestCase):
    def test_minimal_one_pipe_scene_svg_passes(self):
        self.assertValid(BASE.encode())

    def test_utf8_xml_declaration_is_allowed(self):
        self.assertValid(b'<?xml version="1.0" encoding="UTF-8"?>\n' + BASE.encode())

    def test_endpoint_rounded_to_three_decimals_passes(self):
        self.assertValid(mutate('x1="50"', 'x1="50.001"'))

    def test_coordinates_on_the_margin_edge_pass(self):
        self.assertValid(mutate('x="100" y="60"', 'x="216" y="-16"'))


class XmlTest(SafetyTestCase):
    def test_doctype_entities_and_processing_instructions_are_rejected(self):
        laughs = (
            '<!DOCTYPE svg [<!ENTITY a "aaaaaaaaaa">'
            '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>\n'
        )
        cases = {
            "entity expansion": laughs.encode() + mutate("6 in", "&b;"),
            "external entity": b'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc'
            b'/passwd">]>' + mutate("6 in", "&x;"),
            "external DTD": b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
            b'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">' + BASE.encode(),
            "processing instruction": b'<?xml-stylesheet href="https://evil.ex'
            b'ample/x.css"?>' + BASE.encode(),
            "undefined entity": mutate("6 in", "&xxe;"),
            "latin-1 declaration": b'<?xml version="1.0" encoding="ISO-8859-1"?>'
            + BASE.encode(),
            "truncated": BASE.encode()[:-8],
        }
        for name, svg in cases.items():
            with self.subTest(name):
                issues = self.issues(svg)
                self.assertEqual([i.code for i in issues], [Code.SVG_XML_INVALID])
        self.assertIn("DOCTYPE", self.issues(cases["entity expansion"])[0].message)

    def test_non_svg_namespace_is_rejected(self):
        svg = mutate(f'xmlns="{SVG_NAMESPACE}"', 'xmlns="http://evil.example/ns"')
        self.assertCodes(svg, Code.SVG_XML_INVALID)


class ElementTest(SafetyTestCase):
    def test_script_element(self):
        issues = self.issues(insert("<script>alert(1)</script>"))
        self.assertEqual([i.code for i in issues], [Code.SVG_ELEMENT_FORBIDDEN])
        self.assertEqual(issues[0].path, "/svg/script[1]")

    def test_foreign_object_is_reported_once_for_its_subtree(self):
        markup = (
            '<foreignObject><body xmlns="http://www.w3.org/1999/xhtml">'
            "<script>alert(1)</script></body></foreignObject>"
        )
        self.assertCodes(insert(markup), Code.SVG_ELEMENT_FORBIDDEN)

    def test_other_forbidden_elements(self):
        for markup in (
            '<image href="https://evil.example/x.png"/>',
            '<a href="https://evil.example"><text x="1" y="1">x</text></a>',
            "<style>line{stroke:red}</style>",
            '<animate attributeName="x1" to="0"/>',
            '<set attributeName="href" to="javascript:alert(1)"/>',
            '<svg xmlns="http://www.w3.org/2000/svg"/>',
            '<path d="M0 0 L10 10"/>',
        ):
            with self.subTest(markup):
                self.assertCodes(insert(markup), Code.SVG_ELEMENT_FORBIDDEN)

    def test_preview_only_groups_are_forbidden(self):
        for group in ("paper-overlay", "review-overlay"):
            with self.subTest(group):
                svg = insert(f'<g id="{group}"/>')
                self.assertCodes(svg, Code.SVG_ELEMENT_FORBIDDEN)


class AttributeTest(SafetyTestCase):
    def test_onload_attribute(self):
        svg = mutate("<svg xmlns", '<svg onload="alert(1)" xmlns')
        self.assertCodes(svg, Code.SVG_ATTRIBUTE_FORBIDDEN)

    def test_style_attribute(self):
        svg = mutate('x1="50"', 'style="stroke:url(https://evil.example)" x1="50"')
        self.assertCodes(svg, Code.SVG_ATTRIBUTE_FORBIDDEN)

    def test_xlink_href_is_forbidden(self):
        svg = mutate(
            'href="#sym-endpoint"',
            'xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="#sym-endpoint"',
        )
        self.assertCodes(
            svg, Code.SVG_ATTRIBUTE_FORBIDDEN, Code.SVG_ATTRIBUTE_FORBIDDEN
        )

    def test_unknown_id_prefix_and_data_state(self):
        self.assertCodes(insert('<g id="evil"/>'), Code.SVG_ATTRIBUTE_FORBIDDEN)
        svg = mutate('data-state="machine"', 'data-state="rejected"')
        self.assertCodes(svg, Code.SVG_ATTRIBUTE_FORBIDDEN)


class ReferenceTest(SafetyTestCase):
    def test_remote_href(self):
        svg = mutate(
            'href="#sym-endpoint"', 'href="https://evil.example/s.svg#sym-endpoint"'
        )
        self.assertCodes(svg, Code.SVG_EXTERNAL_REFERENCE)

    def test_javascript_url(self):
        cases = [
            ('href="#sym-endpoint"', 'href="javascript:alert(1)"'),
            (
                'marker-end="url(#marker-arrow)"',
                'marker-end="url(javascript:alert(1))"',
            ),
            (
                'marker-end="url(#marker-arrow)"',
                'marker-end="url(https://evil.example/m.svg#a)"',
            ),
            ('fill="none"', 'fill="url(https://evil.example/p.svg#g)"'),
        ]
        for old, new in cases:
            with self.subTest(new):
                self.assertCodes(mutate(old, new), Code.SVG_EXTERNAL_REFERENCE)

    def test_paint_must_be_none_or_a_hex_color(self):
        for value in (
            "\\75 rl(https://evil.example/p.svg#g)",
            "u\\rl(https://evil.example/p.svg#g)",
            "var(--x)",
            "red",
        ):
            with self.subTest(value):
                svg = mutate('fill="none"', f'fill="{value}"')
                self.assertCodes(svg, Code.SVG_ATTRIBUTE_FORBIDDEN)
        svg = mutate('stroke="#0000ff" stroke-width="2"', 'stroke="\\75 rl(#x)"')
        self.assertCodes(svg, Code.SVG_ATTRIBUTE_FORBIDDEN)
        self.assertValid(mutate('fill="none"', 'fill="#ABC"'))

    def test_local_reference_must_name_a_symbol_or_marker(self):
        for target in ("#pipes", "#sym-missing"):
            with self.subTest(target):
                svg = mutate('href="#sym-endpoint"', f'href="{target}"')
                self.assertCodes(svg, Code.SVG_EXTERNAL_REFERENCE)
        svg = mutate('marker-end="url(#marker-arrow)"', 'marker-end="url(#pipes)"')
        self.assertCodes(svg, Code.SVG_EXTERNAL_REFERENCE)


class BoundsTest(SafetyTestCase):
    def test_nan_and_infinite_coordinates(self):
        for value in ("NaN", "inf", "-Infinity", "1e999", "0x10"):
            with self.subTest(value):
                svg = mutate('x1="50"', f'x1="{value}"')
                self.assertCodes(svg, Code.SVG_OUT_OF_BOUNDS)

    def test_non_finite_numbers_in_other_attributes(self):
        cases = [
            ('r="4"', 'r="NaN"'),
            ("translate(150 100)", "translate(NaN 100)"),
            ('stroke-width="2"', 'stroke-width="inf"'),
        ]
        for old, new in cases:
            with self.subTest(new):
                self.assertCodes(mutate(old, new), Code.SVG_OUT_OF_BOUNDS)

    def test_coordinate_far_outside_the_view_box(self):
        cases = [
            ('x="100" y="60"', 'x="5000" y="60"'),
            ('x="100" y="60"', 'x="100" y="-16.5"'),
            ("translate(150 100)", "translate(5000 100)"),
        ]
        for old, new in cases:
            with self.subTest(new):
                self.assertCodes(mutate(old, new), Code.SVG_OUT_OF_BOUNDS)

    def test_symbol_local_coordinates_are_exempt_from_bounds(self):
        self.assertValid(mutate('cy="-4"', 'cy="-400"'))


class SemanticTest(SafetyTestCase):
    def test_missing_object_id(self):
        start = BASE.index('<g id="annotations">')
        end = BASE.index('<g id="unresolved"/>')
        svg = (BASE[:start] + BASE[end:]).encode()
        issues = self.issues(svg)
        self.assertEqual([i.code for i in issues], [Code.SVG_SEMANTIC_MISMATCH])
        self.assertEqual(issues[0].object_id, NOTE)

    def test_extra_object_id(self):
        issues = self.issues(insert(f"<g {tagged(EXTRA)}/>"))
        self.assertEqual([i.code for i in issues], [Code.SVG_SEMANTIC_MISMATCH])
        self.assertEqual(issues[0].object_id, EXTRA)

    def test_rejected_object_is_an_extra_id(self):
        issues = self.issues(insert(f"<g {tagged(MARK)}/>"))
        self.assertEqual([i.code for i in issues], [Code.SVG_SEMANTIC_MISMATCH])
        self.assertEqual(issues[0].object_id, MARK)

    def test_pipe_endpoint_off_its_junction(self):
        issues = self.issues(mutate('x2="150"', 'x2="149.998"'))
        self.assertEqual([i.code for i in issues], [Code.SVG_SEMANTIC_MISMATCH])
        self.assertEqual(issues[0].object_id, PIPE)

    def test_reversed_pipe_line_matches(self):
        self.assertValid(
            mutate('x1="50" y1="100" x2="150"', 'x1="150" y1="100" x2="50"')
        )

    def test_view_box_must_match_the_page(self):
        svg = mutate('viewBox="0 0 200 200"', 'viewBox="0 0 400 200"')
        self.assertCodes(svg, Code.SVG_SEMANTIC_MISMATCH)

    def test_object_element_id_must_match_data_object_id(self):
        svg = mutate(f'id="obj-{NOTE}"', f'id="obj-{EXTRA}"')
        self.assertCodes(svg, Code.SVG_SEMANTIC_MISMATCH)


class IssueOrderTest(SafetyTestCase):
    def test_all_issues_are_collected_in_document_order(self):
        svg = BASE.replace("<svg xmlns", '<svg onload="x()" xmlns', 1)
        svg = svg.replace('x1="50"', 'style="" x1="50"', 1)
        svg = svg.replace('x="100" y="76"', 'x="5000" y="76"', 1)
        svg = svg.replace('<g id="unresolved"/>', f"<g {tagged(EXTRA)}/>", 1)
        expected = [
            Code.SVG_ATTRIBUTE_FORBIDDEN,
            Code.SVG_ATTRIBUTE_FORBIDDEN,
            Code.SVG_OUT_OF_BOUNDS,
            Code.SVG_SEMANTIC_MISMATCH,
        ]
        first = self.issues(svg.encode())
        self.assertEqual([i.code for i in first], expected)
        self.assertEqual(self.issues(svg.encode()), first)
        self.assertEqual(first[0].path, "/svg")


if __name__ == "__main__":
    unittest.main()
