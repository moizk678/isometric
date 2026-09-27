"""API configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiSettings:
    artifact_root: Path
    max_upload_bytes: int
    max_pixels: int
    pipeline_version: str
    profile_id: str
    require_owner_header: bool
    vision_enabled: bool
    cloudflare_account_id: str
    vision_api_key: str
    vision_model: str
    gemini_api_key: str
    gemini_model: str


def load_settings() -> ApiSettings:
    root = Path(os.environ.get("ARTIFACT_ROOT", ".private/artifacts"))
    vision_enabled = os.environ.get("VISION_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return ApiSettings(
        artifact_root=root,
        max_upload_bytes=int(os.environ.get("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024))),
        max_pixels=int(os.environ.get("MAX_PIXELS", str(40_000_000))),
        pipeline_version=os.environ.get("PIPELINE_VERSION", "pipeline@1.0.0"),
        profile_id=os.environ.get("PROFILE_ID", "piping_isometric"),
        require_owner_header=os.environ.get("REQUIRE_OWNER_HEADER", "true").lower()
        == "true",
        vision_enabled=vision_enabled,
        cloudflare_account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip(),
        vision_api_key=os.environ.get("VISION_API_KEY", "").strip(),
        vision_model=os.environ.get(
            "VISION_MODEL", "@cf/meta/llama-3.2-11b-vision-instruct"
        ).strip(),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip(),
    )
