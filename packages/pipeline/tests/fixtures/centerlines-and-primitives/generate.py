"""Generate synthetic stroke fixtures for centerline tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent
SIZE = (320, 240)


def _save(name: str, mask: np.ndarray) -> None:
    image = Image.fromarray(mask, mode="L")
    image.save(OUT / name)


def _page_from_mask(mask: np.ndarray) -> np.ndarray:
    rgb = np.full((mask.shape[0], mask.shape[1], 3), 255, dtype=np.uint8)
    ink = mask > 0
    rgb[ink] = (20, 20, 20)
    return rgb


def generate_all() -> None:
    h, w = SIZE
    horizontal = np.zeros((h, w), dtype=np.uint8)
    cv2.line(horizontal, (40, 120), (280, 120), 255, 6)
    _save("horizontal-stroke.png", horizontal)

    sloped = np.zeros((h, w), dtype=np.uint8)
    cv2.line(sloped, (50, 200), (270, 40), 255, 5)
    _save("sloped-stroke.png", sloped)

    thick = np.zeros((h, w), dtype=np.uint8)
    cv2.line(thick, (60, 60), (260, 60), 255, 14)
    _save("thick-stroke.png", thick)

    broken = np.zeros((h, w), dtype=np.uint8)
    cv2.line(broken, (40, 180), (140, 180), 255, 5)
    cv2.line(broken, (180, 180), (280, 180), 255, 5)
    _save("broken-stroke.png", broken)

    noisy = np.zeros((h, w), dtype=np.uint8)
    pts = np.array(
        [
            [40, 100],
            [80, 103],
            [120, 98],
            [160, 102],
            [200, 99],
            [240, 101],
            [280, 100],
        ],
        dtype=np.int32,
    )
    for i in range(len(pts) - 1):
        cv2.line(noisy, tuple(pts[i]), tuple(pts[i + 1]), 255, 5)
    _save("noisy-stroke.png", noisy)

    bent = np.zeros((h, w), dtype=np.uint8)
    cv2.line(bent, (60, 200), (60, 80), 255, 6)
    cv2.line(bent, (60, 80), (240, 80), 255, 6)
    _save("bent-stroke.png", bent)

    page = _page_from_mask(horizontal)
    Image.fromarray(page, mode="RGB").save(OUT / "horizontal-page.png")


if __name__ == "__main__":
    generate_all()
