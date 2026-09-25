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


def load_settings() -> ApiSettings:
    root = Path(os.environ.get("ARTIFACT_ROOT", ".private/artifacts"))
    return ApiSettings(
        artifact_root=root,
        max_upload_bytes=int(os.environ.get("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024))),
        max_pixels=int(os.environ.get("MAX_PIXELS", str(40_000_000))),
        pipeline_version=os.environ.get("PIPELINE_VERSION", "fixture@1.0.0"),
        profile_id=os.environ.get("PROFILE_ID", "piping_isometric"),
        require_owner_header=os.environ.get("REQUIRE_OWNER_HEADER", "true").lower()
        == "true",
    )
