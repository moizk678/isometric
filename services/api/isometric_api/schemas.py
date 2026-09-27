"""Response models for the JSON routes and the error envelope."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


class DocumentCreateResponse(BaseModel):
    document_id: str
    job_id: str | None
    status: str


class ReprocessResponse(BaseModel):
    document_id: str
    job_id: str
    status: str


class LatestJobSummary(BaseModel):
    id: str
    state: str
    stage: str | None


class LatestJobDetail(LatestJobSummary):
    result_revision_id: str | None


class DocumentListItem(BaseModel):
    document_id: str
    created_at: str | None
    current_revision_id: str | None
    review_state: str | None
    original_filename: str | None
    profile_id: str | None
    latest_job: LatestJobSummary | None


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    limit: int
    offset: int


class DocumentDetailResponse(BaseModel):
    document_id: str
    source_mime: str
    source_hash: str
    source_width_px: int | None
    source_height_px: int | None
    current_revision_id: str | None
    review_state: str | None
    original_filename: str | None
    profile_id: str | None
    latest_job: LatestJobDetail | None


class RevisionSummary(BaseModel):
    revision_id: str
    parent_revision_id: str | None
    review_state: str
    validation_status: str
    created_at: str


class RevisionListResponse(BaseModel):
    document_id: str
    current_revision_id: str | None
    revisions: list[RevisionSummary]


class ReviewItem(BaseModel):
    id: str
    issue_key: str
    object_id: str | None
    relationship_id: str | None = None
    issue_type: str
    severity: str
    crop_uri: str | None = None
    proposed_options: list[dict] = []
    state: str


class RevisionEditsRequest(BaseModel):
    commands: list[dict]


class ResolveReviewItemRequest(BaseModel):
    action: str
    correction: RevisionEditsRequest | None = None


class AdoptCandidateRequest(BaseModel):
    candidate_revision_id: str


class LostConfirmedEdit(BaseModel):
    object_id: str
    reason: str


class RevisionMutationResponse(BaseModel):
    revision_id: str
    review_state: str
    scene_checksum_sha256: str


class AdoptCandidateResponse(BaseModel):
    document_id: str
    current_revision_id: str
    review_state: str
    lost_confirmed_edits: list[LostConfirmedEdit]


class ReviewItemListResponse(BaseModel):
    revision_id: str
    items: list[ReviewItem]


class JobProgress(BaseModel):
    stage: str | None
    attempt: int


class JobLogEntry(BaseModel):
    id: str
    created_at: str
    level: str
    stage: str | None
    message: str
    detail: dict[str, Any]


class JobResponse(BaseModel):
    job_id: str
    document_id: str
    state: str
    stage: str | None
    attempt: int
    progress: JobProgress
    warnings: list[str]
    logs: list[JobLogEntry]
    review_state: str | None
    error_code: str | None
    result_revision_id: str | None
    cancel_requested: bool
    updated_at: str
    review_item_count: int


class JobCancelResponse(BaseModel):
    job_id: str
    state: str
    cancel_requested: bool


class DrawingReadingRow(BaseModel):
    location: str
    reading: str


class DrawingReadingGroup(BaseModel):
    id: str
    title: str
    rows: list[DrawingReadingRow]


class DrawingReadingResponse(BaseModel):
    status: str
    job_id: str | None = None
    error_code: str | None = None
    schema_version: str | None = None
    prompt_version: str | None = None
    provider: str | None = None
    model: str | None = None
    groups: list[DrawingReadingGroup] | None = None
