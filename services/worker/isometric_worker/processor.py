"""Fixture-backed job processor (no CV)."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from isometric_persistence.artifacts import ArtifactStore
from isometric_persistence.db import DatabasePool
from isometric_persistence.errors import ConflictError, PersistenceError
from isometric_persistence.keys import (
    document_axes_metadata_key,
    document_centerlines_metadata_key,
    document_color_mask_key,
    document_crop_key,
    document_display_key,
    document_mask_key,
    document_masks_metadata_key,
    document_normalize_metadata_key,
    document_page_key,
    document_primitives_metadata_key,
    document_regions_metadata_key,
    document_snapped_primitives_metadata_key,
    document_symbol_candidates_metadata_key,
    document_text_candidates_metadata_key,
    document_topology_metadata_key,
    job_stage_artifact_key,
)
from isometric_persistence.publishing import PublishExport, RevisionPublisher
from isometric_persistence.repositories.documents import DocumentRepository
from isometric_persistence.repositories.jobs import JobRepository
from isometric_persistence.repositories.revisions import (
    RevisionRepository,
    SceneRevisionRow,
)
from isometric_pipeline.centerlines.stage import (
    ExtractCenterlinesResult,
    extract_centerlines,
)
from isometric_pipeline.masks.artifact import MasksMetadata
from isometric_pipeline.masks.stage import SeparateMasksResult, separate_masks
from isometric_pipeline.normalize.page import (
    NormalizeLimits,
    NormalizePageError,
    normalize_page,
)
from isometric_pipeline.ocr.artifact import TextCandidatesMetadata
from isometric_pipeline.ocr.stage import transcribe_regions
from isometric_pipeline.primitives.artifact import PrimitivesMetadata
from isometric_pipeline.primitives.stage import fit_primitives
from isometric_pipeline.regions.artifact import RegionsMetadata
from isometric_pipeline.regions.stage import detect_regions
from isometric_pipeline.render import (
    STYLE_PROFILE_VERSION,
    SYMBOL_LIBRARY_VERSION,
    load_symbol_library,
    rasterize_preview,
    render_svg,
)
from isometric_pipeline.render.versions import RENDERER_VERSION
from isometric_pipeline.scene import load_scene
from isometric_pipeline.snapping.artifact import SnappedPrimitivesMetadata
from isometric_pipeline.snapping.stage import snap_primitives
from isometric_pipeline.symbol_candidates.stage import classify_symbol_regions
from isometric_pipeline.topology.artifact import TopologyMetadata
from isometric_pipeline.topology.stage import infer_topology
from psycopg import Connection, OperationalError
from psycopg.errors import UniqueViolation

from .fixture_fit import (
    FixtureReviewItem,
    fit_fixture_scene,
    fixture_review_items,
    read_source_frame,
)
from .queue import JobQueue
from .stages import (
    CLASSIFY_SYMBOL_REGIONS_VERSION,
    DETECT_REGIONS_VERSION,
    EXTRACT_CENTERLINES_VERSION,
    FIT_PRIMITIVES_VERSION,
    INFER_TOPOLOGY_VERSION,
    NORMALIZE_PAGE_VERSION,
    SEPARATE_MASKS_VERSION,
    SNAP_PRIMITIVES_VERSION,
    STAGE_CLASSIFY_SYMBOL_REGIONS,
    STAGE_DETECT_REGIONS,
    STAGE_EXTRACT_CENTERLINES,
    STAGE_FIT_PRIMITIVES,
    STAGE_FIXTURE_PROCESS,
    STAGE_INFER_TOPOLOGY,
    STAGE_NORMALIZE_PAGE,
    STAGE_SEPARATE_MASKS,
    STAGE_SNAP_PRIMITIVES,
    STAGE_TRANSCRIBE_REGIONS,
    TRANSCRIBE_REGIONS_VERSION,
)

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


class _ReviewItemRevisionRepository(RevisionRepository):
    """Inserts fixture review items in the publish transaction, before commit.

    The revision ID is deterministic per job, so a repeated publish fails on the
    revision insert and rolls back these items with it.
    """

    def __init__(self, review_items: list[FixtureReviewItem]) -> None:
        super().__init__()
        self._review_items = review_items

    def insert_revision(self, conn: Connection[Any], **kwargs: Any) -> SceneRevisionRow:
        row = super().insert_revision(conn, **kwargs)
        for item in self._review_items:
            self.insert_review_item(
                conn,
                issue_key=item.issue_key,
                revision_id=row.id,
                issue_type=item.issue_type,
                severity=item.severity,
                state="open",
                object_id=item.object_id,
            )
        return row


def _fitted_scene(
    source_bytes: bytes, document_id: uuid.UUID, revision_id: uuid.UUID
) -> tuple[bytes, list[FixtureReviewItem]]:
    fixture = json.loads(FIXTURE_SCENE.read_text(encoding="utf-8"))
    payload = fit_fixture_scene(fixture, read_source_frame(source_bytes))
    payload["documentId"] = str(document_id)
    payload["revisionId"] = str(revision_id)
    scene_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return scene_bytes, fixture_review_items(payload)


def _retry_or_exhaust(
    pool: DatabasePool,
    jobs: JobRepository,
    job_id: uuid.UUID,
    queue: JobQueue | None,
) -> None:
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


def _execute_normalize_page(
    pool: DatabasePool,
    store: ArtifactStore,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    source_bytes: bytes,
    input_hash: str,
    queue: JobQueue | None,
) -> bool:
    """Run normalize_page and persist artifacts. Returns False if the job stopped."""
    display_key = document_display_key(document_id)
    page_key = document_page_key(document_id)
    meta_key = document_normalize_metadata_key(document_id)

    try:
        normalized = normalize_page(
            source_bytes,
            limits=NormalizeLimits(),
            display_uri=display_key,
            page_uri=page_key,
        )
    except NormalizePageError as err:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, err.code)
            conn.commit()
        return False
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_invalid")
            conn.commit()
        return False

    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return False

    try:
        store.write_immutable(display_key, normalized.display_png)
        store.write_immutable(page_key, normalized.page_png)
        meta_bytes = json.dumps(
            normalized.metadata.to_wire(),
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        store.write_immutable(meta_key, meta_bytes)
        overlay_key = (
            f"{job_stage_artifact_key(job_id, STAGE_NORMALIZE_PAGE, normalized.content_hash)}"
            "/corner-overlay.png"
        )
        store.write_immutable(overlay_key, normalized.overlay_png)
    except (OSError, PersistenceError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    metrics: dict[str, Any] = {key: value for key, value in normalized.metrics.items()}
    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return False
        jobs.insert_stage_run(
            conn,
            job_id=job_id,
            stage=STAGE_NORMALIZE_PAGE,
            status=normalized.status,
            input_hash=input_hash,
            producer_version=NORMALIZE_PAGE_VERSION,
            artifact_uri=meta_key,
            metrics=metrics,
            warnings=normalized.warnings,
        )
        conn.commit()
    return True


_SEPARATE_MASK_FILE_NAMES = {
    "grid": "grid",
    "retained_ink": "retained-ink",
    "black_ink": "black-ink",
    "unclassified_ink": "unclassified-ink",
}


def _job_still_active(
    pool: DatabasePool,
    jobs: JobRepository,
    job_id: uuid.UUID,
) -> bool:
    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return False
    return True


def _execute_separate_masks(
    pool: DatabasePool,
    store: ArtifactStore,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    input_hash: str,
    queue: JobQueue | None,
) -> SeparateMasksResult | None:
    page_key = document_page_key(document_id)
    masks_meta_key = document_masks_metadata_key(document_id)
    try:
        page_png = store.read(page_key)
    except (FileNotFoundError, PersistenceError, OSError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return None

    try:
        separated = separate_masks(
            page_png,
            document_id=str(document_id),
            page_uri=page_key,
            masks_json_uri=masks_meta_key,
        )
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_invalid")
            conn.commit()
        return None

    if not _job_still_active(pool, jobs, job_id):
        return None

    try:
        for mask_key, file_name in _SEPARATE_MASK_FILE_NAMES.items():
            store.write_immutable(
                document_mask_key(document_id, file_name),
                separated.masks[mask_key],
            )
        for layer_id, layer_png in separated.color_layer_masks.items():
            store.write_immutable(
                document_color_mask_key(document_id, layer_id),
                layer_png,
            )
        overlay_key = (
            f"{job_stage_artifact_key(job_id, STAGE_SEPARATE_MASKS, separated.content_hash)}"
            "/overlay.png"
        )
        store.write_immutable(overlay_key, separated.overlay_png)
    except (OSError, PersistenceError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return None

    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return None
        jobs.insert_stage_run(
            conn,
            job_id=job_id,
            stage=STAGE_SEPARATE_MASKS,
            status=separated.status,
            input_hash=input_hash,
            producer_version=SEPARATE_MASKS_VERSION,
            artifact_uri=overlay_key,
            metrics=separated.metrics,
            warnings=separated.warnings,
        )
        conn.commit()
    return separated


def _execute_detect_regions(
    pool: DatabasePool,
    store: ArtifactStore,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    input_hash: str,
    queue: JobQueue | None,
    separated: SeparateMasksResult,
) -> bool:
    page_key = document_page_key(document_id)
    masks_meta_key = document_masks_metadata_key(document_id)
    regions_meta_key = document_regions_metadata_key(document_id)
    try:
        page_png = store.read(page_key)
        retained_png = separated.masks["retained_ink"]
        black_png = separated.masks["black_ink"]
    except (FileNotFoundError, PersistenceError, OSError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    try:
        detected = detect_regions(
            page_png,
            separated.metadata,
            retained_png,
            black_png,
            document_id=str(document_id),
            masks_json_uri=masks_meta_key,
        )
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_invalid")
            conn.commit()
        return False

    if not _job_still_active(pool, jobs, job_id):
        return False

    try:
        store.write_immutable(
            document_mask_key(document_id, "protection"),
            detected.protection_png,
        )
        store.write_immutable(
            document_mask_key(document_id, "geometry-ink"),
            detected.geometry_ink_png,
        )
        store.write_immutable(masks_meta_key, detected.masks_json)
        store.write_immutable(regions_meta_key, detected.regions_json)
        for crop_id, crop_png in detected.crop_pngs.items():
            store.write_immutable(document_crop_key(document_id, crop_id), crop_png)
        overlay_key = (
            f"{job_stage_artifact_key(job_id, STAGE_DETECT_REGIONS, detected.content_hash)}"
            "/overlay.png"
        )
        store.write_immutable(overlay_key, detected.overlay_png)
    except (OSError, PersistenceError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return False
        jobs.insert_stage_run(
            conn,
            job_id=job_id,
            stage=STAGE_DETECT_REGIONS,
            status=detected.status,
            input_hash=input_hash,
            producer_version=DETECT_REGIONS_VERSION,
            artifact_uri=regions_meta_key,
            metrics=detected.metrics,
            warnings=detected.warnings,
        )
        conn.commit()
    return True


def _execute_extract_centerlines(
    pool: DatabasePool,
    store: ArtifactStore,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    input_hash: str,
    queue: JobQueue | None,
    separated: SeparateMasksResult,
) -> ExtractCenterlinesResult | None:
    page_key = document_page_key(document_id)
    masks_meta_key = document_masks_metadata_key(document_id)
    regions_meta_key = document_regions_metadata_key(document_id)
    centerlines_meta_key = document_centerlines_metadata_key(document_id)
    try:
        page_png = store.read(page_key)
        geometry_ink = store.read(document_mask_key(document_id, "geometry-ink"))
        masks_wire = json.loads(store.read(masks_meta_key).decode("utf-8"))
        masks_metadata = MasksMetadata.model_validate(masks_wire)
        regions_wire = json.loads(store.read(regions_meta_key).decode("utf-8"))
        regions_metadata = RegionsMetadata.model_validate(regions_wire)
    except (FileNotFoundError, PersistenceError, OSError, json.JSONDecodeError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return None

    try:
        extracted = extract_centerlines(
            page_png,
            geometry_ink,
            separated.color_layer_masks,
            masks_metadata,
            regions_metadata,
            document_id=str(document_id),
            masks_json_uri=masks_meta_key,
            regions_json_uri=regions_meta_key,
            centerlines_json_uri=centerlines_meta_key,
        )
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_invalid")
            conn.commit()
        return None

    if not _job_still_active(pool, jobs, job_id):
        return None

    try:
        store.write_immutable(centerlines_meta_key, extracted.centerlines_json)
        for crop_id, crop_png in extracted.crop_pngs.items():
            store.write_immutable(document_crop_key(document_id, crop_id), crop_png)
        overlay_key = (
            f"{job_stage_artifact_key(job_id, STAGE_EXTRACT_CENTERLINES, extracted.content_hash)}"
            "/overlay.png"
        )
        store.write_immutable(overlay_key, extracted.overlay_png)
    except (OSError, PersistenceError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return None

    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return None
        jobs.insert_stage_run(
            conn,
            job_id=job_id,
            stage=STAGE_EXTRACT_CENTERLINES,
            status=extracted.status,
            input_hash=input_hash,
            producer_version=EXTRACT_CENTERLINES_VERSION,
            artifact_uri=centerlines_meta_key,
            metrics=extracted.metrics,
            warnings=extracted.warnings,
        )
        conn.commit()
    return extracted


def _execute_fit_primitives(
    pool: DatabasePool,
    store: ArtifactStore,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    input_hash: str,
    queue: JobQueue | None,
    separated: SeparateMasksResult,
    extracted: ExtractCenterlinesResult,
) -> bool:
    page_key = document_page_key(document_id)
    masks_meta_key = document_masks_metadata_key(document_id)
    regions_meta_key = document_regions_metadata_key(document_id)
    centerlines_meta_key = document_centerlines_metadata_key(document_id)
    primitives_meta_key = document_primitives_metadata_key(document_id)
    try:
        page_png = store.read(page_key)
        layer_masks: dict[str, bytes] = {
            "geometry": store.read(document_mask_key(document_id, "geometry-ink"))
        }
        for layer_id, layer_png in separated.color_layer_masks.items():
            layer_masks[layer_id] = layer_png
    except (FileNotFoundError, PersistenceError, OSError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    try:
        fitted = fit_primitives(
            page_png,
            extracted.metadata,
            layer_masks,
            centerlines_json_uri=centerlines_meta_key,
            masks_json_uri=masks_meta_key,
            regions_json_uri=regions_meta_key,
            primitives_json_uri=primitives_meta_key,
        )
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_invalid")
            conn.commit()
        return False

    if not _job_still_active(pool, jobs, job_id):
        return False

    try:
        store.write_immutable(primitives_meta_key, fitted.primitives_json)
        overlay_key = (
            f"{job_stage_artifact_key(job_id, STAGE_FIT_PRIMITIVES, fitted.content_hash)}"
            "/overlay.png"
        )
        store.write_immutable(overlay_key, fitted.overlay_png)
    except (OSError, PersistenceError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return False
        jobs.insert_stage_run(
            conn,
            job_id=job_id,
            stage=STAGE_FIT_PRIMITIVES,
            status=fitted.status,
            input_hash=input_hash,
            producer_version=FIT_PRIMITIVES_VERSION,
            artifact_uri=primitives_meta_key,
            metrics=fitted.metrics,
            warnings=fitted.warnings,
        )
        conn.commit()
    return True


def _execute_snap_primitives(
    pool: DatabasePool,
    store: ArtifactStore,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    input_hash: str,
    queue: JobQueue | None,
) -> bool:
    page_key = document_page_key(document_id)
    masks_meta_key = document_masks_metadata_key(document_id)
    regions_meta_key = document_regions_metadata_key(document_id)
    primitives_meta_key = document_primitives_metadata_key(document_id)
    axes_meta_key = document_axes_metadata_key(document_id)
    snapped_meta_key = document_snapped_primitives_metadata_key(document_id)
    try:
        page_png = store.read(page_key)
        primitives_wire = json.loads(store.read(primitives_meta_key).decode("utf-8"))
        primitives_metadata = PrimitivesMetadata.model_validate(primitives_wire)
        masks_wire = json.loads(store.read(masks_meta_key).decode("utf-8"))
        masks_metadata = MasksMetadata.model_validate(masks_wire)
        regions_wire = json.loads(store.read(regions_meta_key).decode("utf-8"))
        regions_metadata = RegionsMetadata.model_validate(regions_wire)
        grid_mask_png = None
        try:
            grid_mask_png = store.read(document_mask_key(document_id, "grid"))
        except (FileNotFoundError, PersistenceError, OSError):
            grid_mask_png = None
    except (FileNotFoundError, PersistenceError, OSError, json.JSONDecodeError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    grid_confidence = masks_metadata.diagnostics.grid_confidence

    try:
        snapped = snap_primitives(
            page_png,
            primitives_metadata,
            primitives_json_uri=primitives_meta_key,
            axes_json_uri=axes_meta_key,
            snapped_primitives_json_uri=snapped_meta_key,
            masks_json_uri=masks_meta_key,
            regions=regions_metadata,
            regions_json_uri=regions_meta_key,
            grid_mask_png=grid_mask_png,
            grid_confidence=grid_confidence,
        )
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_invalid")
            conn.commit()
        return False

    if not _job_still_active(pool, jobs, job_id):
        return False

    try:
        store.write_immutable(axes_meta_key, snapped.axes_json)
        store.write_immutable(snapped_meta_key, snapped.snapped_primitives_json)
        overlay_key = (
            f"{job_stage_artifact_key(job_id, STAGE_SNAP_PRIMITIVES, snapped.content_hash)}"
            "/overlay.png"
        )
        store.write_immutable(overlay_key, snapped.overlay_png)
    except (OSError, PersistenceError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return False
        jobs.insert_stage_run(
            conn,
            job_id=job_id,
            stage=STAGE_SNAP_PRIMITIVES,
            status=snapped.status,
            input_hash=input_hash,
            producer_version=SNAP_PRIMITIVES_VERSION,
            artifact_uri=snapped_meta_key,
            metrics=snapped.metrics,
            warnings=snapped.warnings,
        )
        conn.commit()
    return True


def _execute_infer_topology(
    pool: DatabasePool,
    store: ArtifactStore,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    input_hash: str,
    queue: JobQueue | None,
) -> bool:
    page_key = document_page_key(document_id)
    masks_meta_key = document_masks_metadata_key(document_id)
    regions_meta_key = document_regions_metadata_key(document_id)
    primitives_meta_key = document_primitives_metadata_key(document_id)
    snapped_meta_key = document_snapped_primitives_metadata_key(document_id)
    topology_meta_key = document_topology_metadata_key(document_id)
    try:
        page_png = store.read(page_key)
        primitives_wire = json.loads(store.read(primitives_meta_key).decode("utf-8"))
        primitives_metadata = PrimitivesMetadata.model_validate(primitives_wire)
        snapped_wire = json.loads(store.read(snapped_meta_key).decode("utf-8"))
        snapped_metadata = SnappedPrimitivesMetadata.model_validate(snapped_wire)
        masks_wire = json.loads(store.read(masks_meta_key).decode("utf-8"))
        masks_metadata = MasksMetadata.model_validate(masks_wire)
        regions_wire = json.loads(store.read(regions_meta_key).decode("utf-8"))
        regions_metadata = RegionsMetadata.model_validate(regions_wire)
        layer_masks: dict[str, bytes] = {}
        try:
            layer_masks["geometry"] = store.read(
                document_mask_key(document_id, "geometry-ink")
            )
        except (FileNotFoundError, PersistenceError, OSError):
            pass
        for layer in masks_metadata.color_layers:
            try:
                layer_masks[layer.layer_id] = store.read(
                    document_color_mask_key(document_id, layer.layer_id)
                )
            except (FileNotFoundError, PersistenceError, OSError):
                continue
    except (FileNotFoundError, PersistenceError, OSError, json.JSONDecodeError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    try:
        topology = infer_topology(
            page_png,
            snapped_metadata,
            primitives_metadata,
            snapped_primitives_json_uri=snapped_meta_key,
            primitives_json_uri=primitives_meta_key,
            topology_json_uri=topology_meta_key,
            masks=masks_metadata,
            masks_json_uri=masks_meta_key,
            regions=regions_metadata,
            regions_json_uri=regions_meta_key,
            layer_masks=layer_masks or None,
        )
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_invalid")
            conn.commit()
        return False

    if not _job_still_active(pool, jobs, job_id):
        return False

    try:
        store.write_immutable(topology_meta_key, topology.topology_json)
        overlay_key = (
            f"{job_stage_artifact_key(job_id, STAGE_INFER_TOPOLOGY, topology.content_hash)}"
            "/overlay.png"
        )
        store.write_immutable(overlay_key, topology.overlay_png)
    except (OSError, PersistenceError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return False
        jobs.insert_stage_run(
            conn,
            job_id=job_id,
            stage=STAGE_INFER_TOPOLOGY,
            status=topology.status,
            input_hash=input_hash,
            producer_version=INFER_TOPOLOGY_VERSION,
            artifact_uri=topology_meta_key,
            metrics=topology.metrics,
            warnings=topology.warnings,
        )
        conn.commit()
    return True


def _execute_transcribe_regions(
    pool: DatabasePool,
    store: ArtifactStore,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    input_hash: str,
    queue: JobQueue | None,
) -> bool:
    page_key = document_page_key(document_id)
    regions_meta_key = document_regions_metadata_key(document_id)
    topology_meta_key = document_topology_metadata_key(document_id)
    text_meta_key = document_text_candidates_metadata_key(document_id)
    try:
        page_png = store.read(page_key)
        regions_wire = json.loads(store.read(regions_meta_key).decode("utf-8"))
        regions_metadata = RegionsMetadata.model_validate(regions_wire)
        topology_metadata: TopologyMetadata | None = None
        try:
            topology_wire = json.loads(store.read(topology_meta_key).decode("utf-8"))
            topology_metadata = TopologyMetadata.model_validate(topology_wire)
        except (FileNotFoundError, PersistenceError, OSError, json.JSONDecodeError):
            topology_metadata = None
        region_crops: dict[str, bytes] = {}
        for region in regions_metadata.regions:
            try:
                region_crops[region.id] = store.read(
                    document_crop_key(document_id, region.id)
                )
            except (FileNotFoundError, PersistenceError, OSError):
                continue
    except (FileNotFoundError, PersistenceError, OSError, json.JSONDecodeError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    try:
        transcribed = transcribe_regions(
            page_png,
            regions_metadata,
            regions_json_uri=regions_meta_key,
            text_candidates_json_uri=text_meta_key,
            region_crops=region_crops or None,
            topology=topology_metadata,
            topology_json_uri=topology_meta_key if topology_metadata else None,
        )
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_invalid")
            conn.commit()
        return False

    if not _job_still_active(pool, jobs, job_id):
        return False

    try:
        store.write_immutable(text_meta_key, transcribed.text_candidates_json)
        overlay_key = (
            f"{job_stage_artifact_key(job_id, STAGE_TRANSCRIBE_REGIONS, transcribed.content_hash)}"
            "/overlay.png"
        )
        store.write_immutable(overlay_key, transcribed.overlay_png)
    except (OSError, PersistenceError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return False
        jobs.insert_stage_run(
            conn,
            job_id=job_id,
            stage=STAGE_TRANSCRIBE_REGIONS,
            status=transcribed.status,
            input_hash=input_hash,
            producer_version=TRANSCRIBE_REGIONS_VERSION,
            artifact_uri=text_meta_key,
            metrics=transcribed.metrics,
            warnings=transcribed.warnings,
        )
        conn.commit()
    return True


def _execute_classify_symbol_regions(
    pool: DatabasePool,
    store: ArtifactStore,
    jobs: JobRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    input_hash: str,
    queue: JobQueue | None,
) -> bool:
    page_key = document_page_key(document_id)
    regions_meta_key = document_regions_metadata_key(document_id)
    topology_meta_key = document_topology_metadata_key(document_id)
    text_meta_key = document_text_candidates_metadata_key(document_id)
    symbol_meta_key = document_symbol_candidates_metadata_key(document_id)
    try:
        page_png = store.read(page_key)
        regions_wire = json.loads(store.read(regions_meta_key).decode("utf-8"))
        regions_metadata = RegionsMetadata.model_validate(regions_wire)
        topology_metadata: TopologyMetadata | None = None
        try:
            topology_wire = json.loads(store.read(topology_meta_key).decode("utf-8"))
            topology_metadata = TopologyMetadata.model_validate(topology_wire)
        except (FileNotFoundError, PersistenceError, OSError, json.JSONDecodeError):
            topology_metadata = None
        text_metadata: TextCandidatesMetadata | None = None
        try:
            text_wire = json.loads(store.read(text_meta_key).decode("utf-8"))
            text_metadata = TextCandidatesMetadata.model_validate(text_wire)
        except (FileNotFoundError, PersistenceError, OSError, json.JSONDecodeError):
            text_metadata = None
        region_crops: dict[str, bytes] = {}
        for region in regions_metadata.regions:
            try:
                region_crops[region.id] = store.read(
                    document_crop_key(document_id, region.id)
                )
            except (FileNotFoundError, PersistenceError, OSError):
                continue
    except (FileNotFoundError, PersistenceError, OSError, json.JSONDecodeError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    try:
        classified = classify_symbol_regions(
            page_png,
            regions_metadata,
            regions_json_uri=regions_meta_key,
            symbol_candidates_json_uri=symbol_meta_key,
            region_crops=region_crops or None,
            topology=topology_metadata,
            topology_json_uri=topology_meta_key if topology_metadata else None,
            text_candidates=text_metadata,
            text_candidates_json_uri=text_meta_key if text_metadata else None,
        )
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_invalid")
            conn.commit()
        return False

    if not _job_still_active(pool, jobs, job_id):
        return False

    try:
        store.write_immutable(symbol_meta_key, classified.symbol_candidates_json)
        overlay_key = (
            f"{job_stage_artifact_key(job_id, STAGE_CLASSIFY_SYMBOL_REGIONS, classified.content_hash)}"
            "/overlay.png"
        )
        store.write_immutable(overlay_key, classified.overlay_png)
    except (OSError, PersistenceError):
        _retry_or_exhaust(pool, jobs, job_id, queue)
        return False

    with pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None or job.cancel_requested or job.result_revision_id is not None:
            if job and job.cancel_requested:
                jobs.mark_canceled(conn, job_id)
                conn.commit()
            return False
        jobs.insert_stage_run(
            conn,
            job_id=job_id,
            stage=STAGE_CLASSIFY_SYMBOL_REGIONS,
            status=classified.status,
            input_hash=input_hash,
            producer_version=CLASSIFY_SYMBOL_REGIONS_VERSION,
            artifact_uri=symbol_meta_key,
            metrics=classified.metrics,
            warnings=classified.warnings,
        )
        conn.commit()
    return True


def _fixture_only_worker() -> bool:
    return os.environ.get("ISOMETRIC_WORKER_FIXTURE_ONLY") == "1"


def _publish_fixture_revision(
    pool: DatabasePool,
    store: ArtifactStore,
    jobs: JobRepository,
    revs: RevisionRepository,
    *,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    revision_id: uuid.UUID,
    source_bytes: bytes,
    queue: JobQueue | None,
) -> None:
    try:
        scene_bytes, review_items = _fitted_scene(
            source_bytes, document_id, revision_id
        )
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
            stage=STAGE_FIXTURE_PROCESS,
            status="running",
            input_hash=job.input_hash,
            producer_version=PIPELINE_VERSION,
        )
        conn.commit()

    publisher = RevisionPublisher(
        store, revisions=_ReviewItemRevisionRepository(review_items)
    )
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
                    stage=STAGE_FIXTURE_PROCESS,
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
        _retry_or_exhaust(pool, jobs, job_id, queue)
    except Exception:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "processing_failed")
            conn.commit()


def process_job(
    pool: DatabasePool,
    store: ArtifactStore,
    job_id: uuid.UUID,
    *,
    queue: JobQueue | None = None,
) -> None:
    jobs = JobRepository()
    revs = RevisionRepository()
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

    with pool.connection() as conn:
        document = DocumentRepository().get(conn, document_id)
    source_bytes: bytes | None = None
    if document is not None and FIXTURE_SCENE.is_file():
        try:
            source_bytes = store.read(document.source_uri)
        except (FileNotFoundError, PersistenceError):
            pass
        except OSError:
            _retry_or_exhaust(pool, jobs, job_id, queue)
            return
    if source_bytes is None:
        with pool.connection() as conn:
            jobs.mark_failed(conn, job_id, "missing_artifact")
            conn.commit()
        return

    if not _execute_normalize_page(
        pool,
        store,
        jobs,
        job_id=job_id,
        document_id=document_id,
        source_bytes=source_bytes,
        input_hash=claimed.input_hash,
        queue=queue,
    ):
        return

    if _fixture_only_worker():
        _publish_fixture_revision(
            pool,
            store,
            jobs,
            revs,
            job_id=job_id,
            document_id=document_id,
            revision_id=revision_id,
            source_bytes=source_bytes,
            queue=queue,
        )
        return

    separated = _execute_separate_masks(
        pool,
        store,
        jobs,
        job_id=job_id,
        document_id=document_id,
        input_hash=claimed.input_hash,
        queue=queue,
    )
    if separated is None:
        return

    if not _execute_detect_regions(
        pool,
        store,
        jobs,
        job_id=job_id,
        document_id=document_id,
        input_hash=claimed.input_hash,
        queue=queue,
        separated=separated,
    ):
        return

    extracted = _execute_extract_centerlines(
        pool,
        store,
        jobs,
        job_id=job_id,
        document_id=document_id,
        input_hash=claimed.input_hash,
        queue=queue,
        separated=separated,
    )
    if extracted is None:
        return

    if not _execute_fit_primitives(
        pool,
        store,
        jobs,
        job_id=job_id,
        document_id=document_id,
        input_hash=claimed.input_hash,
        queue=queue,
        separated=separated,
        extracted=extracted,
    ):
        return

    if not _execute_snap_primitives(
        pool,
        store,
        jobs,
        job_id=job_id,
        document_id=document_id,
        input_hash=claimed.input_hash,
        queue=queue,
    ):
        return

    if not _execute_infer_topology(
        pool,
        store,
        jobs,
        job_id=job_id,
        document_id=document_id,
        input_hash=claimed.input_hash,
        queue=queue,
    ):
        return

    if not _execute_transcribe_regions(
        pool,
        store,
        jobs,
        job_id=job_id,
        document_id=document_id,
        input_hash=claimed.input_hash,
        queue=queue,
    ):
        return

    if not _execute_classify_symbol_regions(
        pool,
        store,
        jobs,
        job_id=job_id,
        document_id=document_id,
        input_hash=claimed.input_hash,
        queue=queue,
    ):
        return

    _publish_fixture_revision(
        pool,
        store,
        jobs,
        revs,
        job_id=job_id,
        document_id=document_id,
        revision_id=revision_id,
        source_bytes=source_bytes,
        queue=queue,
    )
