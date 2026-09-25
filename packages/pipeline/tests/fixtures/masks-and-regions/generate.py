"""Generate masks-and-regions test fixtures."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent


def _png_bytes(rgb: np.ndarray) -> bytes:
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    ok, encoded = cv2.imencode(".png", bgr)
    if not ok:
        raise RuntimeError("failed to encode PNG")
    return encoded.tobytes()


def _write(name: str, data: bytes) -> None:
    path = HERE / name
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()[:12]
    print(f"wrote {path.name} ({len(data)} bytes, sha256={digest})")


def faint_grid() -> bytes:
    w, h = 320, 240
    rgb = np.full((h, w, 3), 252, dtype=np.uint8)
    for x in range(20, w - 20, 20):
        cv2.line(rgb, (x, 16), (x, h - 16), (210, 210, 210), 1)
    for y in range(20, h - 20, 20):
        cv2.line(rgb, (16, y), (w - 16, y), (210, 210, 210), 1)
    cv2.line(rgb, (40, 120), (280, 120), (0, 0, 0), 4)
    cv2.line(rgb, (160, 40), (200, 200), (200, 40, 40), 4)
    return _png_bytes(rgb)


def dark_grid() -> bytes:
    w, h = 320, 240
    rgb = np.full((h, w, 3), 245, dtype=np.uint8)
    for x in range(16, w - 16, 24):
        cv2.line(rgb, (x, 12), (x, h - 12), (60, 60, 60), 2)
    for y in range(16, h - 16, 24):
        cv2.line(rgb, (12, y), (w - 12, y), (60, 60, 60), 2)
    cv2.line(rgb, (30, 180), (290, 60), (55, 55, 55), 3)
    return _png_bytes(rgb)


def colored_routes() -> bytes:
    w, h = 300, 220
    rgb = np.full((h, w, 3), 255, dtype=np.uint8)
    cv2.line(rgb, (20, 110), (280, 110), (220, 30, 30), 5)
    cv2.line(rgb, (150, 20), (150, 200), (30, 80, 220), 5)
    cv2.line(rgb, (40, 40), (260, 180), (30, 180, 60), 5)
    cv2.putText(
        rgb,
        "TAG",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )
    return _png_bytes(rgb)


def text_blocks() -> bytes:
    w, h = 320, 200
    rgb = np.full((h, w, 3), 255, dtype=np.uint8)
    cv2.rectangle(rgb, (24, 40), (180, 62), (0, 0, 0), -1)
    cv2.rectangle(rgb, (24, 80), (140, 102), (0, 0, 0), -1)
    cv2.rectangle(rgb, (220, 50), (250, 80), (0, 0, 0), 2)
    cv2.line(rgb, (40, 140), (260, 140), (0, 0, 0), 3)
    return _png_bytes(rgb)


def generate_all() -> None:
    _write("faint-grid.png", faint_grid())
    _write("dark-grid.png", dark_grid())
    _write("colored-routes.png", colored_routes())
    _write("text-blocks.png", text_blocks())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if args.all:
        generate_all()


if __name__ == "__main__":
    main()
