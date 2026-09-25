"""Fit the fixture scene to an uploaded image's source and display frames."""

from __future__ import annotations

import copy
import io
from dataclasses import dataclass
from typing import Any

from PIL import ExifTags, Image, ImageOps

Matrix = list[float]

FIXTURE_REVIEW_ISSUE_TYPE = "fixture_low_confidence"

# Forward EXIF maps as (a, b, c, d, e, f) with x' = a*x + b*y + c and
# y' = d*x + e*y + f; "W" and "H" in c/f stand for the stored source size.
# The orientation-to-transpose pairing mirrors PIL.ImageOps.exif_transpose.
_ORIENTATION_MAPS: dict[int, tuple[int, int, str, int, int, str]] = {
    1: (1, 0, "0", 0, 1, "0"),
    2: (-1, 0, "W", 0, 1, "0"),  # FLIP_LEFT_RIGHT
    3: (-1, 0, "W", 0, -1, "H"),  # ROTATE_180
    4: (1, 0, "0", 0, -1, "H"),  # FLIP_TOP_BOTTOM
    5: (0, 1, "0", 1, 0, "0"),  # TRANSPOSE
    6: (0, -1, "H", 1, 0, "0"),  # ROTATE_270, 90 degrees clockwise
    7: (0, -1, "H", -1, 0, "W"),  # TRANSVERSE
    8: (0, 1, "0", -1, 0, "W"),  # ROTATE_90, 90 degrees counter-clockwise
}


@dataclass(frozen=True)
class SourceFrame:
    orientation: int
    source_width_px: int
    source_height_px: int
    display_width_px: int
    display_height_px: int
    source_to_display: Matrix
    display_to_source: Matrix


@dataclass(frozen=True)
class FixtureReviewItem:
    issue_key: str
    object_id: str
    issue_type: str
    severity: str


def orientation_matrices(
    orientation: int, source_width_px: int, source_height_px: int
) -> tuple[Matrix, Matrix]:
    """Return row-major (sourceToDisplay, displayToSource) for an EXIF orientation."""
    a, b, c_sym, d, e, f_sym = _ORIENTATION_MAPS.get(orientation, _ORIENTATION_MAPS[1])
    sizes = {"0": 0, "W": source_width_px, "H": source_height_px}
    c, f = sizes[c_sym], sizes[f_sym]
    forward = [a, b, c, d, e, f, 0, 0, 1]
    # The linear part is a signed permutation, so its inverse is its transpose
    # and the translation is -R^T t.
    inverse = [
        a,
        d,
        -(a * c + d * f),
        b,
        e,
        -(b * c + e * f),
        0,
        0,
        1,
    ]
    return [float(v) for v in forward], [float(v) for v in inverse]


def read_source_frame(data: bytes) -> SourceFrame:
    with Image.open(io.BytesIO(data)) as image:
        source_width, source_height = image.size
        raw_orientation = image.getexif().get(ExifTags.Base.Orientation, 1)
        displayed = ImageOps.exif_transpose(image)
        assert displayed is not None
        display_width, display_height = displayed.size
    orientation = (
        raw_orientation
        if isinstance(raw_orientation, int) and raw_orientation in _ORIENTATION_MAPS
        else 1
    )
    source_to_display, display_to_source = orientation_matrices(
        orientation, source_width, source_height
    )
    mapped = _display_size_for(source_to_display, source_width, source_height)
    if mapped != (display_width, display_height):
        raise ValueError(
            f"EXIF orientation {orientation} maps {source_width}x{source_height} to "
            f"{mapped[0]}x{mapped[1]}, but exif_transpose produced "
            f"{display_width}x{display_height}"
        )
    return SourceFrame(
        orientation=orientation,
        source_width_px=source_width,
        source_height_px=source_height,
        display_width_px=display_width,
        display_height_px=display_height,
        source_to_display=source_to_display,
        display_to_source=display_to_source,
    )


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
        fx, fy = _apply(fixture_source_to_page, point["x"], point["y"])
        sx, sy = _apply(frame.display_to_source, fx * scale_x, fy * scale_y)
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


def _apply(matrix: Matrix, x: float, y: float) -> tuple[float, float]:
    w = matrix[6] * x + matrix[7] * y + matrix[8]
    return (
        (matrix[0] * x + matrix[1] * y + matrix[2]) / w,
        (matrix[3] * x + matrix[4] * y + matrix[5]) / w,
    )


def _display_size_for(
    source_to_display: Matrix, width: int, height: int
) -> tuple[int, int]:
    corners = [_apply(source_to_display, x, y) for x, y in ((0, 0), (width, height))]
    return (
        round(abs(corners[1][0] - corners[0][0])),
        round(abs(corners[1][1] - corners[0][1])),
    )


def _clean(value: float, upper: int) -> float:
    return min(max(round(value, 6), 0.0), float(upper)) + 0.0
