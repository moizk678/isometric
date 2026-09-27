"""Tests for confirmed-object overlay on reprocess candidates."""

from __future__ import annotations

import unittest

from isometric_pipeline.review.overlay import lost_confirmed_edits, overlay_confirmed_objects
from isometric_pipeline.scene.models import Interpretation
from test_scene_invariants import NOTE, annotation, route, scene


class ReviewOverlayTest(unittest.TestCase):
    def test_overlay_keeps_confirmed_annotation(self) -> None:
        base_objects = route() + [annotation("machine")]
        candidate = scene(objects=base_objects)
        ann = next(obj for obj in candidate.objects if obj.id == NOTE)
        confirmed = ann.model_copy(
            update={
                "normalized_text": "confirmed text",
                "interpretation": Interpretation(
                    state="confirmed", evidence=ann.interpretation.evidence
                ),
            }
        )
        reviewed_objects = [
            obj if obj.id != NOTE else confirmed for obj in candidate.objects
        ]
        reviewed = scene(objects=reviewed_objects)
        alt_ann = annotation("new machine guess")
        mutated = scene(objects=route() + [alt_ann])
        merged = overlay_confirmed_objects(mutated, reviewed)
        merged_ann = next(obj for obj in merged.objects if obj.id == NOTE)
        self.assertEqual(merged_ann.normalized_text, "confirmed text")

    def test_lost_confirmed_edits_detects_diff(self) -> None:
        current = scene(objects=route() + [annotation("kept")])
        ann = next(obj for obj in current.objects if obj.id == NOTE)
        ann = ann.model_copy(
            update={
                "interpretation": Interpretation(
                    state="confirmed", evidence=ann.interpretation.evidence
                )
            }
        )
        current = scene(
            objects=[obj if obj.id != NOTE else ann for obj in current.objects]
        )
        candidate = scene(objects=route() + [annotation("other")])
        lost = lost_confirmed_edits(current, candidate)
        self.assertEqual(len(lost), 1)
        self.assertEqual(lost[0]["reason"], "differs_on_candidate")


if __name__ == "__main__":
    unittest.main()
