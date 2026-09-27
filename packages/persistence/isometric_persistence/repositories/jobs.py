"""Job and outbox repository."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from psycopg import Connection

JobKind = Literal["pipeline", "drawing_reading"]
JOB_KIND_PIPELINE: JobKind = "pipeline"
JOB_KIND_DRAWING_READING: JobKind = "drawing_reading"


@dataclass(frozen=True)
class JobLogRow:
    id: uuid.UUID
    job_id: uuid.UUID
    created_at: object
    level: str
    stage: str | None
    message: str
    detail: dict[str, Any]


@dataclass(frozen=True)
class JobRow:
    id: uuid.UUID
    document_id: uuid.UUID
    kind: JobKind
    state: str
    stage: str | None
    attempt: int
    input_hash: str
    options_hash: str
    pipeline_version: str
    profile_version: str
    result_revision_id: uuid.UUID | None
    error_code: str | None
    cancel_requested: bool
    created_at: object | None = None
    updated_at: object | None = None


class JobRepository:
    def create_with_outbox(
        self,
        conn: Connection[Any],
        *,
        job_id: uuid.UUID,
        document_id: uuid.UUID,
        state: str,
        input_hash: str,
        options_hash: str,
        pipeline_version: str,
        profile_version: str,
        event_key: str,
        event_type: str = "job.created",
        kind: JobKind = JOB_KIND_PIPELINE,
        dispatch_to_worker: bool = True,
    ) -> JobRow:
        conn.execute(
            """
            INSERT INTO drawing.jobs (
              id, document_id, kind, state, input_hash, options_hash,
              pipeline_version, profile_version
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                job_id,
                document_id,
                kind,
                state,
                input_hash,
                options_hash,
                pipeline_version,
                profile_version,
            ),
        )
        if dispatch_to_worker:
            conn.execute(
                """
                INSERT INTO drawing.outbox_events (event_type, aggregate_id, payload, event_key)
                VALUES (%s, %s, %s::jsonb, %s)
                """,
                (
                    event_type,
                    job_id,
                    json.dumps(
                        {"job_id": str(job_id), "document_id": str(document_id)}
                    ),
                    event_key,
                ),
            )
        return self.get(conn, job_id)  # type: ignore[return-value]

    def get(self, conn: Connection[Any], job_id: uuid.UUID) -> JobRow | None:
        row = conn.execute(
            """
            SELECT id, document_id, kind, state, stage, attempt, input_hash, options_hash,
                   pipeline_version, profile_version, result_revision_id, error_code,
                   cancel_requested, created_at, updated_at
            FROM drawing.jobs
            WHERE id = %s
            """,
            (job_id,),
        ).fetchone()
        return _row_to_job(row) if row else None

    def get_for_document(
        self, conn: Connection[Any], document_id: uuid.UUID
    ) -> JobRow | None:
        row = conn.execute(
            """
            SELECT id, document_id, kind, state, stage, attempt, input_hash, options_hash,
                   pipeline_version, profile_version, result_revision_id, error_code,
                   cancel_requested, created_at, updated_at
            FROM drawing.jobs
            WHERE document_id = %s AND kind = 'pipeline'
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (document_id,),
        ).fetchone()
        return _row_to_job(row) if row else None

    def get_newest_reading_job(
        self, conn: Connection[Any], document_id: uuid.UUID
    ) -> JobRow | None:
        row = conn.execute(
            """
            SELECT id, document_id, kind, state, stage, attempt, input_hash, options_hash,
                   pipeline_version, profile_version, result_revision_id, error_code,
                   cancel_requested, created_at, updated_at
            FROM drawing.jobs
            WHERE document_id = %s AND kind = 'drawing_reading'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (document_id,),
        ).fetchone()
        return _row_to_job(row) if row else None

    def has_active_pipeline_job(
        self, conn: Connection[Any], document_id: uuid.UUID
    ) -> bool:
        row = conn.execute(
            """
            SELECT 1
            FROM drawing.jobs
            WHERE document_id = %s
              AND kind = 'pipeline'
              AND state IN ('queued', 'running')
            LIMIT 1
            """,
            (document_id,),
        ).fetchone()
        return row is not None

    def recover_expired_leases(self, conn: Connection[Any]) -> list[uuid.UUID]:
        conn.execute(
            """
            UPDATE drawing.jobs
            SET state = 'canceled',
                lease_token = NULL,
                lease_expires_at = NULL,
                updated_at = now()
            WHERE state = 'running'
              AND result_revision_id IS NULL
              AND cancel_requested = true
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at < now()
            """
        )
        rows = conn.execute(
            """
            UPDATE drawing.jobs
            SET state = 'queued',
                lease_token = NULL,
                lease_expires_at = NULL,
                updated_at = now()
            WHERE state = 'running'
              AND result_revision_id IS NULL
              AND cancel_requested = false
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at < now()
            RETURNING id
            """
        ).fetchall()
        return [row["id"] for row in rows]

    def requeue_for_retry(self, conn: Connection[Any], job_id: uuid.UUID) -> None:
        conn.execute(
            """
            UPDATE drawing.jobs
            SET state = 'queued',
                lease_token = NULL,
                lease_expires_at = NULL,
                updated_at = now()
            WHERE id = %s
              AND result_revision_id IS NULL
            """,
            (job_id,),
        )

    def requeue_preserving_attempt(self, conn: Connection[Any], job_id: uuid.UUID) -> None:
        conn.execute(
            """
            UPDATE drawing.jobs
            SET state = 'queued',
                lease_token = NULL,
                lease_expires_at = NULL,
                attempt = GREATEST(attempt - 1, 0),
                updated_at = now()
            WHERE id = %s
              AND result_revision_id IS NULL
            """,
            (job_id,),
        )

    def get_latest_stage_warnings(
        self, conn: Connection[Any], job_id: uuid.UUID
    ) -> list[str]:
        row = conn.execute(
            """
            SELECT warnings
            FROM drawing.stage_runs
            WHERE job_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (job_id,),
        ).fetchone()
        if row is None:
            return []
        warnings = row["warnings"]
        if isinstance(warnings, list):
            return [str(item) for item in warnings]
        return []

    def claim(
        self,
        conn: Connection[Any],
        *,
        job_id: uuid.UUID,
        lease_seconds: int = 120,
    ) -> JobRow | None:
        token = uuid.uuid4()
        expires = datetime.now(UTC) + timedelta(seconds=lease_seconds)
        row = conn.execute(
            """
            UPDATE drawing.jobs
            SET state = 'running',
                stage = COALESCE(stage, 'fixture_process'),
                attempt = attempt + 1,
                lease_token = %s,
                lease_expires_at = %s,
                updated_at = now()
            WHERE id = %s
              AND state IN ('queued', 'running')
              AND cancel_requested = false
              AND result_revision_id IS NULL
              AND (lease_expires_at IS NULL OR lease_expires_at < now())
            RETURNING id, document_id, kind, state, stage, attempt, input_hash, options_hash,
                      pipeline_version, profile_version, result_revision_id, error_code,
                      cancel_requested, created_at, updated_at
            """,
            (token, expires, job_id),
        ).fetchone()
        return _row_to_job(row) if row else None

    def request_cancel(self, conn: Connection[Any], job_id: uuid.UUID) -> JobRow | None:
        row = conn.execute(
            """
            UPDATE drawing.jobs
            SET cancel_requested = true, updated_at = now()
            WHERE id = %s AND result_revision_id IS NULL
            RETURNING id, document_id, kind, state, stage, attempt, input_hash, options_hash,
                      pipeline_version, profile_version, result_revision_id, error_code,
                      cancel_requested, created_at, updated_at
            """,
            (job_id,),
        ).fetchone()
        return _row_to_job(row) if row else None

    def mark_canceled(self, conn: Connection[Any], job_id: uuid.UUID) -> None:
        conn.execute(
            """
            UPDATE drawing.jobs
            SET state = 'canceled',
                lease_token = NULL,
                lease_expires_at = NULL,
                updated_at = now()
            WHERE id = %s AND result_revision_id IS NULL
            """,
            (job_id,),
        )

    def mark_failed(
        self, conn: Connection[Any], job_id: uuid.UUID, error_code: str
    ) -> None:
        conn.execute(
            """
            UPDATE drawing.jobs
            SET state = 'failed',
                error_code = %s,
                lease_token = NULL,
                lease_expires_at = NULL,
                updated_at = now()
            WHERE id = %s AND result_revision_id IS NULL
            """,
            (error_code, job_id),
        )

    def complete_with_revision(
        self,
        conn: Connection[Any],
        *,
        job_id: uuid.UUID,
        revision_id: uuid.UUID,
    ) -> bool:
        row = conn.execute(
            """
            UPDATE drawing.jobs
            SET state = 'succeeded',
                stage = 'complete',
                result_revision_id = %s,
                error_code = NULL,
                lease_token = NULL,
                lease_expires_at = NULL,
                updated_at = now()
            WHERE id = %s
              AND result_revision_id IS NULL
              AND cancel_requested = false
            RETURNING id
            """,
            (revision_id, job_id),
        ).fetchone()
        return row is not None

    def complete_without_revision(
        self,
        conn: Connection[Any],
        *,
        job_id: uuid.UUID,
        stage: str = "complete",
    ) -> bool:
        row = conn.execute(
            """
            UPDATE drawing.jobs
            SET state = 'succeeded',
                stage = %s,
                error_code = NULL,
                lease_token = NULL,
                lease_expires_at = NULL,
                updated_at = now()
            WHERE id = %s
              AND result_revision_id IS NULL
              AND cancel_requested = false
            RETURNING id
            """,
            (stage, job_id),
        ).fetchone()
        return row is not None

    def insert_stage_run(
        self,
        conn: Connection[Any],
        *,
        job_id: uuid.UUID,
        stage: str,
        status: str,
        input_hash: str,
        producer_version: str,
        artifact_uri: str | None = None,
        metrics: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO drawing.stage_runs (
              job_id, stage, status, input_hash, producer_version,
              artifact_uri, metrics, warnings
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
            """,
            (
                job_id,
                stage,
                status,
                input_hash,
                producer_version,
                artifact_uri,
                json.dumps(metrics or {}),
                json.dumps(warnings or []),
            ),
        )
        conn.execute(
            """
            UPDATE drawing.jobs
            SET stage = %s, updated_at = now()
            WHERE id = %s
            """,
            (stage, job_id),
        )

    def append_job_log(
        self,
        conn: Connection[Any],
        *,
        job_id: uuid.UUID,
        message: str,
        level: str = "info",
        stage: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> JobLogRow:
        row = conn.execute(
            """
            INSERT INTO drawing.job_logs (job_id, level, stage, message, detail, created_at)
            VALUES (
              %s, %s, %s, %s, %s::jsonb,
              COALESCE(
                (
                  SELECT max(created_at) + interval '1 microsecond'
                  FROM drawing.job_logs
                  WHERE job_id = %s
                ),
                clock_timestamp()
              )
            )
            RETURNING id, job_id, created_at, level, stage, message, detail
            """,
            (job_id, level, stage, message, json.dumps(detail or {}), job_id),
        ).fetchone()
        conn.execute(
            """
            UPDATE drawing.jobs
            SET updated_at = now(),
                lease_expires_at = CASE
                  WHEN lease_token IS NOT NULL THEN now() + interval '120 seconds'
                  ELSE lease_expires_at
                END
            WHERE id = %s
            """,
            (job_id,),
        )
        return _row_to_job_log(row)

    def list_job_logs(
        self, conn: Connection[Any], job_id: uuid.UUID
    ) -> list[JobLogRow]:
        rows = conn.execute(
            """
            SELECT id, job_id, created_at, level, stage, message, detail
            FROM drawing.job_logs
            WHERE job_id = %s
            ORDER BY created_at ASC, id ASC
            """,
            (job_id,),
        ).fetchall()
        return [_row_to_job_log(row) for row in rows]


def _row_to_job_log(row: dict[str, Any]) -> JobLogRow:
    detail = row["detail"]
    if not isinstance(detail, dict):
        detail = {}
    return JobLogRow(
        id=row["id"],
        job_id=row["job_id"],
        created_at=row["created_at"],
        level=row["level"],
        stage=row["stage"],
        message=row["message"],
        detail=detail,
    )


def _row_to_job(row: dict[str, Any]) -> JobRow:
    kind = row.get("kind", JOB_KIND_PIPELINE)
    if kind not in (JOB_KIND_PIPELINE, JOB_KIND_DRAWING_READING):
        kind = JOB_KIND_PIPELINE
    return JobRow(
        id=row["id"],
        document_id=row["document_id"],
        kind=kind,  # type: ignore[arg-type]
        state=row["state"],
        stage=row["stage"],
        attempt=row["attempt"],
        input_hash=row["input_hash"],
        options_hash=row["options_hash"],
        pipeline_version=row["pipeline_version"],
        profile_version=row["profile_version"],
        result_revision_id=row["result_revision_id"],
        error_code=row["error_code"],
        cancel_requested=row["cancel_requested"],
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )
