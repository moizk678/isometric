"""Shared helpers for mask stages."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image


def decode_page_rgb(page_png: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(page_png)) as image:
        rgb = image.convert("RGB")
        return np.array(rgb)


def encode_mask_png(mask: np.ndarray) -> bytes:
    if mask.dtype != np.uint8:
        raise ValueError("mask must be uint8")
    if mask.ndim != 2:
        raise ValueError("mask must be single channel")
    image = Image.fromarray(mask, mode="L")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def encode_crop_png(rgb: np.ndarray) -> bytes:
    image = Image.fromarray(rgb, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def paper_lightness_estimate(gray: np.ndarray) -> float:
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    return float(np.percentile(blur, 88))
