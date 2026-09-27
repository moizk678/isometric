"""Background and grid line estimation."""

from __future__ import annotations

import cv2
import numpy as np

from isometric_pipeline.masks.util import paper_lightness_estimate

GRID_CONFIDENCE_MIN = 0.35
FAINT_LINE_LOW = 5.0
FAINT_LINE_HIGH = 55.0
DARK_LINE_MAX = 80.0
COLOR_SAT_MIN = 28.0


def estimate_grid(
    rgb: np.ndarray,
) -> tuple[np.ndarray, float, float]:
    """Return grid_mask (uint8 0/255), grid_confidence, paper_lightness."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    paper = paper_lightness_estimate(gray)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    faint_band = (blur >= paper - FAINT_LINE_HIGH) & (blur <= paper - FAINT_LINE_LOW)
    faint_u8 = faint_band.astype(np.uint8) * 255
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 1))
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 17))
    faint_h = cv2.morphologyEx(faint_u8, cv2.MORPH_OPEN, kernel_h)
    faint_v = cv2.morphologyEx(faint_u8, cv2.MORPH_OPEN, kernel_v)
    faint_grid = cv2.bitwise_or(faint_h, faint_v)

    dark_band = blur < (paper - DARK_LINE_MAX)
    dark_u8 = dark_band.astype(np.uint8) * 255
    dark_h = cv2.morphologyEx(dark_u8, cv2.MORPH_OPEN, kernel_h)
    dark_v = cv2.morphologyEx(dark_u8, cv2.MORPH_OPEN, kernel_v)
    dark_grid = cv2.bitwise_or(dark_h, dark_v)

    grid_raw = cv2.bitwise_or(faint_grid, dark_grid)
    strong_ink = blur < paper - FAINT_LINE_HIGH - 25
    overlap = int(np.count_nonzero(grid_raw & strong_ink))
    grid_pixels = int(np.count_nonzero(grid_raw))
    if grid_pixels == 0:
        return np.zeros_like(gray, dtype=np.uint8), 0.0, paper

    overlap_ratio = overlap / max(1, grid_pixels)
    faint_pixels = int(np.count_nonzero(faint_grid))
    dark_pixels = int(np.count_nonzero(dark_grid))

    confidence = 0.0
    if faint_pixels > 0:
        faint_overlap = int(np.count_nonzero(faint_grid & strong_ink))
        faint_conf = (1.0 - faint_overlap / max(1, faint_pixels)) * min(
            1.0, faint_pixels / max(1, gray.size) * 120
        )
        confidence = max(confidence, float(faint_conf))

    if dark_pixels > 0:
        dark_overlap = int(np.count_nonzero(dark_grid & strong_ink))
        dark_conf = (1.0 - dark_overlap / max(1, dark_pixels)) * 0.35
        confidence = max(confidence, float(dark_conf))

    confidence = max(0.0, min(1.0, confidence * (1.0 - overlap_ratio * 1.5)))

    if confidence < GRID_CONFIDENCE_MIN:
        return np.zeros_like(gray, dtype=np.uint8), confidence, paper

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    colored = hsv[:, :, 1].astype(np.float32) >= COLOR_SAT_MIN
    grid_mask = grid_raw.copy()
    grid_mask[strong_ink] = 0
    grid_mask[colored] = 0
    return grid_mask, confidence, paper
