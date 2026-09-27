"""Environment-backed vision settings for drawing reading."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DrawingReadingSettings:
    vision_enabled: bool
    cloudflare_account_id: str
    vision_api_key: str
    vision_model: str
    gemini_api_key: str
    gemini_model: str
    request_timeout_seconds: float
    fake_mode: str | None


def load_drawing_reading_settings() -> DrawingReadingSettings:
    fake = os.environ.get("ISOMETRIC_FAKE_DRAWING_READING")
    fake_mode = fake.strip() if fake and fake.strip() else None
    return DrawingReadingSettings(
        vision_enabled=_truthy("VISION_ENABLED"),
        cloudflare_account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip(),
        vision_api_key=os.environ.get("VISION_API_KEY", "").strip(),
        vision_model=os.environ.get(
            "VISION_MODEL", "@cf/meta/llama-3.2-11b-vision-instruct"
        ).strip(),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip(),
        request_timeout_seconds=float(
            os.environ.get("DRAWING_READING_TIMEOUT_SECONDS", "30")
        ),
        fake_mode=fake_mode,
    )
