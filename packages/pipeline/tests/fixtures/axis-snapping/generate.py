"""Generate synthetic fixtures for axis snapping tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent
SIZE = (400, 400)


def _save(name: str, mask: np.ndarray) -> None:
    Image.fromarray(mask, mode="L").save(OUT / name)


def _line_mask(
    canvas: np.ndarray,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    thickness: int = 6,
) -> None:
    cv2.line(
        canvas,
        (int(round(x0)), int(round(y0))),
        (int(round(x1)), int(round(y1))),
        255,
        thickness,
        cv2.LINE_AA,
    )


def _rotate_mask(mask: np.ndarray, degrees: float) -> np.ndarray:
    h, w = mask.shape
    center = (w / 2.0, h / 2.0)
    mat = cv2.getRotationMatrix2D(center, degrees, 1.0)
    return cv2.warpAffine(
        mask,
        mat,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def _iso_triad_mask_separated() -> np.ndarray:
    """Three long iso-direction strokes without a common intersection."""
    h, w = SIZE
    mask = np.zeros((h, w), dtype=np.uint8)
    _line_mask(mask, 70, 60, 70, 340, thickness=6)
    _line_mask(mask, 110, 310, 310, 170, thickness=6)
    _line_mask(mask, 110, 90, 310, 230, thickness=6)
    return mask


def generate_all() -> None:
    h, w = SIZE
    triad = _iso_triad_mask_separated()
    rotated = _rotate_mask(triad, 15.0)
    _save("rotated-isometric-triad.png", rotated)

    off_axis = _iso_triad_mask_separated()
    _line_mask(off_axis, 50, 350, 350, 50, thickness=5)
    _save("off-axis-45.png", off_axis)

    weak = np.zeros((h, w), dtype=np.uint8)
    _line_mask(weak, 180, 200, 215, 198, thickness=4)
    _save("weak-evidence.png", weak)

    dim_adj = _iso_triad_mask_separated()
    _save("dimension-adjacent.png", dim_adj)


if __name__ == "__main__":
    generate_all()
