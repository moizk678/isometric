"""Tests for semantic scene edit commands."""

from __future__ import annotations

import unittest

from isometric_pipeline.scene import DrawingScene, SceneValidationError, validate_scene
from isometric_pipeline.scene.edits import apply_edits
from isometric_pipeline.scene.edits.commands import (
    ConnectPipeEndpoint,
    DisconnectPipeEndpoint,
    SetSymbolType,
    UpdateAnnotationText,
)
from test_scene_invariants import (
    VALVE_CATALOG,
    FakeCatalog,
    J1,
    J2,
    NOTE,
    PIPE,
    SYMBOL,
    annotation,
    junction,
    pipe,
    route,
    scene,
    symbol,
)


class SceneEditsTest(unittest.TestCase):
    def test_update_annotation_text(self) -> None:
        base = scene(objects=route() + [annotation("old")])
        result = apply_edits(
            base,
            [
                UpdateAnnotationText(
                    object_id=NOTE,
                    normalized_text="6 in",
                )
            ],
        )
        ann = next(obj for obj in result.scene.objects if obj.id == NOTE)
        self.assertEqual(ann.normalized_text, "6 in")
        self.assertEqual(ann.recognized_text, "old")
        self.assertEqual(ann.interpretation.state, "confirmed")
        self.assertIn(NOTE, result.affected_object_ids)

    def test_disconnect_pipe_endpoint_creates_junction(self) -> None:
        base = scene()
        result = apply_edits(
            base,
            [
                DisconnectPipeEndpoint(pipe_id=PIPE, endpoint="end"),
            ],
        )
        pipe_obj = next(obj for obj in result.scene.objects if obj.id == PIPE)
        self.assertNotEqual(pipe_obj.end_node_id, J2)
        self.assertEqual(len(result.new_object_ids), 1)
        validate_scene(result.scene)

    def test_connect_pipe_endpoint_snaps_primitive(self) -> None:
        objects = [
            junction(J1, 50.0, 100.0),
            junction(J2, 200.0, 100.0),
            pipe(PIPE, J1, J2, (50.0, 100.0), (150.0, 100.0)),
        ]
        base = scene(objects=objects)
        result = apply_edits(
            base,
            [ConnectPipeEndpoint(pipe_id=PIPE, endpoint="end", node_id=J2)],
        )
        pipe_obj = next(obj for obj in result.scene.objects if obj.id == PIPE)
        self.assertEqual(pipe_obj.primitive.end.x, 200.0)
        validate_scene(result.scene)

    def test_set_symbol_type_requires_catalog(self) -> None:
        base = scene(
            objects=route()
            + [
                symbol(
                    {"inlet": J1, "outlet": J2},
                    symbol_id="valve",
                )
            ]
        )
        with self.assertRaises(SceneValidationError):
            apply_edits(
                base,
                [SetSymbolType(object_id=SYMBOL, symbol_id="unknown_symbol")],
                catalog=FakeCatalog(VALVE_CATALOG),
            )

    def test_unknown_object_raises(self) -> None:
        base = scene()
        with self.assertRaises(ValueError):
            apply_edits(
                base,
                [UpdateAnnotationText(object_id=NOTE, normalized_text="x")],
            )


if __name__ == "__main__":
    unittest.main()
