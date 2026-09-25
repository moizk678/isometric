"""Crop and deskew text regions in page coordinates."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from isometric_pipeline.regions.artifact import PageBBox


@dataclass(frozen=True)
class PreprocessedCrop:
    rgb: np.ndarray
    rotation_deg: float
    crop_bbox_page: PageBBox


def crop_region(
    page_rgb: np.ndarray,
    bbox: PageBBox,
    *,
    padding_px: int,
    deskew: bool,
) -> PreprocessedCrop:
    height, width = page_rgb.shape[:2]
    x0 = max(0, int(bbox.x) - padding_px)
    y0 = max(0, int(bbox.y) - padding_px)
    x1 = min(width, int(bbox.x + bbox.width) + padding_px)
    y1 = min(height, int(bbox.y + bbox.height) + padding_px)
    crop = page_rgb[y0:y1, x0:x1].copy()
    rotation = 0.0
    if deskew and crop.size > 0:
        crop, rotation = deskew_image(crop)
    page_bbox = PageBBox(
        x=float(x0),
        y=float(y0),
        width=float(x1 - x0),
        height=float(y1 - y0),
    )
    return PreprocessedCrop(rgb=crop, rotation_deg=rotation, crop_bbox_page=page_bbox)


def deskew_image(rgb: np.ndarray) -> tuple[np.ndarray, float]:
    """Deskew a crop in isolation; returns (rgb, rotation_deg)."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(ink)
    if coords is None or len(coords) < 4:
        return rgb, 0.0
    rect = cv2.minAreaRect(coords)
    angle = float(rect[-1])
    if rect[1][0] < rect[1][1]:
        angle += 90.0
    if abs(angle) < 0.5 or abs(angle) > 45.0:
        return rgb, 0.0
    center = (rgb.shape[1] // 2, rgb.shape[0] // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        rgb,
        matrix,
        (rgb.shape[1], rgb.shape[0]),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated, angle
