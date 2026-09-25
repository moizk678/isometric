"""Visual diagnostics for primitive snapping."""

from __future__ import annotations

import io
import math

import cv2
import numpy as np
from PIL import Image

from isometric_pipeline.snapping.artifact import (
    AxesMetadata,
    SnappedPrimitiveCandidate,
)


def snapping_overlay_png(
    rgb: np.ndarray,
    candidates: list[SnappedPrimitiveCandidate],
    axes_meta: AxesMetadata,
) -> bytes:
    bgr = cv2.cvtColor(rgb.copy(), cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    cx, cy = w // 2, h // 2
    rose_len = min(w, h) // 6
    for axis in axes_meta.axes:
        rad = math.radians(axis.angle_deg)
        ex = int(cx + rose_len * math.cos(rad))
        ey = int(cy + rose_len * math.sin(rad))
        cv2.line(bgr, (cx, cy), (ex, ey), (200, 200, 0), 1)

    for cand in candidates:
        pre0 = (int(cand.pre_snap.start.x), int(cand.pre_snap.start.y))
        pre1 = (int(cand.pre_snap.end.x), int(cand.pre_snap.end.y))
        cv2.line(bgr, pre0, pre1, (180, 180, 180), 1, cv2.LINE_AA)
        post0 = (int(cand.post_snap.start.x), int(cand.post_snap.start.y))
        post1 = (int(cand.post_snap.end.x), int(cand.post_snap.end.y))
        if cand.status == "snapped":
            cv2.line(bgr, post0, post1, (0, 220, 0), 2, cv2.LINE_AA)
        else:
            cv2.line(bgr, post0, post1, (0, 140, 255), 2, cv2.LINE_AA)

    rgb_out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb_out, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
