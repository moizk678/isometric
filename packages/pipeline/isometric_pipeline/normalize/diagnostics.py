"""Visual diagnostics for page normalization."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image


def corner_overlay_png(
    display_rgb: np.ndarray,
    quad: np.ndarray | None,
) -> bytes:
    """Draw detected page corners on the display image (display coordinate space)."""
    bgr = cv2.cvtColor(display_rgb, cv2.COLOR_RGB2BGR)
    if quad is not None and len(quad) == 4:
        pts = quad.astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(bgr, [pts], True, (0, 200, 0), 2)
        for index, point in enumerate(quad):
            x, y = int(point[0]), int(point[1])
            cv2.circle(bgr, (x, y), 4, (255, 80, 0), -1)
            cv2.putText(
                bgr,
                str(index),
                (x + 6, y - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 80, 0),
                1,
                cv2.LINE_AA,
            )
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
