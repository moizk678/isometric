"""Worker entry for drawing_reading jobs."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from isometric_persistence.artifacts import ArtifactStore
from isometric_persistence.db import DatabasePool
from isometric_persistence.errors import PersistenceError
from isometric_persistence.keys import document_page_key, document_reading_key
from isometric_persistence.repositories.jobs import JobRepository, JobRow

from .drawing_reading.reader import (
    DrawingReadingFailure,
    DrawingReadingSuccess,
    _settings_with_env_fake,
    build_artifact_payload,
    read_drawing_table,
)
from .job_logging import commit_job_log, log_job_error
from .queue import JobQueue

logger = logging.getLogger(__name__)

PAGE_WAIT_MAX = timedelta(minutes=10)


def _reading_job_too_old(job: JobRow) -> bool:
    created = job.created_at
    if created is None:
        return False
    if isinstance(created, datetime):
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        return datetime.now(UTC) - created > PAGE_WAIT_MAX
    return False


def process_drawing_reading_job(
    pool: DatabasePool,
    store: ArtifactStore,
    job: JobRow,
    *,
    queue: JobQueue | None = None,
) -> None:
    jobs = JobRepository()
    job_id = job.id
    document_id = job.document_id
    page_key = document_page_key(document_id)
    page_bytes: bytes | None = None
    try:
        page_bytes = store.read(page_key)
    except (FileNotFoundError, PersistenceError):
        page_bytes = None

    if page_bytes is None:
        with pool.connection() as conn:
            active_pipeline = jobs.has_active_pipeline_job(conn, document_id)
            too_old = _reading_job_too_old(job)
            if active_pipeline and not too_old:
                jobs.requeue_preserving_attempt(conn, job_id)
                conn.commit()
                if queue is not None:
                    queue.enqueue(str(job_id))
                commit_job_log(
                    pool,
                    jobs,
                    job_id=job_id,
                    message="Waiting for page.png from pipeline",
                    stage="drawing_reading",
                )
                return
            log_job_error(
                pool,
                jobs,
                job_id=job_id,
                message="page.png missing for drawing reading",
                error_code="missing_page",
                stage="drawing_reading",
            )
            jobs.mark_failed(conn, job_id, "missing_page")
            conn.commit()
        return

    settings = _settings_with_env_fake(None)
    artifact_key = document_reading_key(document_id, job_id)
    if not settings.vision_enabled and settings.fake_mode is None:
        payload = build_artifact_payload(
            status="disabled", table=None, provider=None, model=None
        )
        store.write_immutable(artifact_key, json.dumps(payload).encode("utf-8"))
        with pool.connection() as conn:
            jobs.complete_without_revision(conn, job_id=job_id)
            conn.commit()
        commit_job_log(
            pool,
            jobs,
            job_id=job_id,
            message="Drawing reading disabled",
            stage="drawing_reading",
        )
        return

    result = read_drawing_table(image_bytes=page_bytes, job_id=str(job_id))
    if isinstance(result, DrawingReadingFailure):
        log_job_error(
            pool,
            jobs,
            job_id=job_id,
            message="Drawing reading failed",
            error_code=result.error_code,
            stage="drawing_reading",
            detail=result.detail,
        )
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, result.error_code)
            conn.commit()
        return

    assert isinstance(result, DrawingReadingSuccess)
    payload = build_artifact_payload(
        status="ready",
        table=result.table,
        provider=result.provider,
        model=result.model,
    )
    store.write_immutable(artifact_key, json.dumps(payload).encode("utf-8"))
    with pool.connection() as conn:
        jobs.complete_without_revision(conn, job_id=job_id)
        conn.commit()
    commit_job_log(
        pool,
        jobs,
        job_id=job_id,
        message="Drawing reading complete",
        stage="drawing_reading",
        detail={"provider": result.provider, "model": result.model},
    )
