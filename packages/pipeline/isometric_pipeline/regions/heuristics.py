"""Heuristic region proposals on page ink."""

from __future__ import annotations

import cv2
import numpy as np

from isometric_pipeline.regions.artifact import PageBBox, RegionCandidate, RegionKind

MIN_REGION_AREA = 24
TEXT_ASPECT_MIN = 2.2
SYMBOL_MAX_ASPECT = 1.8
DIMENSION_MIN_WIDTH = 40


def propose_regions(
    rgb: np.ndarray,
    annotation_mask: np.ndarray,
    crops_prefix: str,
) -> tuple[list[RegionCandidate], dict[str, bytes]]:
    """Return region candidates and crop PNG bytes keyed by crop id."""
    height, width = annotation_mask.shape
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        annotation_mask, connectivity=8
    )
    regions: list[RegionCandidate] = []
    crops: dict[str, bytes] = {}
    pad = 4

    for label in range(1, num_labels):
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < MIN_REGION_AREA:
            continue

        aspect = w / max(1, h)
        kind, score, evidence = _classify_region(w, h, aspect, area)

        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(width, x + w + pad)
        y1 = min(height, y + h + pad)
        crop_id = f"region_{label:04d}"
        crop_uri = f"{crops_prefix}/{crop_id}.png"
        crop_rgb = rgb[y0:y1, x0:x1].copy()
        crops[crop_id] = _encode_crop(crop_rgb)

        regions.append(
            RegionCandidate(
                id=crop_id,
                kind=kind,
                bbox=PageBBox(x=float(x), y=float(y), width=float(w), height=float(h)),
                score=score,
                crop_uri=crop_uri,
                evidence=evidence,
            )
        )

    return regions, crops


def build_protection_mask(
    height: int,
    width: int,
    regions: list[RegionCandidate],
    annotation_mask: np.ndarray,
) -> np.ndarray:
    protection = np.zeros((height, width), dtype=np.uint8)
    for region in regions:
        box = region.bbox
        x0 = max(0, int(box.x))
        y0 = max(0, int(box.y))
        x1 = min(width, int(box.x + box.width))
        y1 = min(height, int(box.y + box.height))
        component = annotation_mask[y0:y1, x0:x1] > 0
        protection_slice = protection[y0:y1, x0:x1]
        protection_slice[component] = 255
    return protection


def _classify_region(
    w: int, h: int, aspect: float, area: int
) -> tuple[RegionKind, float, str]:
    if aspect >= TEXT_ASPECT_MIN and w >= 30:
        return "text", 0.72, "wide horizontal blob"
    if aspect <= SYMBOL_MAX_ASPECT and max(w, h) <= 48:
        return "symbol", 0.68, "compact mark"
    if aspect >= 3.0 and w >= DIMENSION_MIN_WIDTH and h <= 20:
        return "dimension", 0.65, "elongated thin horizontal mark"
    if aspect >= 1.2 and area < 200:
        return "arrow", 0.55, "small elongated mark"
    if aspect >= TEXT_ASPECT_MIN:
        return "text", 0.6, "horizontal ink cluster"
    return "symbol", 0.5, "unclassified ink cluster"


def _encode_crop(rgb: np.ndarray) -> bytes:
    from isometric_pipeline.masks.util import encode_crop_png

    return encode_crop_png(rgb)
