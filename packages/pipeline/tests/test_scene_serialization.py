import json
import unittest
from pathlib import Path

from isometric_pipeline.scene.errors import IssueCode, SceneValidationError
from isometric_pipeline.scene.models import DrawingScene
from isometric_pipeline.scene.serialization import dump_scene, load_scene
from isometric_pipeline.scene.versioning import check_version

FIXTURES = Path(__file__).resolve().parents[2] / "scene-schema/fixtures"
VALID = FIXTURES / "valid"
INVALID = FIXTURES / "invalid"

_IDENTITY_TRANSFORM = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]


def _minimal_scene_dict() -> dict:
    layer_id = "a1000001-0001-4001-8001-000000000003"
    junction_id = "a1000001-0001-4001-8001-000000000011"
    return {
        "schemaVersion": "1.0",
        "documentId": "a1000001-0001-4001-8001-000000000001",
        "revisionId": "a1000001-0001-4001-8001-000000000002",
        "profileId": "piping_isometric",
        "page": {
            "sourceWidthPx": 200,
            "sourceHeightPx": 200,
            "displayWidthPx": 200,
            "displayHeightPx": 200,
            "widthPx": 200,
            "heightPx": 200,
            "sourceToDisplay": _IDENTITY_TRANSFORM,
            "displayToSource": _IDENTITY_TRANSFORM,
            "sourceToPage": _IDENTITY_TRANSFORM,
            "pageToSource": _IDENTITY_TRANSFORM,
        },
        "layers": [
            {
                "id": layer_id,
                "name": "piping",
                "sourceColor": "#1a1a1a",
                "renderColor": "#0b5fff",
            }
        ],
        "objects": [
            {
                "type": "junction",
                "id": junction_id,
                "layerId": layer_id,
                "position": {"x": 50.0, "y": 50.0},
                "kind": "endpoint",
                "interpretation": {
                    "state": "machine",
                    "evidence": [
                        {
                            "sourcePolygon": [
                                {"x": 10.0, "y": 10.0},
                                {"x": 20.0, "y": 10.0},
                                {"x": 15.0, "y": 20.0},
                            ],
                            "stage": "vectorize",
                            "artifactId": "test-artifact",
                            "observations": {"confidence": 0.9},
                        }
                    ],
                },
            }
        ],
        "relationships": [],
    }


def _segments_intersect(a, b) -> bool:
    def orient(p, q, r) -> float:
        return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)

    return (
        orient(a.start, a.end, b.start) * orient(a.start, a.end, b.end) < 0
        and orient(b.start, b.end, a.start) * orient(b.start, b.end, a.end) < 0
    )


def _assert_round_trip_stable(test: unittest.TestCase, scene: DrawingScene) -> None:
    first = dump_scene(scene)
    second = dump_scene(load_scene(first))
    test.assertEqual(first, second)


class SceneSerializationTest(unittest.TestCase):
    def test_minimal_python_scene_round_trip_is_byte_stable(self):
        scene = load_scene(_minimal_scene_dict())
        _assert_round_trip_stable(self, scene)

    def test_valid_fixture_round_trips_are_byte_stable(self):
        for path in sorted(VALID.glob("*.json")):
            with self.subTest(fixture=path.name):
                scene = load_scene(path.read_text(encoding="utf-8"))
                _assert_round_trip_stable(self, scene)

    def test_crossing_unconnected_keeps_four_distinct_endpoint_ids(self):
        raw = (VALID / "crossing-unconnected.json").read_text(encoding="utf-8")
        scene = load_scene(raw)
        before = {
            obj.id
            for obj in scene.objects
            if obj.type == "junction" and obj.kind == "endpoint"
        }
        self.assertEqual(len(before), 4)

        after_scene = load_scene(dump_scene(scene))
        after = {
            obj.id
            for obj in after_scene.objects
            if obj.type == "junction" and obj.kind == "endpoint"
        }
        self.assertEqual(after, before)
        self.assertEqual(len(after), 4)

    def test_crossing_pipes_share_no_node_after_round_trip(self):
        raw = (VALID / "crossing-unconnected.json").read_text(encoding="utf-8")
        scene = load_scene(dump_scene(load_scene(raw)))
        pipes = [obj for obj in scene.objects if obj.type == "pipe_segment"]
        self.assertEqual(len(pipes), 2)
        first, second = pipes
        self.assertTrue(
            _segments_intersect(first.primitive, second.primitive),
            "fixture pipes must geometrically cross",
        )
        self.assertEqual(
            {first.start_node_id, first.end_node_id}
            & {second.start_node_id, second.end_node_id},
            set(),
        )
        self.assertFalse(
            any(obj.type == "symbol" for obj in scene.objects),
            "no symbol port may join the crossing pipes",
        )
        self.assertEqual(scene.relationships, [])

    def test_check_version_rejects_2_0_and_1_1(self):
        base = json.loads((VALID / "connected-route.json").read_text(encoding="utf-8"))
        for version in ("2.0", "1.1"):
            with self.subTest(schemaVersion=version):
                data = dict(base)
                data["schemaVersion"] = version
                with self.assertRaises(SceneValidationError) as ctx:
                    check_version(data)
                self.assertEqual(ctx.exception.codes, (IssueCode.VERSION_UNSUPPORTED,))

    def test_check_version_accepts_1_0(self):
        base = json.loads((VALID / "connected-route.json").read_text(encoding="utf-8"))
        base["schemaVersion"] = "1.0"
        result = check_version(base)
        self.assertEqual(result["schemaVersion"], "1.0")

    def test_non_finite_coordinate_fixture_raises_non_finite_number(self):
        raw = (INVALID / "non-finite-coordinate.json").read_text(encoding="utf-8")
        with self.assertRaises(SceneValidationError) as ctx:
            load_scene(raw)
        self.assertIn(IssueCode.NON_FINITE_NUMBER, ctx.exception.codes)

    def test_malformed_wire_data_raises_schema_invalid(self):
        raw = (VALID / "connected-route.json").read_text(encoding="utf-8")
        cases = {
            "truncated": raw[:-5],
            "invalid_utf8": b"\xff\xfe{}",
            "bom": "\ufeff" + raw,
            "too_deep": "[" * 100_000 + "]" * 100_000,
        }
        for name, data in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(SceneValidationError) as ctx:
                    load_scene(data)
                self.assertEqual(ctx.exception.codes, (IssueCode.SCHEMA_INVALID,))

    def test_duplicate_json_keys_are_rejected(self):
        raw = (VALID / "connected-route.json").read_text(encoding="utf-8")
        duplicated = raw.replace(
            '"schemaVersion": "1.0"',
            '"schemaVersion": "9.0",\n  "schemaVersion": "1.0"',
            1,
        )
        self.assertNotEqual(duplicated, raw)
        with self.assertRaises(SceneValidationError) as ctx:
            load_scene(duplicated)
        self.assertEqual(ctx.exception.codes, (IssueCode.SCHEMA_INVALID,))
        self.assertIn("schemaVersion", ctx.exception.issues[0].message)

    def test_unknown_object_type_raises_schema_invalid(self):
        raw = (INVALID / "unknown-object-type.json").read_text(encoding="utf-8")
        with self.assertRaises(SceneValidationError) as ctx:
            load_scene(raw)
        self.assertIn(IssueCode.SCHEMA_INVALID, ctx.exception.codes)


if __name__ == "__main__":
    unittest.main()
