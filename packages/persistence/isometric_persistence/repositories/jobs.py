"""Job and outbox repository."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from psycopg import Connection


@dataclass(frozen=True)
class JobRow:
    id: uuid.UUID
    document_id: uuid.UUID
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
    ) -> JobRow:
        conn.execute(
            """
            INSERT INTO drawing.jobs (
              id, document_id, state, input_hash, options_hash,
              pipeline_version, profile_version
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                job_id,
                document_id,
                state,
                input_hash,
                options_hash,
                pipeline_version,
                profile_version,
            ),
        )
        conn.execute(
            """
            INSERT INTO drawing.outbox_events (event_type, aggregate_id, payload, event_key)
            VALUES (%s, %s, %s::jsonb, %s)
            """,
            (
                event_type,
                job_id,
                json.dumps({"job_id": str(job_id), "document_id": str(document_id)}),
                event_key,
            ),
        )
        return self.get(conn, job_id)  # type: ignore[return-value]

    def get(self, conn: Connection[Any], job_id: uuid.UUID) -> JobRow | None:
        row = conn.execute(
            """
            SELECT id, document_id, state, stage, attempt, input_hash, options_hash,
                   pipeline_version, profile_version, result_revision_id, error_code,
                   cancel_requested, updated_at
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
            SELECT id, document_id, state, stage, attempt, input_hash, options_hash,
                   pipeline_version, profile_version, result_revision_id, error_code,
                   cancel_requested, updated_at
            FROM drawing.jobs
            WHERE document_id = %s
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (document_id,),
        ).fetchone()
        return _row_to_job(row) if row else None

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
            RETURNING id, document_id, state, stage, attempt, input_hash, options_hash,
                      pipeline_version, profile_version, result_revision_id, error_code,
                      cancel_requested
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
            RETURNING id, document_id, state, stage, attempt, input_hash, options_hash,
                      pipeline_version, profile_version, result_revision_id, error_code,
                      cancel_requested
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


def _row_to_job(row: dict[str, Any]) -> JobRow:
    return JobRow(
        id=row["id"],
        document_id=row["document_id"],
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
        updated_at=row.get("updated_at"),
    )
