"""Multipart upload validation."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass

from PIL import Image

from .errors import ApiError

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"


@dataclass(frozen=True)
class ValidatedUpload:
    data: bytes
    mime: str
    source_hash: str
    width_px: int
    height_px: int
    options_hash: str


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def options_hash(profile_id: str, options: dict[str, object]) -> str:
    payload = json.dumps(
        {"profile_id": profile_id, "options": options},
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_hex(payload.encode("utf-8"))


def validate_image_bytes(
    data: bytes,
    *,
    max_bytes: int,
    max_pixels: int,
) -> tuple[str, int, int]:
    if len(data) > max_bytes:
        raise ApiError(413, "payload_too_large", "upload exceeds byte limit")
    if data.startswith(PNG_SIGNATURE):
        mime = "image/png"
    elif data.startswith(JPEG_SIGNATURE):
        mime = "image/jpeg"
    else:
        raise ApiError(415, "unsupported_media_type", "only PNG and JPEG are accepted")
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if width * height > max_pixels:
                raise ApiError(
                    413, "image_too_large", "decoded pixel count exceeds limit"
                )
            image.verify()
    except ApiError:
        raise
    except Exception:
        raise ApiError(400, "invalid_image", "image could not be decoded") from None
    return mime, width, height


def validate_upload(
    data: bytes,
    *,
    profile_id: str,
    options: dict[str, object],
    max_bytes: int,
    max_pixels: int,
) -> ValidatedUpload:
    mime, width, height = validate_image_bytes(
        data, max_bytes=max_bytes, max_pixels=max_pixels
    )
    return ValidatedUpload(
        data=data,
        mime=mime,
        source_hash=_sha256_hex(data),
        width_px=width,
        height_px=height,
        options_hash=options_hash(profile_id, options),
    )
