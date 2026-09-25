"""Fit the fixture scene to an uploaded image's source and display frames."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from isometric_pipeline.geometry.transforms import Matrix, apply_mat3
from isometric_pipeline.ingest.exif_frame import (
    SourceFrame,
    orientation_matrices,
    read_source_frame,
)

FIXTURE_REVIEW_ISSUE_TYPE = "fixture_low_confidence"

__all__ = [
    "FIXTURE_REVIEW_ISSUE_TYPE",
    "FixtureReviewItem",
    "SourceFrame",
    "fit_fixture_scene",
    "fixture_review_items",
    "orientation_matrices",
    "read_source_frame",
    "severity_for_score",
]


@dataclass(frozen=True)
class FixtureReviewItem:
    issue_key: str
    object_id: str
    issue_type: str
    severity: str


def fit_fixture_scene(fixture: dict[str, Any], frame: SourceFrame) -> dict[str, Any]:
    """Scale fixture geometry into the display page and evidence into source pixels.

    The page is the display frame, so sourceToPage equals sourceToDisplay.
    """
    scene = copy.deepcopy(fixture)
    fixture_page = fixture["page"]
    fixture_source_to_page: Matrix = fixture_page["sourceToPage"]
    page_width = frame.display_width_px
    page_height = frame.display_height_px
    scale_x = page_width / fixture_page["widthPx"]
    scale_y = page_height / fixture_page["heightPx"]

    def to_page(point: dict[str, float]) -> dict[str, float]:
        return {
            "x": _clean(point["x"] * scale_x, page_width),
            "y": _clean(point["y"] * scale_y, page_height),
        }

    def to_source(point: dict[str, float]) -> dict[str, float]:
        fx, fy = apply_mat3(fixture_source_to_page, point["x"], point["y"])
        sx, sy = apply_mat3(frame.display_to_source, fx * scale_x, fy * scale_y)
        return {
            "x": _clean(sx, frame.source_width_px),
            "y": _clean(sy, frame.source_height_px),
        }

    scene["page"] = {
        "sourceWidthPx": frame.source_width_px,
        "sourceHeightPx": frame.source_height_px,
        "displayWidthPx": frame.display_width_px,
        "displayHeightPx": frame.display_height_px,
        "widthPx": page_width,
        "heightPx": page_height,
        "sourceToDisplay": list(frame.source_to_display),
        "displayToSource": list(frame.display_to_source),
        "sourceToPage": list(frame.source_to_display),
        "pageToSource": list(frame.display_to_source),
    }

    for obj in scene["objects"]:
        for path in _page_point_paths(obj):
            parent = obj
            for key in path[:-1]:
                parent = parent.get(key) or {}
            if path[-1] in parent:
                parent[path[-1]] = to_page(parent[path[-1]])
        _fit_evidence(obj["interpretation"], to_source)
    for relationship in scene["relationships"]:
        _fit_evidence(relationship["interpretation"], to_source)
    return scene


def fixture_review_items(scene: dict[str, Any]) -> list[FixtureReviewItem]:
    """One review item per machine-state object, keyed stably by object ID."""
    items: list[FixtureReviewItem] = []
    for obj in scene["objects"]:
        interpretation = obj["interpretation"]
        if interpretation["state"] != "machine":
            continue
        items.append(
            FixtureReviewItem(
                issue_key=f"{FIXTURE_REVIEW_ISSUE_TYPE}:{obj['id']}",
                object_id=obj["id"],
                issue_type=FIXTURE_REVIEW_ISSUE_TYPE,
                severity=severity_for_score(interpretation.get("score")),
            )
        )
    return items


def severity_for_score(score: float | None) -> str:
    if score is None or score < 0.5:
        return "high"
    if score < 0.9:
        return "medium"
    return "low"


def _page_point_paths(obj: dict[str, Any]) -> list[tuple[str, ...]]:
    kind = obj["type"]
    if kind == "junction":
        return [("position",)]
    if kind == "pipe_segment":
        return [
            ("primitive", "start"),
            ("primitive", "end"),
            ("originalPrimitive", "start"),
            ("originalPrimitive", "end"),
        ]
    if kind in ("symbol", "annotation"):
        return [("anchor",)]
    if kind == "dimension":
        return [("witnessStart",), ("witnessEnd",)]
    if kind == "unknown_mark":
        return []
    raise ValueError(f"fixture object type {kind!r} has no page-point mapping")


def _fit_evidence(interpretation: dict[str, Any], to_source: Any) -> None:
    for evidence in interpretation["evidence"]:
        evidence["sourcePolygon"] = [to_source(p) for p in evidence["sourcePolygon"]]


def _clean(value: float, upper: int) -> float:
    return min(max(round(value, 6), 0.0), float(upper)) + 0.0
