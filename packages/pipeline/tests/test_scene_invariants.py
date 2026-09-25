import math
import unittest
from typing import Any

from isometric_pipeline.scene import (
    DrawingScene,
    IssueCode,
    SceneValidationError,
    validate_scene,
)
from pydantic import ValidationError

IDENTITY = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
ZERO = [0.0] * 9


def uid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


LAYER = uid(1)
J1, J2, J3, J4 = uid(11), uid(12), uid(13), uid(14)
PIPE, PIPE2 = uid(21), uid(22)
SYMBOL, NOTE, DIM, MARK = uid(31), uid(32), uid(33), uid(34)
REL, REL2 = uid(41), uid(42)


def evidence(points=((10.0, 10.0), (20.0, 10.0), (15.0, 20.0))) -> dict[str, Any]:
    return {
        "sourcePolygon": [{"x": x, "y": y} for x, y in points],
        "stage": "vectorize",
        "artifactId": "artifact",
        "observations": {"confidence": 0.9},
    }


def interp(state: str = "machine", *, with_evidence: bool = True) -> dict[str, Any]:
    return {"state": state, "evidence": [evidence()] if with_evidence else []}


def xy(x: float, y: float) -> dict[str, float]:
    return {"x": x, "y": y}


def junction(id_: str, x: float, y: float) -> dict[str, Any]:
    return {
        "type": "junction",
        "id": id_,
        "layerId": LAYER,
        "position": xy(x, y),
        "kind": "endpoint",
        "interpretation": interp(),
    }


def pipe(id_: str, start_id: str, end_id: str, start, end) -> dict[str, Any]:
    return {
        "type": "pipe_segment",
        "id": id_,
        "layerId": LAYER,
        "startNodeId": start_id,
        "endNodeId": end_id,
        "primitive": {"kind": "line", "start": xy(*start), "end": xy(*end)},
        "interpretation": interp(),
    }


def symbol(ports: dict[str, str | None], symbol_id: str = "valve") -> dict[str, Any]:
    return {
        "type": "symbol",
        "id": SYMBOL,
        "layerId": LAYER,
        "symbolId": symbol_id,
        "anchor": xy(100.0, 100.0),
        "rotationDegrees": 0.0,
        "portNodeIds": ports,
        "interpretation": interp(),
    }


def annotation(text: str = "6in", target: str | None = None) -> dict[str, Any]:
    obj = {
        "type": "annotation",
        "id": NOTE,
        "layerId": LAYER,
        "recognizedText": text,
        "normalizedText": text,
        "alternatives": [],
        "anchor": xy(100.0, 60.0),
        "interpretation": interp(),
    }
    if target is not None:
        obj["targetObjectId"] = target
    return obj


def dimension(targets: list[str]) -> dict[str, Any]:
    return {
        "type": "dimension",
        "id": DIM,
        "layerId": LAYER,
        "displayText": "100 mm",
        "witnessStart": xy(50.0, 80.0),
        "witnessEnd": xy(150.0, 80.0),
        "targetObjectIds": targets,
        "interpretation": interp(),
    }


def mark(id_: str = MARK) -> dict[str, Any]:
    return {
        "type": "unknown_mark",
        "id": id_,
        "layerId": LAYER,
        "sourceCropId": "crop-1",
        "candidateLabels": ["flange"],
        "interpretation": interp(),
    }


def rel(type_: str, from_id: str, to_id: str, id_: str = REL) -> dict[str, Any]:
    return {
        "id": id_,
        "type": type_,
        "fromId": from_id,
        "toId": to_id,
        "interpretation": interp(),
    }


def route() -> list[dict[str, Any]]:
    """Two junctions joined by one horizontal pipe."""
    return [
        junction(J1, 50.0, 100.0),
        junction(J2, 150.0, 100.0),
        pipe(PIPE, J1, J2, (50.0, 100.0), (150.0, 100.0)),
    ]


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
                }
            ],
            "objects": route() if objects is None else list(objects),
            "relationships": list(relationships),
        }
    )


class FakeCatalog:
    def __init__(self, symbols: dict[str, tuple[set[str], set[str]]]) -> None:
        self.symbols = symbols
        self.calls: list[str] = []

    def port_names(self, symbol_id: str) -> frozenset[str] | None:
        self.calls.append(symbol_id)
        entry = self.symbols.get(symbol_id)
        return None if entry is None else frozenset(entry[0])

    def required_ports(self, symbol_id: str) -> frozenset[str]:
        return frozenset(self.symbols[symbol_id][1])


VALVE_CATALOG = {"valve": ({"inlet", "outlet"}, {"inlet", "outlet"})}


class InvariantTestCase(unittest.TestCase):
    def issues(self, value: DrawingScene, **kwargs: Any):
        try:
            validate_scene(value, **kwargs)
        except SceneValidationError as exc:
            return exc.issues
        return ()

    def codes(self, value: DrawingScene, **kwargs: Any) -> list[IssueCode]:
        return [issue.code for issue in self.issues(value, **kwargs)]

    def assertValid(self, value: DrawingScene, **kwargs: Any) -> None:
        self.assertIsNone(validate_scene(value, **kwargs))

    def assertCodes(self, value: DrawingScene, *expected: IssueCode, **kwargs):
        self.assertEqual(self.codes(value, **kwargs), list(expected))


class ValidScenesTest(InvariantTestCase):
    def test_connected_route_is_valid(self):
        self.assertValid(scene())

    def test_unconnected_crossing_stays_valid(self):
        crossing = scene(
            [
                junction(J1, 20.0, 100.0),
                junction(J2, 180.0, 100.0),
                junction(J3, 100.0, 20.0),
                junction(J4, 100.0, 180.0),
                pipe(PIPE, J1, J2, (20.0, 100.0), (180.0, 100.0)),
                pipe(PIPE2, J3, J4, (100.0, 20.0), (100.0, 180.0)),
            ]
        )
        self.assertValid(crossing)
        node_ids = {
            (obj.start_node_id, obj.end_node_id)
            for obj in crossing.objects
            if obj.type == "pipe_segment"
        }
        self.assertEqual(node_ids, {(J1, J2), (J3, J4)})

    def test_points_on_the_page_edge_are_in_bounds(self):
        objects = route() + [junction(J3, 0.0, 200.0)]
        objects[0]["interpretation"]["evidence"] = [
            evidence(((0.0, 0.0), (200.0, 0.0), (200.0, 200.0)))
        ]
        self.assertValid(scene(objects))


class NumberAndCoordinateTest(InvariantTestCase):
    def test_non_finite_point_is_reported_without_follow_on_issues(self):
        value = scene()
        value.objects[0].position.x = math.nan
        self.assertCodes(value, IssueCode.NON_FINITE_NUMBER)

    def test_non_finite_transform_skips_transform_checks(self):
        value = scene()
        value.page.source_to_page[0] = math.inf
        self.assertCodes(value, IssueCode.NON_FINITE_NUMBER)

    def test_non_finite_score_and_observation(self):
        value = scene()
        value.objects[0].interpretation.score = math.nan
        value.objects[1].interpretation.evidence[0].observations["c"] = -math.inf
        self.assertCodes(
            value, IssueCode.NON_FINITE_NUMBER, IssueCode.NON_FINITE_NUMBER
        )

    def test_page_point_outside_page(self):
        objects = route() + [annotation()]
        objects[3]["anchor"] = xy(201.0, 10.0)
        issues = self.issues(scene(objects))
        self.assertEqual([i.code for i in issues], [IssueCode.COORDINATE_OUT_OF_BOUNDS])
        self.assertEqual(issues[0].path, "objects[3].anchor")
        self.assertEqual(issues[0].object_id, NOTE)

    def test_page_points_use_page_size_not_source_size(self):
        objects = route() + [annotation()]
        objects[3]["anchor"] = xy(250.0, 10.0)
        self.assertValid(scene(objects, widthPx=300))

    def test_source_point_outside_source(self):
        objects = route()
        objects[2]["interpretation"]["evidence"] = [
            evidence(((10.0, 10.0), (20.0, 10.0), (15.0, 250.0)))
        ]
        issues = self.issues(scene(objects, sourceHeightPx=240, heightPx=400))
        self.assertEqual([i.code for i in issues], [IssueCode.COORDINATE_OUT_OF_BOUNDS])
        self.assertEqual(
            issues[0].path, "objects[2].interpretation.evidence[0].sourcePolygon[2]"
        )

    def test_negative_coordinate_is_out_of_bounds(self):
        objects = route() + [annotation()]
        objects[3]["anchor"] = xy(10.0, -0.5)
        self.assertCodes(scene(objects), IssueCode.COORDINATE_OUT_OF_BOUNDS)


class TransformTest(InvariantTestCase):
    def test_singular_forward_matrix_reports_only_singular(self):
        issues = self.issues(scene(sourceToDisplay=ZERO))
        self.assertEqual([i.code for i in issues], [IssueCode.TRANSFORM_SINGULAR])
        self.assertEqual(issues[0].path, "page.sourceToDisplay")
        self.assertIsNone(issues[0].object_id)

    def test_each_singular_matrix_is_reported(self):
        self.assertCodes(
            scene(sourceToPage=ZERO, pageToSource=ZERO),
            IssueCode.TRANSFORM_SINGULAR,
            IssueCode.TRANSFORM_SINGULAR,
        )

    def test_inverse_mismatch(self):
        shifted = [1.0, 0.0, 1e-6, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        self.assertCodes(
            scene(pageToSource=shifted), IssueCode.TRANSFORM_INVERSE_MISMATCH
        )

    def test_non_uniform_scale_is_a_mismatch(self):
        stretched = [2.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        self.assertCodes(
            scene(displayToSource=stretched), IssueCode.TRANSFORM_INVERSE_MISMATCH
        )

    def test_homogeneous_scale_is_normalized(self):
        scaled = [3.0 * v for v in IDENTITY]
        self.assertValid(scene(pageToSource=scaled))

    def test_real_inverse_pair_is_valid(self):
        forward = [0.5, 0.0, 10.0, 0.0, 0.5, -4.0, 0.0, 0.0, 1.0]
        inverse = [2.0, 0.0, -20.0, 0.0, 2.0, 8.0, 0.0, 0.0, 1.0]
        self.assertValid(scene(sourceToPage=forward, pageToSource=inverse))

    def test_projective_inverse_pair_is_valid(self):
        forward = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.001, 0.0, 1.0]
        inverse = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, -0.001, 0.0, 1.0]
        self.assertValid(scene(sourceToDisplay=forward, displayToSource=inverse))


class IdAndReferenceTest(InvariantTestCase):
    def test_duplicate_object_id(self):
        issues = self.issues(scene(route() + [mark(PIPE)]))
        self.assertEqual([i.code for i in issues], [IssueCode.DUPLICATE_ID])
        self.assertEqual(issues[0].path, "objects[3].id")

    def test_ids_are_unique_across_layers_objects_and_relationships(self):
        objects = route() + [annotation(), mark(LAYER)]
        relationships = [rel("annotates", NOTE, PIPE, id_=J1)]
        self.assertCodes(
            scene(objects, relationships),
            IssueCode.DUPLICATE_ID,
            IssueCode.DUPLICATE_ID,
        )

    def test_unknown_layer(self):
        objects = route()
        objects[0]["layerId"] = uid(999)
        self.assertCodes(scene(objects), IssueCode.UNKNOWN_REFERENCE)

    def test_unknown_pipe_node_skips_endpoint_check(self):
        objects = route()
        objects[2]["endNodeId"] = uid(999)
        issues = self.issues(scene(objects))
        self.assertEqual([i.code for i in issues], [IssueCode.UNKNOWN_REFERENCE])
        self.assertEqual(issues[0].path, "objects[2].endNodeId")
        self.assertEqual(issues[0].object_id, PIPE)

    def test_unknown_annotation_dimension_and_relationship_targets(self):
        objects = route() + [annotation(target=uid(997)), dimension([uid(998)])]
        relationships = [rel("annotates", NOTE, uid(999))]
        self.assertCodes(
            scene(objects, relationships),
            IssueCode.UNKNOWN_REFERENCE,
            IssueCode.UNKNOWN_REFERENCE,
            IssueCode.UNKNOWN_REFERENCE,
        )

    def test_layer_id_must_name_a_layer(self):
        objects = route()
        objects[0]["layerId"] = J2
        self.assertCodes(scene(objects), IssueCode.WRONG_REFERENCE_TYPE)

    def test_pipe_nodes_must_be_junctions(self):
        objects = route() + [mark()]
        objects[2]["startNodeId"] = MARK
        self.assertCodes(scene(objects), IssueCode.WRONG_REFERENCE_TYPE)

    def test_symbol_ports_must_be_junctions(self):
        objects = route() + [symbol({"inlet": J1, "outlet": PIPE})]
        issues = self.issues(scene(objects))
        self.assertEqual([i.code for i in issues], [IssueCode.WRONG_REFERENCE_TYPE])
        self.assertEqual(issues[0].path, 'objects[3].portNodeIds["outlet"]')

    def test_null_symbol_port_is_not_a_reference(self):
        self.assertValid(scene(route() + [symbol({"inlet": J1, "outlet": None})]))

    def test_annotation_target_must_be_an_object(self):
        self.assertCodes(
            scene(route() + [annotation(target=LAYER)]),
            IssueCode.WRONG_REFERENCE_TYPE,
        )

    def test_relationship_end_must_be_an_object(self):
        objects = route() + [annotation()]
        relationships = [rel("annotates", NOTE, LAYER)]
        self.assertCodes(scene(objects, relationships), IssueCode.WRONG_REFERENCE_TYPE)


class PipeTest(InvariantTestCase):
    def test_endpoint_off_its_junction(self):
        objects = route()
        objects[2]["primitive"]["start"] = xy(51.0, 100.0)
        issues = self.issues(scene(objects))
        self.assertEqual([i.code for i in issues], [IssueCode.PIPE_ENDPOINT_MISMATCH])
        self.assertEqual(issues[0].path, "objects[2].primitive.start")

    def test_endpoint_within_tolerance(self):
        objects = route()
        objects[2]["primitive"]["end"] = xy(150.0 + 5e-7, 100.0)
        self.assertValid(scene(objects))

    def test_custom_tolerance(self):
        objects = route()
        objects[2]["primitive"]["start"] = xy(51.0, 100.0)
        self.assertValid(scene(objects), endpoint_tolerance_px=1.5)

    def test_same_start_and_end_node_is_degenerate_once(self):
        objects = [
            junction(J1, 50.0, 100.0),
            pipe(PIPE, J1, J1, (50.0, 100.0), (50.0, 100.0)),
        ]
        self.assertCodes(scene(objects), IssueCode.PIPE_DEGENERATE)

    def test_zero_length_pipe_is_degenerate(self):
        objects = [
            junction(J1, 50.0, 100.0),
            junction(J2, 50.0, 100.0),
            pipe(PIPE, J1, J2, (50.0, 100.0), (50.0, 100.0)),
        ]
        self.assertCodes(scene(objects), IssueCode.PIPE_DEGENERATE)


class SymbolCatalogTest(InvariantTestCase):
    def test_catalog_accepts_known_ports(self):
        catalog = FakeCatalog(VALVE_CATALOG)
        value = scene(route() + [symbol({"inlet": J1, "outlet": J2})])
        self.assertValid(value, catalog=catalog)
        self.assertEqual(catalog.calls, ["valve"])

    def test_null_port_counts_as_present(self):
        value = scene(route() + [symbol({"inlet": J1, "outlet": None})])
        self.assertValid(value, catalog=FakeCatalog(VALVE_CATALOG))

    def test_unknown_port_name(self):
        value = scene(route() + [symbol({"inlet": J1, "outlet": J2, "drain": None})])
        self.assertCodes(
            value,
            IssueCode.SYMBOL_PORT_UNKNOWN_NAME,
            catalog=FakeCatalog(VALVE_CATALOG),
        )

    def test_required_port_missing(self):
        value = scene(route() + [symbol({"inlet": J1})])
        issues = self.issues(value, catalog=FakeCatalog(VALVE_CATALOG))
        self.assertEqual(
            [i.code for i in issues], [IssueCode.SYMBOL_REQUIRED_PORT_MISSING]
        )
        self.assertIn("outlet", issues[0].message)

    def test_optional_port_may_be_omitted(self):
        catalog = FakeCatalog({"valve": ({"inlet", "outlet", "drain"}, {"inlet"})})
        value = scene(route() + [symbol({"inlet": J1})])
        self.assertValid(value, catalog=catalog)

    def test_symbol_missing_from_catalog(self):
        value = scene(route() + [symbol({"inlet": J1}, symbol_id="mystery")])
        self.assertCodes(
            value, IssueCode.UNKNOWN_REFERENCE, catalog=FakeCatalog(VALVE_CATALOG)
        )

    def test_port_names_are_not_checked_without_a_catalog(self):
        self.assertValid(scene(route() + [symbol({"anything": None})]))


class EvidenceAndTextTest(InvariantTestCase):
    def test_machine_object_needs_evidence(self):
        objects = route()
        objects[2]["interpretation"] = interp(with_evidence=False)
        issues = self.issues(scene(objects))
        self.assertEqual([i.code for i in issues], [IssueCode.MACHINE_EVIDENCE_MISSING])
        self.assertEqual(issues[0].object_id, PIPE)

    def test_machine_relationship_needs_evidence(self):
        relationships = [rel("annotates", NOTE, PIPE)]
        relationships[0]["interpretation"] = interp(with_evidence=False)
        self.assertCodes(
            scene(route() + [annotation()], relationships),
            IssueCode.MACHINE_EVIDENCE_MISSING,
        )

    def test_confirmed_object_may_omit_evidence(self):
        objects = route()
        objects[2]["interpretation"] = interp("confirmed", with_evidence=False)
        self.assertValid(scene(objects))

    def test_control_character_in_text(self):
        issues = self.issues(scene(route() + [annotation("6\x01in")]))
        self.assertEqual(
            [i.code for i in issues],
            [IssueCode.TEXT_INVALID_CHARACTER, IssueCode.TEXT_INVALID_CHARACTER],
        )
        self.assertEqual(issues[0].path, "objects[3].recognizedText")
        self.assertIn("U+0001", issues[0].message)

    def test_xml_whitespace_is_allowed(self):
        self.assertValid(scene(route() + [annotation("6in\t\n\r ok")]))

    def test_invalid_characters_in_keys_and_non_bmp_edges(self):
        objects = route()
        objects[0]["interpretation"]["evidence"][0]["observations"] = {"a\x0b": 1}
        value = scene(objects + [annotation("ok")])
        value.layers[0].name = "pipe\ud800"
        value.objects[3].alternatives = ["\ufffe", "\U0001f527"]
        self.assertCodes(
            value,
            IssueCode.TEXT_INVALID_CHARACTER,
            IssueCode.TEXT_INVALID_CHARACTER,
            IssueCode.TEXT_INVALID_CHARACTER,
        )


class RelationshipTest(InvariantTestCase):
    def test_annotation_relationships_are_valid(self):
        objects = route() + [annotation(target=PIPE)]
        relationships = [
            rel("annotates", NOTE, PIPE),
            rel("callout_targets", NOTE, J1, id_=REL2),
        ]
        self.assertValid(scene(objects, relationships))

    def test_relationship_between_two_pipes_is_only_connectivity_forbidden(self):
        objects = [
            junction(J1, 20.0, 100.0),
            junction(J2, 180.0, 100.0),
            junction(J3, 100.0, 20.0),
            junction(J4, 100.0, 180.0),
            pipe(PIPE, J1, J2, (20.0, 100.0), (180.0, 100.0)),
            pipe(PIPE2, J3, J4, (100.0, 20.0), (100.0, 180.0)),
        ]
        issues = self.issues(scene(objects, [rel("annotates", PIPE, PIPE2)]))
        self.assertEqual(
            [i.code for i in issues], [IssueCode.RELATIONSHIP_CONNECTIVITY_FORBIDDEN]
        )
        self.assertEqual(issues[0].object_id, REL)

    def test_junction_to_symbol_is_connectivity_forbidden(self):
        objects = route() + [symbol({"inlet": J1, "outlet": J2})]
        self.assertCodes(
            scene(objects, [rel("measures", J1, SYMBOL)]),
            IssueCode.RELATIONSHIP_CONNECTIVITY_FORBIDDEN,
        )

    def test_every_connectivity_pair_and_type_is_forbidden(self):
        objects = route() + [symbol({"inlet": J1, "outlet": J2})]
        ends = {"pipe_segment": PIPE, "junction": J1, "symbol": SYMBOL}
        for type_ in ("annotates", "measures", "callout_targets"):
            for from_type, from_id in ends.items():
                for to_type, to_id in ends.items():
                    with self.subTest(type=type_, pair=(from_type, to_type)):
                        self.assertCodes(
                            scene(objects, [rel(type_, from_id, to_id)]),
                            IssueCode.RELATIONSHIP_CONNECTIVITY_FORBIDDEN,
                        )

    def test_relationship_type_outside_the_enum_is_rejected(self):
        with self.assertRaises(ValidationError):
            scene(route(), [rel("connects", J1, J2)])

    def test_annotates_must_come_from_an_annotation(self):
        objects = route() + [mark()]
        self.assertCodes(
            scene(objects, [rel("annotates", MARK, PIPE)]),
            IssueCode.RELATIONSHIP_INVALID_ENDPOINTS,
        )

    def test_callout_targets_must_come_from_an_annotation(self):
        objects = route() + [annotation()]
        self.assertCodes(
            scene(objects, [rel("callout_targets", PIPE, NOTE)]),
            IssueCode.RELATIONSHIP_INVALID_ENDPOINTS,
        )

    def test_measures_must_come_from_a_dimension(self):
        objects = route() + [annotation()]
        self.assertCodes(
            scene(objects, [rel("measures", NOTE, PIPE)]),
            IssueCode.RELATIONSHIP_INVALID_ENDPOINTS,
        )

    def test_measures_matching_dimension_targets_is_valid(self):
        objects = route() + [dimension([PIPE])]
        self.assertValid(scene(objects, [rel("measures", DIM, PIPE)]))

    def test_dimension_target_without_measures_relationship(self):
        issues = self.issues(scene(route() + [dimension([PIPE])]))
        self.assertEqual(
            [i.code for i in issues], [IssueCode.DIMENSION_TARGET_MISMATCH]
        )
        self.assertEqual(issues[0].path, "objects[3].targetObjectIds[0]")

    def test_measures_relationship_not_in_dimension_targets(self):
        objects = route() + [dimension([PIPE])]
        relationships = [
            rel("measures", DIM, PIPE),
            rel("measures", DIM, J1, id_=REL2),
        ]
        issues = self.issues(scene(objects, relationships))
        self.assertEqual(
            [i.code for i in issues], [IssueCode.DIMENSION_TARGET_MISMATCH]
        )
        self.assertEqual(issues[0].object_id, REL2)


class IssueOrderTest(InvariantTestCase):
    def test_all_issues_are_collected_in_a_stable_order(self):
        objects = route() + [annotation("bad\x00"), mark(PIPE)]
        objects[2]["primitive"]["end"] = xy(149.0, 100.0)
        objects[0]["interpretation"] = interp(with_evidence=False)
        value = scene(objects, [rel("annotates", J1, J2)], pageToSource=ZERO)
        expected = [
            IssueCode.TEXT_INVALID_CHARACTER,
            IssueCode.TEXT_INVALID_CHARACTER,
            IssueCode.TRANSFORM_SINGULAR,
            IssueCode.DUPLICATE_ID,
            IssueCode.PIPE_ENDPOINT_MISMATCH,
            IssueCode.MACHINE_EVIDENCE_MISSING,
            IssueCode.RELATIONSHIP_CONNECTIVITY_FORBIDDEN,
        ]
        first = self.issues(value)
        self.assertEqual([i.code for i in first], expected)
        self.assertEqual(self.issues(value), first)

    def test_error_message_lists_every_issue(self):
        with self.assertRaises(SceneValidationError) as caught:
            validate_scene(scene(sourceToDisplay=ZERO, sourceToPage=ZERO))
        self.assertIn("2 scene issues", str(caught.exception))
        self.assertEqual(
            caught.exception.codes,
            (IssueCode.TRANSFORM_SINGULAR, IssueCode.TRANSFORM_SINGULAR),
        )


if __name__ == "__main__":
    unittest.main()
