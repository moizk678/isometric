"""Publish human-authored revisions with regenerated exports."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from isometric_persistence.artifacts import ArtifactStore
from isometric_persistence.errors import ConflictError
from isometric_persistence.publishing import PublishExport, RevisionPublisher
from isometric_persistence.repositories.revisions import (
    RevisionRepository,
    SceneRevisionRow,
)
from isometric_pipeline.render import (
    STYLE_PROFILE_VERSION,
    SYMBOL_LIBRARY_VERSION,
    load_symbol_library,
    render_svg,
)
from isometric_pipeline.render.preview import rasterize_preview
from isometric_pipeline.render.versions import RENDERER_VERSION
from isometric_pipeline.review.policy import ReviewItemRow
from isometric_pipeline.scene import load_scene
from isometric_pipeline.scene.models import DrawingScene
from isometric_pipeline.scene.serialization import dump_scene
from psycopg import Connection

from .errors import ApiError


@dataclass(frozen=True)
class HumanPublishResult:
    revision_id: uuid.UUID
    review_state: str
    scene_checksum_sha256: str


@dataclass(frozen=True)
class _PendingReviewEvent:
    issue_key: str
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None


class _HumanRevisionRepository(RevisionRepository):
    def __init__(
        self,
        review_items: list[ReviewItemRow],
        events: list[_PendingReviewEvent],
        source_revision_id: uuid.UUID,
        actor_id: str,
    ) -> None:
        super().__init__()
        self._review_items = review_items
        self._events = events
        self._source_revision_id = source_revision_id
        self._actor_id = actor_id

    def insert_revision(self, conn: Connection[Any], **kwargs: Any) -> SceneRevisionRow:
        row = super().insert_revision(conn, **kwargs)
        for item in self._review_items:
            self.insert_review_item(
                conn,
                issue_key=item.issue_key,
                revision_id=row.id,
                issue_type=item.issue_type,
                severity=item.severity,
                state=item.state,
                object_id=item.object_id,
                relationship_id=item.relationship_id,
                crop_uri=item.crop_uri,
                proposed_options=item.proposed_options,
            )
        for event in self._events:
            self.insert_review_event(
                conn,
                issue_key=event.issue_key,
                source_revision_id=self._source_revision_id,
                result_revision_id=row.id,
                actor_id=self._actor_id,
                old_value=event.old_value,
                new_value=event.new_value,
            )
        return row


def parse_if_match(if_match: str | None, revision_id: uuid.UUID) -> None:
    if if_match is None or not if_match.strip():
        raise ApiError(428, "precondition_required", "If-Match revision header is required")
    expected = if_match.strip().strip('"')
    if expected != str(revision_id):
        raise ApiError(409, "revision_conflict", "revision is stale; refresh and retry")


def bump_scene_revision(scene: DrawingScene, new_revision_id: uuid.UUID) -> DrawingScene:
    return scene.model_copy(
        update={
            "revision_id": str(new_revision_id),
            "parent_revision_id": scene.revision_id,
        }
    )


def render_exports(scene: DrawingScene) -> tuple[bytes, bytes]:
    svg = render_svg(scene, SYMBOL_LIBRARY_VERSION, STYLE_PROFILE_VERSION).svg
    png = rasterize_preview(svg).png
    return svg, png


def publish_human_revision(
    conn: Connection[Any],
    store: ArtifactStore,
    *,
    document_id: uuid.UUID,
    parent_revision_id: uuid.UUID,
    scene: DrawingScene,
    review_state: str,
    review_items: list[ReviewItemRow],
    review_events: list[_PendingReviewEvent],
    actor_id: str,
) -> HumanPublishResult:
    new_revision_id = uuid.uuid4()
    scene = bump_scene_revision(scene, new_revision_id)
    scene_bytes = dump_scene(scene).encode("utf-8")
    svg, png = render_exports(scene)
    publisher = RevisionPublisher(
        store,
        revisions=_HumanRevisionRepository(
            review_items,
            review_events,
            parent_revision_id,
            actor_id,
        ),
    )
    try:
        result = publisher.publish(
            conn,
            document_id=document_id,
            expected_parent_revision_id=parent_revision_id,
            schema_version="1.0",
            scene_bytes=scene_bytes,
            author_type="human",
            review_state=review_state,
            validation_status="valid",
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
    except ConflictError:
        raise ApiError(
            409, "revision_conflict", "revision is stale; refresh and retry"
        ) from None
    return HumanPublishResult(
        revision_id=result.revision_id,
        review_state=review_state,
        scene_checksum_sha256=result.scene_checksum_sha256,
    )


def load_revision_scene(
    store: ArtifactStore,
    revs: RevisionRepository,
    conn: Connection[Any],
    revision_id: uuid.UUID,
) -> DrawingScene:
    rev = revs.get_revision(conn, revision_id)
    if rev is None:
        raise ApiError(404, "not_found", "revision not found")
    raw = store.read(rev.scene_uri)
    library = load_symbol_library(SYMBOL_LIBRARY_VERSION)
    return load_scene(raw, catalog=library)
