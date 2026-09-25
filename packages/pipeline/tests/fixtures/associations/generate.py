"""Generate synthetic association test fixtures."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent


def _save(name: str, rgb: np.ndarray) -> None:
    Image.fromarray(rgb, mode="RGB").save(OUT / name)


def _save_mask(name: str, mask: np.ndarray) -> None:
    Image.fromarray(mask, mode="L").save(OUT / name)


def clean_dimension() -> None:
    rgb = np.full((200, 320, 3), 255, dtype=np.uint8)
    mask = np.zeros((200, 320), dtype=np.uint8)
    cv2.line(rgb, (40, 90), (240, 90), (0, 0, 0), 2)
    cv2.line(mask, (40, 90), (240, 90), 255, 1)
    cv2.line(rgb, (40, 100), (40, 130), (0, 0, 0), 1)
    cv2.line(rgb, (240, 100), (240, 130), (0, 0, 0), 1)
    cv2.putText(rgb, "20 ft", (110, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    _save("clean-dimension-page.png", rgb)
    _save_mask("clean-dimension-geometry.png", mask)


def note_with_leader() -> None:
    rgb = np.full((200, 240, 3), 255, dtype=np.uint8)
    mask = np.zeros((200, 240), dtype=np.uint8)
    cv2.putText(rgb, "BV", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.line(rgb, (45, 50), (120, 110), (0, 0, 0), 1)
    cv2.line(mask, (45, 50), (120, 110), 255, 1)
    cv2.circle(rgb, (120, 110), 8, (0, 0, 0), 2)
    _save("note-leader-page.png", rgb)
    _save_mask("note-leader-geometry.png", mask)


def generate_all() -> None:
    clean_dimension()
    note_with_leader()


if __name__ == "__main__":
    generate_all()
