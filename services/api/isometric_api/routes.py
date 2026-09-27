"""HTTP routes for Run 04."""

from __future__ import annotations

import io
import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import Response
from isometric_persistence.errors import PersistenceError
from isometric_persistence.keys import (
    document_display_key,
    document_original_key,
)
from isometric_persistence.repositories.documents import DocumentRepository
from isometric_persistence.repositories.jobs import (
    JOB_KIND_DRAWING_READING,
    JobRepository,
)
from isometric_persistence.repositories.revisions import RevisionRepository
from isometric_worker.dispatcher import dispatch_outbox
from isometric_worker.runner import run_once
from isometric_worker.trace_svg import read_or_build_document_trace
from PIL import Image, ImageOps
from psycopg.errors import UniqueViolation

from .deps import AppState, get_owner_id, get_state
from .drawing_reading import build_drawing_reading_response
from .errors import ApiError, error_responses
from .human_revision import parse_if_match
from .revision_edits import (
    adopt_candidate_revision,
    apply_revision_edits,
    resolve_review_item,
)
from .schemas import (
    AdoptCandidateRequest,
    AdoptCandidateResponse,
    DocumentCreateResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DrawingReadingResponse,
    JobCancelResponse,
    JobResponse,
    ReprocessResponse,
    ResolveReviewItemRequest,
    ReviewItemListResponse,
    RevisionEditsRequest,
    RevisionListResponse,
    RevisionMutationResponse,
)
from .upload import sanitize_original_filename, validate_upload

router = APIRouter(prefix="/api/v1", responses=error_responses(400, 401, 500))
_OWNED = error_responses(403, 404)
_SVG_EXPORT_CSP = "default-src 'none'; style-src 'unsafe-inline'"
# Modes Pillow can write as PNG; anything else (e.g. CMYK JPEG) is converted to RGB.
_PNG_MODES = frozenset({"1", "L", "LA", "I", "I;16", "P", "RGB", "RGBA"})


def _run_worker_sync(pool: Any, store: Any, queue: Any) -> None:
    dispatch_outbox(pool, queue)
    run_once(pool, store, queue)


def _schedule_worker(request: Request, background_tasks: BackgroundTasks) -> None:
    if os.environ.get("SKIP_INLINE_WORKER") == "1":
        return
    state = get_state(request)
    background_tasks.add_task(_run_worker_sync, state.pool, state.store, state.queue)


def _ensure_owner(doc_owner: str, caller: str) -> None:
    if doc_owner != caller:
        raise ApiError(403, "forbidden", "document access denied")


def _read_artifact(state: AppState, key: str) -> bytes:
    try:
        return state.store.read(key)
    except FileNotFoundError:
        raise ApiError(404, "missing_artifact", "artifact is missing") from None
    except PersistenceError as exc:
        if exc.code in {"invalid_artifact_key", "artifact_not_found"}:
            raise ApiError(404, "missing_artifact", "artifact is missing") from exc
        raise


def _review_state_for_revision(
    conn: Any, revs: RevisionRepository, revision_id: uuid.UUID | None
) -> str | None:
    if revision_id is None:
        return None
    return revs.get_review_state(conn, revision_id)


def _review_item_count(
    conn: Any, revs: RevisionRepository, revision_id: uuid.UUID | None
) -> int:
    if revision_id is None:
        return 0
    return len(revs.list_review_items(conn, revision_id))


def _document_json_fields(doc: Any) -> dict[str, Any]:
    return {
        "original_filename": doc.original_filename,
        "profile_id": doc.profile_id,
    }


def _enqueue_drawing_reading_job(
    jobs: JobRepository,
    conn: Any,
    *,
    document_id: uuid.UUID,
    input_hash: str,
    options_hash: str,
    pipeline_version: str,
    profile_version: str,
) -> uuid.UUID:
    reading_job_id = uuid.uuid4()
    jobs.create_with_outbox(
        conn,
        job_id=reading_job_id,
        document_id=document_id,
        state="queued",
        input_hash=input_hash,
        options_hash=options_hash,
        pipeline_version=pipeline_version,
        profile_version=profile_version,
        event_key=f"job.created.{reading_job_id}",
        kind=JOB_KIND_DRAWING_READING,
    )
    return reading_job_id


def _idempotent_upload_response(
    conn: Any,
    *,
    docs: DocumentRepository,
    jobs: JobRepository,
    existing: Any,
    validated: Any,
) -> dict[str, Any]:
    if (
        existing.source_hash != validated.source_hash
        or existing.upload_options_hash != validated.options_hash
    ):
        raise ApiError(
            409,
            "idempotency_conflict",
            "idempotency key was reused with different payload",
        )
    job = jobs.get_for_document(conn, existing.id)
    return {
        "document_id": str(existing.id),
        "job_id": str(job.id) if job else None,
        "status": job.state if job else "queued",
    }


def _job_updated_at_iso(job: Any) -> str | None:
    updated = job.updated_at
    if updated is None:
        return None
    if hasattr(updated, "isoformat"):
        return updated.isoformat()
    return str(updated)


def _timestamp_iso(value: object | None) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _job_logs_json(jobs: JobRepository, conn: Any, job_id: uuid.UUID) -> list[dict[str, Any]]:
    return [
        {
            "id": str(row.id),
            "created_at": _timestamp_iso(row.created_at),
            "level": row.level,
            "stage": row.stage,
            "message": row.message,
            "detail": row.detail,
        }
        for row in jobs.list_job_logs(conn, job_id)
    ]


@router.post(
    "/documents",
    status_code=202,
    response_model=DocumentCreateResponse,
    responses=error_responses(409, 413, 415),
)
async def create_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
    profile_id: str = Form(default="piping_isometric"),
    options_json: str = Form(default="{}"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    state = get_state(request)
    owner_id = get_owner_id(request)
    if profile_id != state.settings.profile_id:
        raise ApiError(400, "unsupported_profile", "profile is not supported")
    try:
        options = json.loads(options_json) if options_json else {}
    except json.JSONDecodeError:
        raise ApiError(
            400, "invalid_options", "options_json must be valid JSON"
        ) from None
    if not isinstance(options, dict):
        raise ApiError(
            400, "invalid_options", "options_json must be an object"
        ) from None

    raw = await file.read()
    validated = validate_upload(
        raw,
        profile_id=profile_id,
        options=options,
        max_bytes=state.settings.max_upload_bytes,
        max_pixels=state.settings.max_pixels,
    )
    original_filename = sanitize_original_filename(file.filename)

    docs = DocumentRepository()
    jobs = JobRepository()
    with state.pool.connection() as conn:
        if idempotency_key:
            existing = docs.find_by_idempotency(
                conn, owner_id=owner_id, idempotency_key=idempotency_key
            )
            if existing is not None:
                payload = _idempotent_upload_response(
                    conn,
                    docs=docs,
                    jobs=jobs,
                    existing=existing,
                    validated=validated,
                )
                conn.commit()
                _schedule_worker(request, background_tasks)
                return payload

        document_id = uuid.uuid4()
        job_id = uuid.uuid4()
        original_key = document_original_key(document_id)
        state.store.write_immutable(original_key, validated.data)
        try:
            docs.create(
                conn,
                document_id=document_id,
                owner_id=owner_id,
                source_hash=validated.source_hash,
                source_uri=original_key,
                source_mime=validated.mime,
                upload_idempotency_key=idempotency_key,
                upload_options_hash=validated.options_hash,
                source_width_px=validated.width_px,
                source_height_px=validated.height_px,
                original_filename=original_filename,
                profile_id=profile_id,
            )
            jobs.create_with_outbox(
                conn,
                job_id=job_id,
                document_id=document_id,
                state="queued",
                input_hash=validated.source_hash,
                options_hash=validated.options_hash,
                pipeline_version=state.settings.pipeline_version,
                profile_version=profile_id,
                event_key=f"job.created.{job_id}",
            )
            _enqueue_drawing_reading_job(
                jobs,
                conn,
                document_id=document_id,
                input_hash=validated.source_hash,
                options_hash=validated.options_hash,
                pipeline_version=state.settings.pipeline_version,
                profile_version=profile_id,
            )
        except UniqueViolation:
            conn.rollback()
            if not idempotency_key:
                raise
            existing = docs.find_by_idempotency(
                conn, owner_id=owner_id, idempotency_key=idempotency_key
            )
            if existing is None:
                raise
            payload = _idempotent_upload_response(
                conn,
                docs=docs,
                jobs=jobs,
                existing=existing,
                validated=validated,
            )
            conn.commit()
            _schedule_worker(request, background_tasks)
            return payload
        conn.commit()

    _schedule_worker(request, background_tasks)
    return {"document_id": str(document_id), "job_id": str(job_id), "status": "queued"}


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    jobs = JobRepository()
    revs = RevisionRepository()
    with state.pool.connection() as conn:
        rows = docs.list_for_owner(conn, owner_id=owner_id, limit=limit, offset=offset)
        items = []
        for doc in rows:
            job = jobs.get_for_document(conn, doc.id)
            items.append(
                {
                    "document_id": str(doc.id),
                    "created_at": doc.created_at.isoformat()
                    if doc.created_at
                    else None,
                    "current_revision_id": str(doc.current_revision_id)
                    if doc.current_revision_id
                    else None,
                    "review_state": _review_state_for_revision(
                        conn, revs, doc.current_revision_id
                    ),
                    **_document_json_fields(doc),
                    "latest_job": {
                        "id": str(job.id),
                        "state": job.state,
                        "stage": job.stage,
                    }
                    if job
                    else None,
                }
            )
    return {"items": items, "limit": limit, "offset": offset}


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    responses=_OWNED,
)
def get_document(request: Request, document_id: uuid.UUID) -> dict[str, Any]:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    jobs = JobRepository()
    revs = RevisionRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        job = jobs.get_for_document(conn, doc.id)
        review_state = _review_state_for_revision(conn, revs, doc.current_revision_id)
    return {
        "document_id": str(doc.id),
        "source_mime": doc.source_mime,
        "source_hash": doc.source_hash,
        "source_width_px": doc.source_width_px,
        "source_height_px": doc.source_height_px,
        "current_revision_id": str(doc.current_revision_id)
        if doc.current_revision_id
        else None,
        "review_state": review_state,
        **_document_json_fields(doc),
        "latest_job": {
            "id": str(job.id),
            "state": job.state,
            "stage": job.stage,
            "result_revision_id": str(job.result_revision_id)
            if job and job.result_revision_id
            else None,
        }
        if job
        else None,
    }


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=ReprocessResponse,
    status_code=202,
    responses=_OWNED,
)
def reprocess_document(
    request: Request,
    background_tasks: BackgroundTasks,
    document_id: uuid.UUID,
) -> dict[str, Any]:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    jobs = JobRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        profile_id = doc.profile_id or state.settings.profile_id
        job_id = uuid.uuid4()
        jobs.create_with_outbox(
            conn,
            job_id=job_id,
            document_id=document_id,
            state="queued",
            input_hash=doc.source_hash,
            options_hash="reprocess",
            pipeline_version=state.settings.pipeline_version,
            profile_version=profile_id,
            event_key=f"job.reprocess.{job_id}",
            event_type="job.reprocess",
        )
        _enqueue_drawing_reading_job(
            jobs,
            conn,
            document_id=document_id,
            input_hash=doc.source_hash,
            options_hash="reprocess",
            pipeline_version=state.settings.pipeline_version,
            profile_version=profile_id,
        )
        conn.commit()
    _schedule_worker(request, background_tasks)
    return {
        "document_id": str(document_id),
        "job_id": str(job_id),
        "status": "queued",
    }


@router.get(
    "/documents/{document_id}/drawing-reading",
    response_model=DrawingReadingResponse,
    responses=_OWNED,
)
def get_document_drawing_reading(
    request: Request, document_id: uuid.UUID
) -> dict[str, Any]:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    jobs = JobRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        reading_job = jobs.get_newest_reading_job(conn, document_id)
    return build_drawing_reading_response(
        reading_job=reading_job,
        store=state.store,
    )


@router.post(
    "/documents/{document_id}/drawing-reading/retry",
    response_model=ReprocessResponse,
    status_code=202,
    responses=_OWNED,
)
def retry_document_drawing_reading(
    request: Request,
    background_tasks: BackgroundTasks,
    document_id: uuid.UUID,
) -> dict[str, Any]:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    jobs = JobRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        profile_id = doc.profile_id or state.settings.profile_id
        reading_job_id = _enqueue_drawing_reading_job(
            jobs,
            conn,
            document_id=document_id,
            input_hash=doc.source_hash,
            options_hash="drawing_reading_retry",
            pipeline_version=state.settings.pipeline_version,
            profile_version=profile_id,
        )
        conn.commit()
    _schedule_worker(request, background_tasks)
    return {
        "document_id": str(document_id),
        "job_id": str(reading_job_id),
        "status": "queued",
    }


@router.get("/documents/{document_id}/source", responses=_OWNED)
def get_document_source(request: Request, document_id: uuid.UUID) -> Response:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
    data = _read_artifact(state, doc.source_uri)
    return Response(content=data, media_type=doc.source_mime)


@router.get("/documents/{document_id}/display", responses=_OWNED)
def get_document_display(request: Request, document_id: uuid.UUID) -> Response:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
    display_key = document_display_key(document_id)
    try:
        data = state.store.read(display_key)
        return Response(content=data, media_type="image/png")
    except FileNotFoundError:
        pass
    except PersistenceError as exc:
        if exc.code not in {"invalid_artifact_key", "artifact_not_found"}:
            raise
    data = _read_artifact(state, doc.source_uri)
    with Image.open(io.BytesIO(data)) as image:
        transposed = ImageOps.exif_transpose(image)
        if transposed is None:
            transposed = image
        if transposed.mode not in _PNG_MODES:
            transposed = transposed.convert("RGB")
        out = io.BytesIO()
        transposed.save(out, format="PNG")
    return Response(content=out.getvalue(), media_type="image/png")


def _svg_export_response(data: bytes) -> Response:
    return Response(
        content=data,
        media_type="image/svg+xml",
        headers={
            "Content-Security-Policy": _SVG_EXPORT_CSP,
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/documents/{document_id}/trace", responses=_OWNED)
def get_document_trace(request: Request, document_id: uuid.UUID) -> Response:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        profile_id = doc.profile_id
    data = read_or_build_document_trace(state.store, document_id, profile_id)
    if not data:
        raise ApiError(404, "not_found", "trace export not found")
    return _svg_export_response(data)


@router.get(
    "/documents/{document_id}/revisions",
    response_model=RevisionListResponse,
    responses=_OWNED,
)
def list_revisions(request: Request, document_id: uuid.UUID) -> dict[str, Any]:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    revs = RevisionRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        rows = revs.list_for_document(conn, document_id)
    return {
        "document_id": str(document_id),
        "current_revision_id": str(doc.current_revision_id)
        if doc.current_revision_id
        else None,
        "revisions": [
            {
                "revision_id": str(row["id"]),
                "parent_revision_id": str(row["parent_revision_id"])
                if row["parent_revision_id"]
                else None,
                "review_state": row["review_state"],
                "validation_status": row["validation_status"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ],
    }


@router.get("/documents/{document_id}/revisions/{revision_id}/scene", responses=_OWNED)
def get_revision_scene(
    request: Request, document_id: uuid.UUID, revision_id: uuid.UUID
) -> Response:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    revs = RevisionRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        rev = revs.get_revision(conn, revision_id)
        if rev is None or rev.document_id != document_id:
            raise ApiError(404, "not_found", "revision not found")
    data = _read_artifact(state, rev.scene_uri)
    return Response(content=data, media_type="application/json")


@router.get(
    "/documents/{document_id}/revisions/{revision_id}/review-items",
    response_model=ReviewItemListResponse,
    responses=_OWNED,
)
def get_review_items(
    request: Request, document_id: uuid.UUID, revision_id: uuid.UUID
) -> dict[str, Any]:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    revs = RevisionRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        rev = revs.get_revision(conn, revision_id)
        if rev is None or rev.document_id != document_id:
            raise ApiError(404, "not_found", "revision not found")
        items = revs.list_review_items(conn, revision_id)
    return {
        "revision_id": str(revision_id),
        "items": [
            {
                "id": str(item["id"]),
                "issue_key": item["issue_key"],
                "object_id": item["object_id"],
                "relationship_id": item.get("relationship_id"),
                "issue_type": item["issue_type"],
                "severity": item["severity"],
                "crop_uri": item.get("crop_uri"),
                "proposed_options": item.get("proposed_options") or [],
                "state": item["state"],
            }
            for item in items
        ],
    }


@router.post(
    "/documents/{document_id}/revisions/{revision_id}/edits",
    response_model=RevisionMutationResponse,
    responses=error_responses(409, 428) | _OWNED,
)
def post_revision_edits(
    request: Request,
    document_id: uuid.UUID,
    revision_id: uuid.UUID,
    body: RevisionEditsRequest,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, str]:
    parse_if_match(if_match, revision_id)
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        if doc.current_revision_id != revision_id:
            raise ApiError(
                409,
                "revision_conflict",
                "edits must apply to the document current revision",
            )
        return apply_revision_edits(
            conn,
            state.store,
            document_id=document_id,
            revision_id=revision_id,
            commands_raw=body.commands,
            actor_id=owner_id,
        )


@router.post(
    "/documents/{document_id}/revisions/{revision_id}/review-items/{item_id}/resolve",
    response_model=RevisionMutationResponse,
    responses=error_responses(409, 428) | _OWNED,
)
def post_resolve_review_item(
    request: Request,
    document_id: uuid.UUID,
    revision_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ResolveReviewItemRequest,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, str]:
    parse_if_match(if_match, revision_id)
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        if doc.current_revision_id != revision_id:
            raise ApiError(
                409,
                "revision_conflict",
                "resolve must apply to the document current revision",
            )
        correction = (
            body.correction.commands if body.correction is not None else None
        )
        if body.action not in ("confirm", "correct", "acknowledge_unknown"):
            raise ApiError(400, "invalid_request", "invalid resolve action")
        return resolve_review_item(
            conn,
            state.store,
            document_id=document_id,
            revision_id=revision_id,
            item_id=item_id,
            action=body.action,
            correction_commands=correction,
            actor_id=owner_id,
        )


@router.post(
    "/documents/{document_id}/revisions/{revision_id}/adopt",
    response_model=AdoptCandidateResponse,
    responses=error_responses(409, 428) | _OWNED,
)
def post_adopt_candidate(
    request: Request,
    document_id: uuid.UUID,
    revision_id: uuid.UUID,
    body: AdoptCandidateRequest,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    parse_if_match(if_match, revision_id)
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        candidate_id = uuid.UUID(body.candidate_revision_id)
        return adopt_candidate_revision(
            conn,
            state.store,
            document_id=document_id,
            current_revision_id=revision_id,
            candidate_revision_id=candidate_id,
            actor_id=owner_id,
        )


@router.get(
    "/documents/{document_id}/revisions/{revision_id}/exports/{kind}",
    responses=_OWNED,
)
def get_export(
    request: Request, document_id: uuid.UUID, revision_id: uuid.UUID, kind: str
) -> Response:
    owner_id = get_owner_id(request)
    state = get_state(request)
    docs = DocumentRepository()
    revs = RevisionRepository()
    with state.pool.connection() as conn:
        doc = docs.get(conn, document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        rev = revs.get_revision(conn, revision_id)
        if rev is None or rev.document_id != document_id:
            raise ApiError(404, "not_found", "revision not found")
        export = revs.get_export(conn, revision_id, kind)
        profile_id = doc.profile_id
    if export is None and kind == "trace":
        data = read_or_build_document_trace(state.store, document_id, profile_id)
        if data:
            return _svg_export_response(data)
    if export is None:
        raise ApiError(404, "not_found", "export not found")
    data = _read_artifact(state, export["uri"])
    if kind in {"svg", "trace"}:
        return _svg_export_response(data)
    return Response(content=data, media_type="image/png")


@router.get("/jobs/{job_id}", response_model=JobResponse, responses=_OWNED)
def get_job(request: Request, job_id: uuid.UUID) -> dict[str, Any]:
    owner_id = get_owner_id(request)
    state = get_state(request)
    jobs = JobRepository()
    docs = DocumentRepository()
    revs = RevisionRepository()
    with state.pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None:
            raise ApiError(404, "not_found", "job not found")
        doc = docs.get(conn, job.document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        warnings = jobs.get_latest_stage_warnings(conn, job_id)
        logs = _job_logs_json(jobs, conn, job_id)
        review_state = _review_state_for_revision(conn, revs, job.result_revision_id)
        review_item_count = _review_item_count(conn, revs, job.result_revision_id)
    return {
        "job_id": str(job.id),
        "document_id": str(job.document_id),
        "state": job.state,
        "stage": job.stage,
        "attempt": job.attempt,
        "progress": {"stage": job.stage, "attempt": job.attempt},
        "warnings": warnings,
        "logs": logs,
        "review_state": review_state,
        "error_code": job.error_code,
        "result_revision_id": str(job.result_revision_id)
        if job.result_revision_id
        else None,
        "cancel_requested": job.cancel_requested,
        "updated_at": _job_updated_at_iso(job),
        "review_item_count": review_item_count,
    }


@router.post(
    "/jobs/{job_id}/cancel", response_model=JobCancelResponse, responses=_OWNED
)
def cancel_job(request: Request, job_id: uuid.UUID) -> dict[str, Any]:
    owner_id = get_owner_id(request)
    state = get_state(request)
    jobs = JobRepository()
    docs = DocumentRepository()
    with state.pool.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None:
            raise ApiError(404, "not_found", "job not found")
        doc = docs.get(conn, job.document_id)
        if doc is None:
            raise ApiError(404, "not_found", "document not found")
        _ensure_owner(doc.owner_id, owner_id)
        updated = jobs.request_cancel(conn, job_id)
        if updated and updated.state == "queued":
            jobs.mark_canceled(conn, job_id)
            updated = jobs.get(conn, job_id)
        conn.commit()
    return {
        "job_id": str(job_id),
        "state": updated.state if updated else "unknown",
        "cancel_requested": updated.cancel_requested if updated else True,
    }
