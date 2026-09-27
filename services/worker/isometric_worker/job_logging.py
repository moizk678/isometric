"""Persist job processing lines for live UI polling."""

from __future__ import annotations

import uuid
from typing import Any

from isometric_persistence.db import DatabasePool
from isometric_persistence.repositories.jobs import JobRepository


def commit_job_log(
    pool: DatabasePool,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    message: str,
    level: str = "info",
    stage: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    with pool.connection() as conn:
        jobs.append_job_log(
            conn,
            job_id=job_id,
            message=message,
            level=level,
            stage=stage,
            detail=detail,
        )
        conn.commit()


def log_stage_started(
    pool: DatabasePool,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    stage: str,
) -> None:
    commit_job_log(
        pool,
        jobs,
        job_id=job_id,
        stage=stage,
        message=f"Starting {stage}",
    )


def log_stage_finished(
    pool: DatabasePool,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    stage: str,
    metrics: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> None:
    detail: dict[str, Any] = {}
    if metrics:
        detail["metrics"] = metrics
    commit_job_log(
        pool,
        jobs,
        job_id=job_id,
        stage=stage,
        message=f"Finished {stage}",
        detail=detail or None,
    )
    for warning in warnings or []:
        commit_job_log(
            pool,
            jobs,
            job_id=job_id,
            stage=stage,
            level="warning",
            message=warning,
        )


def log_job_error(
    pool: DatabasePool,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    message: str,
    error_code: str | None = None,
    stage: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {}
    if error_code:
        payload["error_code"] = error_code
    if detail:
        payload.update(detail)
    detail = payload or None
    commit_job_log(
        pool,
        jobs,
        job_id=job_id,
        stage=stage,
        level="error",
        message=message,
        detail=detail,
    )
