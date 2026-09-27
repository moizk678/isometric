"""Ink retention from page RGB."""

from __future__ import annotations

import cv2
import numpy as np

from isometric_pipeline.masks.grid import COLOR_SAT_MIN, GRID_CONFIDENCE_MIN
from isometric_pipeline.masks.util import paper_lightness_estimate

INK_THRESHOLD = 14.0


def estimate_retained_ink(
    rgb: np.ndarray,
    grid_mask: np.ndarray,
    *,
    grid_confidence: float,
    apply_grid_removal: bool,
) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    paper = paper_lightness_estimate(gray)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1].astype(np.float32)

    dark_ink = gray.astype(np.float32) < (paper - INK_THRESHOLD)
    colored_ink = saturation >= COLOR_SAT_MIN
    retained = (dark_ink | colored_ink).astype(np.uint8) * 255

    if apply_grid_removal and grid_confidence >= GRID_CONFIDENCE_MIN:
        retained = retained.copy()
        retained[grid_mask > 0] = 0

    return retained
