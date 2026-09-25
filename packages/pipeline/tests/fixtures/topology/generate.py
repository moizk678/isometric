"""Generate synthetic topology fixture masks."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent
SIZE = (256, 256)


def _save(name: str, mask: np.ndarray) -> None:
    Image.fromarray(mask, mode="L").save(OUT / name)


def _line(
    canvas: np.ndarray,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    thickness: int = 5,
) -> None:
    cv2.line(
        canvas,
        (int(round(x0)), int(round(y0))),
        (int(round(x1)), int(round(y1))),
        255,
        thickness,
        cv2.LINE_AA,
    )


def generate_all() -> None:
    h, w = SIZE

    crossing = np.zeros((h, w), dtype=np.uint8)
    _line(crossing, 24, 128, 232, 128)
    _line(crossing, 128, 24, 128, 118)
    _line(crossing, 128, 138, 128, 232)
    _save("disconnected-crossing.png", crossing)

    tee = np.zeros((h, w), dtype=np.uint8)
    _line(tee, 128, 40, 128, 216)
    _line(tee, 128, 128, 220, 128)
    _save("true-tee.png", tee)

    elbow = np.zeros((h, w), dtype=np.uint8)
    _line(elbow, 60, 180, 60, 100)
    _line(elbow, 60, 100, 180, 100)
    _save("elbow.png", elbow)

    near_miss = np.zeros((h, w), dtype=np.uint8)
    _line(near_miss, 40, 128, 118, 128)
    _line(near_miss, 138, 128, 216, 128)
    _save("near-miss.png", near_miss)

    gap_bridge = np.zeros((h, w), dtype=np.uint8)
    _line(gap_bridge, 40, 128, 110, 128)
    _line(gap_bridge, 130, 128, 216, 128)
    for x in range(110, 131):
        gap_bridge[126:131, x] = 255
    _save("collinear-gap-bridge.png", gap_bridge)

    red_blue = np.zeros((h, w, 3), dtype=np.uint8)
    cv2.line(red_blue, (30, 128), (226, 128), (220, 40, 40), 5, cv2.LINE_AA)
    cv2.line(red_blue, (128, 30), (128, 226), (40, 80, 220), 5, cv2.LINE_AA)
    Image.fromarray(red_blue, mode="RGB").save(OUT / "different-color-crossing.png")


if __name__ == "__main__":
    generate_all()
