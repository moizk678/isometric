"""Fixture-backed job processor (no CV)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from isometric_persistence.artifacts import ArtifactStore
from isometric_persistence.db import DatabasePool
from isometric_persistence.errors import ConflictError, PersistenceError
from isometric_persistence.publishing import PublishExport, RevisionPublisher
from isometric_persistence.repositories.jobs import JobRepository
from isometric_persistence.repositories.revisions import RevisionRepository
from isometric_pipeline.render import (
    STYLE_PROFILE_VERSION,
    SYMBOL_LIBRARY_VERSION,
    load_symbol_library,
    rasterize_preview,
    render_svg,
)
from isometric_pipeline.render.versions import RENDERER_VERSION
from isometric_pipeline.scene import load_scene
from psycopg import OperationalError
from psycopg.errors import UniqueViolation

from .queue import JobQueue

FIXTURE_SCENE = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "scene-schema"
    / "fixtures"
    / "valid"
    / "annotation.json"
)
PIPELINE_VERSION = "fixture@1.0.0"
REVISION_NAMESPACE = uuid.UUID("8d8a0c3e-6b1a-4f0e-9c2d-1a7e5b4c9d20")
MAX_ATTEMPTS = 3


def revision_id_for_job(job_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(REVISION_NAMESPACE, str(job_id))


def _fixture_scene_bytes(document_id: uuid.UUID, revision_id: uuid.UUID) -> bytes:
    payload = json.loads(FIXTURE_SCENE.read_text(encoding="utf-8"))
    payload["documentId"] = str(document_id)
    payload["revisionId"] = str(revision_id)
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _complete_if_revision_exists(
    pool: DatabasePool,
    jobs: JobRepository,
    revs: RevisionRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    revision_id: uuid.UUID,
) -> bool:
    with pool.connection() as conn:
        existing = revs.get_revision(conn, revision_id)
        if existing is None or existing.document_id != document_id:
            return False
        jobs.complete_with_revision(conn, job_id=job_id, revision_id=revision_id)
        conn.commit()
        return True


def process_job(
    pool: DatabasePool,
    store: ArtifactStore,
    job_id: uuid.UUID,
    *,
    queue: JobQueue | None = None,
) -> None:
    jobs = JobRepository()
    revs = RevisionRepository()
    publisher = RevisionPublisher(store)
    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None:
            return
        if job.result_revision_id is not None:
            return
        if job.cancel_requested:
            jobs.mark_canceled(conn, job_id)
            conn.commit()
            return
        claimed = jobs.claim(conn, job_id=job_id)
        if claimed is None:
            return
        conn.commit()

    document_id = claimed.document_id
    revision_id = revision_id_for_job(job_id)
    if _complete_if_revision_exists(
        pool,
        jobs,
        revs,
        job_id=job_id,
        document_id=document_id,
        revision_id=revision_id,
    ):
        return

    if not FIXTURE_SCENE.is_file():
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "missing_artifact")
            conn.commit()
        return

    scene_bytes = _fixture_scene_bytes(document_id, revision_id)
    try:
        catalog = load_symbol_library(SYMBOL_LIBRARY_VERSION)
        scene = load_scene(scene_bytes.decode("utf-8"), catalog=catalog)
        svg = render_svg(scene, SYMBOL_LIBRARY_VERSION, STYLE_PROFILE_VERSION).svg
        png = rasterize_preview(svg).png
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_invalid")
            conn.commit()
        return

    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return
        jobs.insert_stage_run(
            conn,
            job_id=job_id,
            stage="fixture_process",
            status="running",
            input_hash=job.input_hash,
            producer_version=PIPELINE_VERSION,
        )
        conn.commit()

    try:
        with pool.connection() as conn:
            job = jobs.get(conn, job_id)
            if (
                job is None
                or job.cancel_requested
                or job.result_revision_id is not None
            ):
                if job and job.cancel_requested:
                    jobs.mark_canceled(conn, job_id)
                    conn.commit()
                return
            result = publisher.publish(
                conn,
                document_id=document_id,
                expected_parent_revision_id=None,
                schema_version="1.0",
                scene_bytes=scene_bytes,
                author_type="machine",
                review_state="review_required",
                validation_status="valid",
                revision_id=revision_id,
                exports=[
                    PublishExport(
                        kind="svg",
                        format="svg",
                        data=svg,
                        renderer_version=RENDERER_VERSION,
                    ),
                    PublishExport(
                        kind="preview",
                        format="png",
                        data=png,
                        renderer_version=RENDERER_VERSION,
                    ),
                ],
            )
            completed = jobs.complete_with_revision(
                conn, job_id=job_id, revision_id=result.revision_id
            )
            if completed:
                jobs.insert_stage_run(
                    conn,
                    job_id=job_id,
                    stage="fixture_process",
                    status="succeeded",
                    input_hash=job.input_hash,
                    producer_version=PIPELINE_VERSION,
                    artifact_uri=result.scene_key,
                )
            conn.commit()
    except (ConflictError, UniqueViolation):
        if _complete_if_revision_exists(
            pool,
            jobs,
            revs,
            job_id=job_id,
            document_id=document_id,
            revision_id=revision_id,
        ):
            return
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_failed")
            conn.commit()
    except PersistenceError:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "missing_artifact")
            conn.commit()
    except (OSError, OperationalError):
        with pool.connection() as conn:
            job = jobs.get(conn, job_id)
            if job is None or job.result_revision_id is not None:
                return
            if job.attempt < MAX_ATTEMPTS:
                jobs.requeue_for_retry(conn, job_id)
                conn.commit()
                if queue is not None:
                    queue.enqueue(str(job_id))
            else:
                jobs.mark_failed(conn, job_id, "worker_exhausted")
                conn.commit()
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_failed")
            conn.commit()
