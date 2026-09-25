"""Visual diagnostics for mask stages."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image


def masks_overlay_png(
    rgb: np.ndarray,
    grid_mask: np.ndarray,
    retained_ink_mask: np.ndarray,
    protection_mask: np.ndarray,
    region_boxes: list[tuple[int, int, int, int]] | None = None,
) -> bytes:
    overlay = rgb.copy().astype(np.float32)
    grid = grid_mask > 0
    ink = retained_ink_mask > 0
    protect = protection_mask > 0
    overlay[grid] = (
        overlay[grid] * 0.5 + np.array([80, 200, 80], dtype=np.float32) * 0.5
    )
    overlay[ink] = (
        overlay[ink] * 0.45 + np.array([40, 120, 255], dtype=np.float32) * 0.55
    )
    overlay[protect] = (
        overlay[protect] * 0.4 + np.array([255, 80, 80], dtype=np.float32) * 0.6
    )
    bgr = cv2.cvtColor(overlay.astype(np.uint8), cv2.COLOR_RGB2BGR)
    if region_boxes:
        for x0, y0, x1, y1 in region_boxes:
            cv2.rectangle(bgr, (x0, y0), (x1, y1), (255, 200, 0), 1)
    rgb_out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb_out, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
