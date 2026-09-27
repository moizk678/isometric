"""Cloudflare Workers AI vision client."""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from ..prompt import DRAWING_READING_SYSTEM
from ..settings import DrawingReadingSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderCallResult:
    provider: str
    model: str
    latency_ms: int
    status: str
    text: str | None
    http_status: int | None = None


def _extract_workers_text(payload: dict[str, Any]) -> str | None:
    for key in ("response", "result", "output"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(payload.get("result"), dict):
        nested = payload["result"]
        for key in ("response", "output", "text"):
            value = nested.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _post_json(
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: float,
) -> tuple[int, dict[str, Any] | None, str | None]:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        detail = getattr(exc, "reason", None) or str(exc)
        return 0, None, str(detail)
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None, "invalid_json_response"
    if not isinstance(parsed, dict):
        return status, None, "invalid_json_response"
    return status, parsed, None


def call_workers_ai(
    *,
    settings: DrawingReadingSettings,
    image_bytes: bytes,
    job_id: str,
) -> ProviderCallResult:
    account_id = settings.cloudflare_account_id
    model = settings.vision_model
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {settings.vision_api_key}"}
    encoded = base64.b64encode(image_bytes).decode("ascii")
    body = {
        "messages": [
            {"role": "system", "content": DRAWING_READING_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Read this isometric drawing."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"},
                    },
                ],
            },
        ]
    }
    last_status: int | None = None
    last_error: str | None = None
    for attempt in range(2):
        started = time.perf_counter()
        status, payload, error = _post_json(
            url, headers=headers, body=body, timeout=settings.request_timeout_seconds
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        if error:
            last_error = error
            logger.info(
                "drawing_reading provider=workers_ai model=%s latency_ms=%s status=error job_id=%s detail=%s attempt=%s",
                model,
                latency_ms,
                job_id,
                error,
                attempt + 1,
            )
            if attempt == 0:
                continue
            return ProviderCallResult(
                provider="workers_ai",
                model=model,
                latency_ms=latency_ms,
                status="error",
                text=None,
                http_status=last_status,
            )
        last_status = status
        text = _extract_workers_text(payload or {})
        if status in {429, 500, 502, 503, 504}:
            logger.info(
                "drawing_reading provider=workers_ai model=%s latency_ms=%s status=http_%s job_id=%s attempt=%s",
                model,
                latency_ms,
                status,
                job_id,
                attempt + 1,
            )
            if attempt == 0:
                continue
            return ProviderCallResult(
                provider="workers_ai",
                model=model,
                latency_ms=latency_ms,
                status="error",
                text=text,
                http_status=status,
            )
        if status >= 400 or text is None:
            logger.info(
                "drawing_reading provider=workers_ai model=%s latency_ms=%s status=failed job_id=%s http_status=%s",
                model,
                latency_ms,
                job_id,
                status,
            )
            return ProviderCallResult(
                provider="workers_ai",
                model=model,
                latency_ms=latency_ms,
                status="failed",
                text=text,
                http_status=status,
            )
        logger.info(
            "drawing_reading provider=workers_ai model=%s latency_ms=%s status=ok job_id=%s",
            model,
            latency_ms,
            job_id,
        )
        return ProviderCallResult(
            provider="workers_ai",
            model=model,
            latency_ms=latency_ms,
            status="ok",
            text=text,
            http_status=status,
        )
    return ProviderCallResult(
        provider="workers_ai",
        model=model,
        latency_ms=0,
        status="error",
        text=None,
        http_status=last_status,
    )
