"""Shared helpers for centerline stages."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

from isometric_pipeline.masks.util import encode_crop_png
from isometric_pipeline.regions.artifact import PageBBox


def decode_mask_png(png: bytes, height: int, width: int) -> np.ndarray:
    with Image.open(io.BytesIO(png)) as image:
        gray = np.array(image.convert("L"))
    if gray.shape != (height, width):
        raise ValueError("mask dimensions do not match page")
    return gray


def apply_protection_mask(
    mask: np.ndarray, protection: np.ndarray | None
) -> np.ndarray:
    """Zero ink that belongs to protected components, not their bounding boxes."""
    if protection is None:
        return mask
    if protection.shape != mask.shape:
        raise ValueError("protection mask dimensions do not match")
    out = mask.copy()
    out[protection > 0] = 0
    return out


def crop_from_bbox(rgb: np.ndarray, bbox: PageBBox, pad: int = 2) -> bytes:
    height, width = rgb.shape[:2]
    x0 = max(0, int(bbox.x) - pad)
    y0 = max(0, int(bbox.y) - pad)
    x1 = min(width, int(bbox.x + bbox.width) + pad)
    y1 = min(height, int(bbox.y + bbox.height) + pad)
    if x1 <= x0 or y1 <= y0:
        return encode_crop_png(rgb[0:1, 0:1])
    return encode_crop_png(rgb[y0:y1, x0:x1])
