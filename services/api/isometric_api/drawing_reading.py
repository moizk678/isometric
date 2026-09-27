"""Drawing reading API helpers."""

from __future__ import annotations

import json
from typing import Any

from isometric_persistence.artifacts import ArtifactStore
from isometric_persistence.errors import PersistenceError
from isometric_persistence.keys import document_reading_key
from isometric_persistence.repositories.jobs import JobRow
from isometric_worker.drawing_reading.schema import (
    DrawingReadingValidationError,
    table_to_json,
    validate_table,
)


def build_drawing_reading_response(
    *,
    reading_job: JobRow | None,
    store: ArtifactStore,
) -> dict[str, Any]:
    if reading_job is None:
        return {"status": "absent"}

    if reading_job.state in {"queued", "running"}:
        return {
            "status": "pending",
            "job_id": str(reading_job.id),
        }

    if reading_job.state == "failed":
        return {
            "status": "unavailable",
            "job_id": str(reading_job.id),
            "error_code": reading_job.error_code or "reading_failed",
        }

    if reading_job.state != "succeeded":
        return {
            "status": "pending",
            "job_id": str(reading_job.id),
        }

    key = document_reading_key(reading_job.document_id, reading_job.id)
    try:
        raw = store.read(key)
    except (FileNotFoundError, PersistenceError):
        return {
            "status": "unavailable",
            "job_id": str(reading_job.id),
            "error_code": "artifact_missing",
        }

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "status": "unavailable",
            "job_id": str(reading_job.id),
            "error_code": "artifact_invalid",
        }

    if not isinstance(payload, dict):
        return {
            "status": "unavailable",
            "job_id": str(reading_job.id),
            "error_code": "artifact_invalid",
        }

    status = payload.get("status")
    if status == "disabled":
        return {
            "status": "disabled",
            "job_id": str(reading_job.id),
        }

    try:
        table = validate_table({"groups": payload.get("groups")})
    except (DrawingReadingValidationError, TypeError):
        return {
            "status": "unavailable",
            "job_id": str(reading_job.id),
            "error_code": "artifact_invalid",
        }

    body: dict[str, Any] = {
        "status": "ready",
        "job_id": str(reading_job.id),
        "groups": table_to_json(table)["groups"],
    }
    for field in ("schema_version", "prompt_version", "provider", "model"):
        value = payload.get(field)
        if isinstance(value, str) and value:
            body[field] = value
    return body
