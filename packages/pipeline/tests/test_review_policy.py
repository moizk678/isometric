"""Tests for review carry-forward and readiness policy."""

from __future__ import annotations

import unittest

from isometric_pipeline.review.policy import (
    ReviewItemRow,
    derive_review_state,
    items_after_edit,
    items_after_resolution,
)


def _item(
    key: str,
    *,
    severity: str = "medium",
    state: str = "open",
    object_id: str | None = "obj-1",
) -> ReviewItemRow:
    return ReviewItemRow(
        issue_key=key,
        object_id=object_id,
        relationship_id=None,
        issue_type="test.issue",
        severity=severity,
        crop_uri=None,
        proposed_options=[],
        state=state,
    )


class ReviewPolicyTest(unittest.TestCase):
    def test_critical_acknowledged_blocks_ready(self) -> None:
        items = [_item("a", severity="critical", state="acknowledged_unknown")]
        self.assertEqual(derive_review_state(items), "review_required")

    def test_all_resolved_allows_ready(self) -> None:
        items = [_item("a", state="confirmed")]
        self.assertEqual(derive_review_state(items), "ready")

    def test_unrelated_item_survives_edit(self) -> None:
        parent = [
            _item("a", object_id="obj-1"),
            _item("b", object_id="obj-2"),
        ]
        result = items_after_edit(parent, affected_object_ids={"obj-1"})
        keys = {item.issue_key for item in result}
        self.assertEqual(keys, {"a", "b"})
        a = next(item for item in result if item.issue_key == "a")
        b = next(item for item in result if item.issue_key == "b")
        self.assertEqual(a.state, "open")
        self.assertEqual(b.state, "open")

    def test_resolution_closes_item(self) -> None:
        parent = [_item("a"), _item("b")]
        result = items_after_resolution(parent, issue_key="a", new_state="confirmed")
        states = {item.issue_key: item.state for item in result}
        self.assertEqual(states["a"], "confirmed")
        self.assertEqual(states["b"], "open")

    def test_resolution_keeps_prior_confirmed_items(self) -> None:
        parent = [
            _item("a", state="confirmed"),
            _item("b", object_id="obj-2"),
        ]
        result = items_after_resolution(parent, issue_key="b", new_state="confirmed")
        states = {item.issue_key: item.state for item in result}
        self.assertEqual(states["a"], "confirmed")
        self.assertEqual(states["b"], "confirmed")

    def test_edit_keeps_confirmed_items(self) -> None:
        parent = [
            _item("a", state="confirmed"),
            _item("b", object_id="obj-2"),
        ]
        result = items_after_edit(parent, affected_object_ids={"obj-2"})
        keys = {item.issue_key for item in result}
        self.assertEqual(keys, {"a", "b"})
        self.assertEqual(next(i for i in result if i.issue_key == "a").state, "confirmed")


if __name__ == "__main__":
    unittest.main()
