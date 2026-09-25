"""Response models for the JSON routes and the error envelope."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


class DocumentCreateResponse(BaseModel):
    document_id: str
    job_id: str | None
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
    issue_type: str
    severity: str
    state: str


class ReviewItemListResponse(BaseModel):
    revision_id: str
    items: list[ReviewItem]


class JobProgress(BaseModel):
    stage: str | None
    attempt: int


class JobResponse(BaseModel):
    job_id: str
    document_id: str
    state: str
    stage: str | None
    attempt: int
    progress: JobProgress
    warnings: list[str]
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
