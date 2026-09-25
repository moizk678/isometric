"""Generate synthetic OCR fixture crops."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent


def _save(name: str, rgb: np.ndarray) -> None:
    Image.fromarray(rgb, mode="RGB").save(OUT / name)


def _text_image(
    text: str,
    *,
    size: tuple[int, int] = (120, 40),
    angle: float = 0.0,
) -> np.ndarray:
    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    draw.text((4, 8), text, fill=(0, 0, 0), font=font)
    if angle:
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))
    return np.array(img)


def generate_all() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _save("abbrev-conn.png", _text_image("conn. to main"))
    _save("feet-inches.png", _text_image("20 ft"))
    _save("rotated-note.png", _text_image("NPT", angle=12.0))
    line = Image.new("RGB", (100, 36), (255, 255, 255))
    draw = ImageDraw.Draw(line)
    draw.line((0, 18, 99, 18), fill=(0, 0, 0), width=2)
    draw.text((8, 4), "???", fill=(0, 0, 0))
    _save("line-crossing.png", np.array(line))


if __name__ == "__main__":
    generate_all()
