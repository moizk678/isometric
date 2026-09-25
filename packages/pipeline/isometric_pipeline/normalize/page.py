"""Safe image ingestion and page normalization stage."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np
from PIL import Image, ImageOps

from isometric_pipeline.geometry.transforms import (
    IDENTITY_MAT3,
    compose_mat3,
    invert_mat3,
)
from isometric_pipeline.ingest.exif_frame import read_source_frame
from isometric_pipeline.normalize.artifact import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    WARNING_PAGE_BOUNDARY_LOW,
    NormalizeDiagnostics,
    NormalizePageMetadata,
    RasterArtifactRef,
)
from isometric_pipeline.normalize.diagnostics import corner_overlay_png

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"

BOUNDARY_CONFIDENCE_MIN = 0.20
MIN_BLUR_FOR_RECTIFY = 20.0
MIN_CONTRAST_FOR_RECTIFY = 8.0

StageStatus = Literal["succeeded", "partial"]


@dataclass(frozen=True)
class NormalizeLimits:
    max_bytes: int = 20 * 1024 * 1024
    max_pixels: int = 40_000_000


class NormalizePageError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class NormalizePageResult:
    status: StageStatus
    display_png: bytes
    page_png: bytes
    overlay_png: bytes
    metadata: NormalizePageMetadata
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def normalize_page(
    source_bytes: bytes,
    *,
    limits: NormalizeLimits | None = None,
    display_uri: str = "display.png",
    page_uri: str = "page.png",
) -> NormalizePageResult:
    """Decode source bytes and produce display/page derivatives with transforms."""
    bounds = limits or NormalizeLimits()
    _validate_bytes(source_bytes, bounds)
    frame = read_source_frame(source_bytes)
    display_rgb = _load_display_rgb(source_bytes)
    gray = cv2.cvtColor(display_rgb, cv2.COLOR_RGB2GRAY)

    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(gray.std())
    shadow_heavy = _shadow_heavy(gray)

    quad, boundary_confidence = _find_page_quad(display_rgb)
    warnings: list[str] = []
    rectified = False
    display_to_page = list(IDENTITY_MAT3)

    quality_ok = (
        quad is not None
        and boundary_confidence >= BOUNDARY_CONFIDENCE_MIN
        and blur_score >= MIN_BLUR_FOR_RECTIFY
        and contrast >= MIN_CONTRAST_FOR_RECTIFY
    )

    page_rgb = display_rgb
    page_w = frame.display_width_px
    page_h = frame.display_height_px

    if quality_ok and quad is not None:
        try:
            page_rgb, display_to_page, page_w, page_h = _rectify(display_rgb, quad)
            _ = invert_mat3(display_to_page)
            rectified = True
        except ValueError:
            page_rgb = display_rgb.copy()
            display_to_page = list(IDENTITY_MAT3)
            page_w = frame.display_width_px
            page_h = frame.display_height_px
            warnings.append(WARNING_PAGE_BOUNDARY_LOW)

    if rectified:
        status: StageStatus = "succeeded"
    else:
        if quad is None or boundary_confidence < BOUNDARY_CONFIDENCE_MIN:
            if WARNING_PAGE_BOUNDARY_LOW not in warnings:
                warnings.append(WARNING_PAGE_BOUNDARY_LOW)
        status = "partial" if warnings else "succeeded"

    page_to_display = invert_mat3(display_to_page)
    source_to_page = compose_mat3(display_to_page, frame.source_to_display)
    page_to_source = invert_mat3(source_to_page)

    display_png = _encode_png(display_rgb)
    page_png = _encode_png(page_rgb)
    overlay_png = corner_overlay_png(display_rgb, quad)

    display_hash = _average_hash(display_rgb)
    page_hash = _average_hash(page_rgb)

    metadata = NormalizePageMetadata(
        source_width_px=frame.source_width_px,
        source_height_px=frame.source_height_px,
        display_width_px=frame.display_width_px,
        display_height_px=frame.display_height_px,
        page_width_px=page_w,
        page_height_px=page_h,
        orientation=frame.orientation,
        source_to_display=list(frame.source_to_display),
        display_to_source=list(frame.display_to_source),
        display_to_page=display_to_page,
        page_to_display=page_to_display,
        source_to_page=source_to_page,
        page_to_source=page_to_source,
        display_artifact=RasterArtifactRef(
            uri=display_uri,
            coordinate_space="display",
            width_px=frame.display_width_px,
            height_px=frame.display_height_px,
            media_type="image/png",
        ),
        page_artifact=RasterArtifactRef(
            uri=page_uri,
            coordinate_space="page",
            width_px=page_w,
            height_px=page_h,
            media_type="image/png",
        ),
        display_hash=display_hash,
        page_hash=page_hash,
        diagnostics=NormalizeDiagnostics(
            blur_score=blur_score,
            contrast=contrast,
            shadow_heavy=shadow_heavy,
            boundary_confidence=boundary_confidence,
            rectified=rectified,
        ),
        warnings=warnings,
    )

    wire = metadata.to_wire()
    content_hash = hashlib.sha256(json_bytes(wire) + display_png + page_png).hexdigest()

    metrics = {
        "blur_score": blur_score,
        "contrast": contrast,
        "boundary_confidence": boundary_confidence,
        "rectified": rectified,
        "orientation": frame.orientation,
    }

    return NormalizePageResult(
        status=status,
        display_png=display_png,
        page_png=page_png,
        overlay_png=overlay_png,
        metadata=metadata,
        warnings=warnings,
        metrics=metrics,
        content_hash=content_hash,
    )


def json_bytes(payload: dict) -> bytes:
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _validate_bytes(data: bytes, limits: NormalizeLimits) -> None:
    if len(data) > limits.max_bytes:
        raise NormalizePageError("payload_too_large", "upload exceeds byte limit")
    if data.startswith(PNG_SIGNATURE):
        pass
    elif data.startswith(JPEG_SIGNATURE):
        pass
    else:
        raise NormalizePageError(
            "unsupported_media_type", "only PNG and JPEG are accepted"
        )
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if width * height > limits.max_pixels:
                raise NormalizePageError(
                    "image_too_large", "decoded pixel count exceeds limit"
                )
            image.verify()
    except NormalizePageError:
        raise
    except Exception as exc:
        raise NormalizePageError("invalid_image", "image could not be decoded") from exc


def _load_display_rgb(source_bytes: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(source_bytes)) as image:
        displayed = ImageOps.exif_transpose(image)
        assert displayed is not None
        rgb = displayed.convert("RGB")
        return np.array(rgb)


def _encode_png(rgb: np.ndarray) -> bytes:
    image = Image.fromarray(rgb, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _average_hash(rgb: np.ndarray, size: int = 8) -> str:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    resized = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
    avg = float(resized.mean())
    bits = "".join("1" if pixel >= avg else "0" for pixel in resized.reshape(-1))
    return format(int(bits, 2), f"0{size * size // 4}x")


def _shadow_heavy(gray: np.ndarray) -> bool:
    h, w = gray.shape
    margin_x = max(1, w // 10)
    margin_y = max(1, h // 10)
    corners = [
        gray[:margin_y, :margin_x],
        gray[:margin_y, -margin_x:],
        gray[-margin_y:, :margin_x],
        gray[-margin_y:, -margin_x:],
    ]
    center = gray[margin_y : h - margin_y, margin_x : w - margin_x]
    if center.size == 0:
        return False
    corner_mean = float(np.mean([part.mean() for part in corners]))
    center_mean = float(center.mean())
    return corner_mean + 25.0 < center_mean


def _find_page_quad(display_rgb: np.ndarray) -> tuple[np.ndarray | None, float]:
    gray = cv2.cvtColor(display_rgb, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 75, 200)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = gray.shape
    image_area = float(width * height)
    best_quad: np.ndarray | None = None
    best_score = 0.0
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        area = cv2.contourArea(approx)
        if area < 0.12 * image_area or area > 0.98 * image_area:
            continue
        score = area / image_area
        if score > best_score:
            best_score = score
            best_quad = approx.reshape(4, 2).astype(np.float32)
    return best_quad, best_score


def _order_quad_points(points: np.ndarray) -> np.ndarray:
    pts = np.array(points, dtype=np.float32)
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1).reshape(-1)
    tl_idx = int(np.argmin(sums))
    br_idx = int(np.argmax(sums))
    tr_idx = int(np.argmin(diffs))
    bl_idx = int(np.argmax(diffs))
    indices = [tl_idx, tr_idx, br_idx, bl_idx]
    if len(set(indices)) != 4:
        raise ValueError("page quad corners are ambiguous")
    ordered = np.array(
        [pts[tl_idx], pts[tr_idx], pts[br_idx], pts[bl_idx]], dtype=np.float32
    )
    if cv2.contourArea(ordered.reshape(-1, 1, 2)) < 1.0:
        raise ValueError("page quad has no area")
    return ordered


def _rectify(
    display_rgb: np.ndarray,
    quad: np.ndarray,
) -> tuple[np.ndarray, list[float], int, int]:
    src = _order_quad_points(quad)
    width_a = float(np.linalg.norm(src[0] - src[1]))
    width_b = float(np.linalg.norm(src[2] - src[3]))
    height_a = float(np.linalg.norm(src[0] - src[3]))
    height_b = float(np.linalg.norm(src[1] - src[2]))
    page_w = max(1, int(round(max(width_a, width_b))))
    page_h = max(1, int(round(max(height_a, height_b))))
    dst = np.array(
        [
            [0, 0],
            [page_w - 1, 0],
            [page_w - 1, page_h - 1],
            [0, page_h - 1],
        ],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(src, dst)
    display_bgr = cv2.cvtColor(display_rgb, cv2.COLOR_RGB2BGR)
    page_bgr = cv2.warpPerspective(
        display_bgr, matrix, (page_w, page_h), flags=cv2.INTER_LINEAR
    )
    page_rgb = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2RGB)
    display_to_page = [float(value) for value in matrix.reshape(-1)]
    return page_rgb, display_to_page, page_w, page_h


__all__ = [
    "NormalizeLimits",
    "NormalizePageError",
    "NormalizePageResult",
    "PRODUCER_VERSION",
    "SCHEMA_VERSION",
    "normalize_page",
]
