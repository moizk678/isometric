"""Generate synthetic symbol crop PNGs for classifier tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent


def _save(name: str, rgb: np.ndarray) -> None:
    Image.fromarray(rgb, mode="RGB").save(OUT / name)


def ball_valve() -> None:
    img = Image.new("RGB", (80, 40), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.polygon([(10, 10), (10, 30), (70, 15), (70, 25)], outline=(0, 0, 0), width=2)
    draw.ellipse((35, 16, 45, 24), fill=(0, 0, 0))
    _save("ball-valve.png", np.array(img))


def ambiguous_blob() -> None:
    img = Image.new("RGB", (48, 48), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 40, 40), outline=(0, 0, 0), width=2)
    _save("ambiguous-blob.png", np.array(img))


def flow_arrow() -> None:
    img = Image.new("RGB", (72, 32), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.polygon([(60, 16), (20, 4), (20, 28)], outline=(0, 0, 0), width=2)
    _save("flow-arrow.png", np.array(img))


def flange_mark() -> None:
    img = Image.new("RGB", (64, 40), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.line([(12, 8), (12, 32)], fill=(0, 0, 0), width=2)
    draw.line([(52, 8), (52, 32)], fill=(0, 0, 0), width=2)
    draw.line([(12, 20), (52, 20)], fill=(0, 0, 0), width=2)
    _save("flange.png", np.array(img))


def generate_all() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ball_valve()
    ambiguous_blob()
    flow_arrow()
    flange_mark()


if __name__ == "__main__":
    generate_all()
