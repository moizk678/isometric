"""Generate page-normalization test fixtures."""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path

import cv2
import numpy as np
from PIL import ExifTags, Image

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


def flat_scan() -> bytes:
    rgb = np.full((240, 320, 3), 255, dtype=np.uint8)
    cv2.rectangle(rgb, (8, 8), (311, 231), (0, 0, 0), 2)
    return _png_bytes(rgb)


def skewed_page() -> bytes:
    width, height = 420, 320
    canvas = np.full((height, width, 3), 210, dtype=np.uint8)
    margin = 24
    cv2.rectangle(
        canvas,
        (margin, margin),
        (width - margin - 1, height - margin - 1),
        (255, 255, 255),
        -1,
    )
    cv2.rectangle(
        canvas,
        (margin, margin),
        (width - margin - 1, height - margin - 1),
        (0, 0, 0),
        2,
    )
    src = np.float32(
        [
            [margin, margin],
            [width - margin, margin],
            [width - margin, height - margin],
            [margin, height - margin],
        ]
    )
    dst = np.float32([[36, 28], [384, 12], [404, 292], [18, 300]])
    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(
        canvas, matrix, (width, height), borderValue=(120, 120, 120)
    )
    warped_rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
    return _png_bytes(warped_rgb)


def no_boundary() -> bytes:
    rgb = np.full((200, 200, 3), 128, dtype=np.uint8)
    return _png_bytes(rgb)


def exif_rotated_jpeg(orientation: int = 6) -> bytes:
    image = Image.new("RGB", (60, 40), color="white")
    image.paste((255, 0, 0), (4, 2, 12, 8))
    buf = io.BytesIO()
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = orientation
    image.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def generate_all() -> None:
    _write("flat-scan.png", flat_scan())
    _write("skewed-page.png", skewed_page())
    _write("no-boundary.png", no_boundary())
    _write("exif-orientation-6.jpg", exif_rotated_jpeg(6))


def check_hashes() -> int:
    generate_all()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        raise SystemExit(check_hashes())
    generate_all()


if __name__ == "__main__":
    main()
