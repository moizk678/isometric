"""Gemini vision fallback."""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from ..prompt import DRAWING_READING_SYSTEM
from ..settings import DrawingReadingSettings
from .workers_ai import ProviderCallResult

logger = logging.getLogger(__name__)


def _extract_gemini_text(payload: dict[str, Any]) -> str | None:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    first = candidates[0]
    if not isinstance(first, dict):
        return None
    content = first.get("content")
    if not isinstance(content, dict):
        return None
    parts = content.get("parts")
    if not isinstance(parts, list):
        return None
    chunks: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            chunks.append(part["text"])
    text = "".join(chunks).strip()
    return text or None


def call_gemini(
    *,
    settings: DrawingReadingSettings,
    image_bytes: bytes,
    job_id: str,
) -> ProviderCallResult:
    model = settings.gemini_model
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={settings.gemini_api_key}"
    )
    encoded = base64.b64encode(image_bytes).decode("ascii")
    body = {
        "systemInstruction": {"parts": [{"text": DRAWING_READING_SYSTEM}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Read this isometric drawing."},
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": encoded,
                        }
                    },
                ],
            }
        ],
    }
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(
            request, timeout=settings.request_timeout_seconds
        ) as response:
            raw = response.read()
            http_status = response.status
    except urllib.error.HTTPError as exc:
        http_status = exc.code
        raw = exc.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        detail = getattr(exc, "reason", None) or str(exc)
        logger.info(
            "drawing_reading provider=gemini model=%s latency_ms=%s status=error job_id=%s detail=%s",
            model,
            latency_ms,
            job_id,
            detail,
        )
        return ProviderCallResult(
            provider="gemini",
            model=model,
            latency_ms=latency_ms,
            status="error",
            text=None,
            http_status=None,
        )
    latency_ms = int((time.perf_counter() - started) * 1000)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.info(
            "drawing_reading provider=gemini model=%s latency_ms=%s status=failed job_id=%s",
            model,
            latency_ms,
            job_id,
        )
        return ProviderCallResult(
            provider="gemini",
            model=model,
            latency_ms=latency_ms,
            status="failed",
            text=None,
            http_status=http_status,
        )
    if not isinstance(payload, dict):
        return ProviderCallResult(
            provider="gemini",
            model=model,
            latency_ms=latency_ms,
            status="failed",
            text=None,
            http_status=http_status,
        )
    text = _extract_gemini_text(payload)
    if http_status >= 400 or text is None:
        logger.info(
            "drawing_reading provider=gemini model=%s latency_ms=%s status=failed job_id=%s http_status=%s",
            model,
            latency_ms,
            job_id,
            http_status,
        )
        return ProviderCallResult(
            provider="gemini",
            model=model,
            latency_ms=latency_ms,
            status="failed",
            text=text,
            http_status=http_status,
        )
    logger.info(
        "drawing_reading provider=gemini model=%s latency_ms=%s status=ok job_id=%s",
        model,
        latency_ms,
        job_id,
    )
    return ProviderCallResult(
        provider="gemini",
        model=model,
        latency_ms=latency_ms,
        status="ok",
        text=text,
        http_status=http_status,
    )
