"""Provider-neutral drawing reading orchestration."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from typing import Any

from .providers.fake import FakeDrawingReadingProviders
from .providers.gemini import call_gemini
from .providers.workers_ai import call_workers_ai, call_workers_ai_structure_notes
from .schema import (
    DRAWING_READING_SCHEMA_VERSION,
    DrawingReadingTable,
    DrawingReadingValidationError,
    validate_table,
)
from .settings import DrawingReadingSettings, load_drawing_reading_settings


@dataclass(frozen=True)
class DrawingReadingSuccess:
    table: DrawingReadingTable
    provider: str
    model: str


@dataclass(frozen=True)
class DrawingReadingFailure:
    error_code: str
    detail: dict[str, object] | None = None


def _parse_json_text(text: str) -> object:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return json.loads(stripped)


def _sanitize_groups_payload(payload: dict[str, object]) -> dict[str, object]:
    groups = payload.get("groups")
    if not isinstance(groups, list):
        return payload
    for group in groups:
        if not isinstance(group, dict):
            continue
        rows = group.get("rows")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            location = row.get("location")
            reading = row.get("reading")
            if not (isinstance(location, str) and location.strip()):
                fallback = reading.strip() if isinstance(reading, str) else ""
                row["location"] = fallback[:80] if fallback else "drawing"
    return payload


def _try_validate_provider_text(text: str | None) -> DrawingReadingTable | None:
    if text is None or not text.strip():
        return None
    try:
        payload = _parse_json_text(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or "groups" not in payload:
        return None
    payload = _sanitize_groups_payload(payload)
    try:
        return validate_table({"groups": payload["groups"]})
    except (DrawingReadingValidationError, AttributeError, TypeError):
        return None


def _settings_with_env_fake(
    settings: DrawingReadingSettings | None,
) -> DrawingReadingSettings:
    cfg = settings or load_drawing_reading_settings()
    fake = os.environ.get("ISOMETRIC_FAKE_DRAWING_READING", "").strip()
    if fake:
        return replace(cfg, fake_mode=fake)
    return cfg


def read_drawing_table(
    *,
    image_bytes: bytes,
    job_id: str,
    settings: DrawingReadingSettings | None = None,
) -> DrawingReadingSuccess | DrawingReadingFailure:
    cfg = _settings_with_env_fake(settings)
    if cfg.fake_mode:
        fake = FakeDrawingReadingProviders(cfg.fake_mode)
        workers = fake.call_workers(image_bytes=image_bytes)
        table = _try_validate_provider_text(workers.body)
        if table is not None:
            return DrawingReadingSuccess(
                table=table, provider="fake_workers", model=cfg.fake_mode
            )
        gemini = fake.call_gemini(image_bytes=image_bytes)
        table = _try_validate_provider_text(gemini.body)
        if table is not None:
            return DrawingReadingSuccess(
                table=table, provider="fake_gemini", model=cfg.fake_mode
            )
        return DrawingReadingFailure(error_code="reading_failed")

    workers = call_workers_ai(settings=cfg, image_bytes=image_bytes, job_id=job_id)
    table = _try_validate_provider_text(workers.text)
    if table is not None:
        return DrawingReadingSuccess(
            table=table, provider=workers.provider, model=workers.model
        )

    structured = workers
    if workers.text and workers.status in {"ok", "failed"}:
        structured = call_workers_ai_structure_notes(
            settings=cfg, notes=workers.text, job_id=job_id
        )
        table = _try_validate_provider_text(structured.text)
        if table is not None:
            return DrawingReadingSuccess(
                table=table,
                provider=f"{structured.provider}_structure",
                model=structured.model,
            )

    gemini = call_gemini(settings=cfg, image_bytes=image_bytes, job_id=job_id)
    table = _try_validate_provider_text(gemini.text)
    if table is not None:
        return DrawingReadingSuccess(
            table=table, provider=gemini.provider, model=gemini.model
        )
    return DrawingReadingFailure(
        error_code="reading_failed",
        detail={
            "workers_ai": {
                "status": workers.status,
                "http_status": workers.http_status,
            },
            "workers_ai_structure": {
                "status": structured.status,
                "http_status": structured.http_status,
            },
            "gemini": {
                "status": gemini.status,
                "http_status": gemini.http_status,
            },
        },
    )


def build_artifact_payload(
    *,
    status: str,
    table: DrawingReadingTable | None,
    provider: str | None,
    model: str | None,
) -> dict[str, Any]:
    from .schema import PROMPT_VERSION, table_to_json

    payload: dict[str, Any] = {
        "schema_version": DRAWING_READING_SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "status": status,
    }
    if provider:
        payload["provider"] = provider
    if model:
        payload["model"] = model
    if table is not None:
        payload["groups"] = table_to_json(table)["groups"]
    return payload
