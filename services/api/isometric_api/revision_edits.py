"""Orchestration for human revision edits and review resolution."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from isometric_persistence.artifacts import ArtifactStore
from isometric_persistence.repositories.documents import DocumentRepository
from isometric_persistence.repositories.revisions import RevisionRepository
from isometric_pipeline.render import SYMBOL_LIBRARY_VERSION, load_symbol_library
from isometric_pipeline.review import (
    derive_review_state,
    items_after_edit,
    items_after_resolution,
    lost_confirmed_edits,
    reopen_affected_items,
    row_from_db,
)
from isometric_pipeline.scene import SceneValidationError
from isometric_pipeline.scene.edits import apply_edits, parse_edit_commands
from isometric_pipeline.scene.models import Interpretation
from psycopg import Connection
from pydantic import ValidationError

from .errors import ApiError
from .human_revision import (
    _PendingReviewEvent,
    load_revision_scene,
    publish_human_revision,
)
from .scene_errors import raise_for_scene_failure


def _parent_items(conn: Connection[Any], revs: RevisionRepository, revision_id: uuid.UUID):
    return [row_from_db(row) for row in revs.list_review_items(conn, revision_id)]


def _ensure_revision_on_document(
    revs: RevisionRepository,
    conn: Connection[Any],
    document_id: uuid.UUID,
    revision_id: uuid.UUID,
) -> None:
    rev = revs.get_revision(conn, revision_id)
    if rev is None or rev.document_id != document_id:
        raise ApiError(404, "not_found", "revision not found")


def apply_revision_edits(
    conn: Connection[Any],
    store: ArtifactStore,
    *,
    document_id: uuid.UUID,
    revision_id: uuid.UUID,
    commands_raw: list[dict[str, Any]],
    actor_id: str,
) -> dict[str, str]:
    revs = RevisionRepository()
    _ensure_revision_on_document(revs, conn, document_id, revision_id)
    scene = load_revision_scene(store, revs, conn, revision_id)
    library = load_symbol_library(SYMBOL_LIBRARY_VERSION)
    try:
        commands = parse_edit_commands(commands_raw)
        result = apply_edits(scene, commands, catalog=library)
    except (ValueError, ValidationError, SceneValidationError) as exc:
        raise_for_scene_failure(exc)
    parent_items = _parent_items(conn, revs, revision_id)
    new_items = items_after_edit(
        parent_items,
        affected_object_ids=set(result.affected_object_ids),
    )
    review_state = derive_review_state(new_items)
    published = publish_human_revision(
        conn,
        store,
        document_id=document_id,
        parent_revision_id=revision_id,
        scene=result.scene,
        review_state=review_state,
        review_items=new_items,
        review_events=[],
        actor_id=actor_id,
    )
    conn.commit()
    return {
        "revision_id": str(published.revision_id),
        "review_state": published.review_state,
        "scene_checksum_sha256": published.scene_checksum_sha256,
    }


def resolve_review_item(
    conn: Connection[Any],
    store: ArtifactStore,
    *,
    document_id: uuid.UUID,
    revision_id: uuid.UUID,
    item_id: uuid.UUID,
    action: Literal["confirm", "correct", "acknowledge_unknown"],
    correction_commands: list[dict[str, Any]] | None,
    actor_id: str,
) -> dict[str, str]:
    revs = RevisionRepository()
    _ensure_revision_on_document(revs, conn, document_id, revision_id)
    row = revs.get_review_item(conn, revision_id, item_id)
    if row is None:
        raise ApiError(404, "not_found", "review item not found")
    parent_items = _parent_items(conn, revs, revision_id)
    scene = load_revision_scene(store, revs, conn, revision_id)
    library = load_symbol_library(SYMBOL_LIBRARY_VERSION)
    events: list[_PendingReviewEvent] = []
    new_state: str
    affected_object_ids: set[str] = set()
    try:
        if action == "confirm":
            new_state = "confirmed"
            if row["object_id"]:
                scene = _confirm_object(scene, row["object_id"])
        elif action == "acknowledge_unknown":
            new_state = "acknowledged_unknown"
        elif action == "correct":
            if not correction_commands:
                raise ApiError(400, "invalid_request", "correction commands are required")
            new_state = "corrected"
            commands = parse_edit_commands(correction_commands)
            applied = apply_edits(scene, commands, catalog=library)
            scene = applied.scene
            affected_object_ids = set(applied.affected_object_ids)
        else:
            raise ApiError(400, "invalid_request", "invalid resolve action")
    except ApiError:
        raise
    except (ValueError, ValidationError, SceneValidationError) as exc:
        raise_for_scene_failure(exc)
    new_items = items_after_resolution(
        parent_items,
        issue_key=row["issue_key"],
        new_state=new_state,
    )
    if action == "correct":
        new_items = reopen_affected_items(
            new_items,
            affected_object_ids=affected_object_ids,
            except_issue_key=row["issue_key"],
        )
    review_state = derive_review_state(new_items)
    events.append(
        _PendingReviewEvent(
            issue_key=row["issue_key"],
            old_value={"state": row["state"]},
            new_value={"state": new_state, "action": action},
        )
    )
    published = publish_human_revision(
        conn,
        store,
        document_id=document_id,
        parent_revision_id=revision_id,
        scene=scene,
        review_state=review_state,
        review_items=new_items,
        review_events=events,
        actor_id=actor_id,
    )
    conn.commit()
    return {
        "revision_id": str(published.revision_id),
        "review_state": published.review_state,
        "scene_checksum_sha256": published.scene_checksum_sha256,
    }


def _confirm_object(scene, object_id: str):
    found = False
    objects = []
    for obj in scene.objects:
        if obj.id == object_id:
            found = True
            objects.append(
                obj.model_copy(
                    update={
                        "interpretation": Interpretation(
                            state="confirmed", evidence=obj.interpretation.evidence
                        )
                    }
                )
            )
        else:
            objects.append(obj)
    if not found:
        raise ApiError(404, "not_found", "scene object not found")
    return scene.model_copy(update={"objects": objects})


def adopt_candidate_revision(
    conn: Connection[Any],
    store: ArtifactStore,
    *,
    document_id: uuid.UUID,
    current_revision_id: uuid.UUID,
    candidate_revision_id: uuid.UUID,
    actor_id: str,
) -> dict[str, Any]:
    revs = RevisionRepository()
    docs = DocumentRepository()
    doc = docs.get(conn, document_id)
    if doc is None:
        raise ApiError(404, "not_found", "document not found")
    if doc.current_revision_id != current_revision_id:
        raise ApiError(409, "revision_conflict", "revision is stale; refresh and retry")
    if candidate_revision_id == current_revision_id:
        raise ApiError(400, "invalid_request", "candidate revision must differ from current")
    candidate_row = revs.get_revision(conn, candidate_revision_id)
    if candidate_row is None or candidate_row.document_id != document_id:
        raise ApiError(404, "not_found", "candidate revision not found")
    current = load_revision_scene(store, revs, conn, current_revision_id)
    candidate = load_revision_scene(store, revs, conn, candidate_revision_id)
    lost = lost_confirmed_edits(current, candidate)
    revs.promote_revision_to_current(
        conn,
        document_id=document_id,
        expected_current_revision_id=current_revision_id,
        candidate_revision_id=candidate_revision_id,
    )
    revs.set_revision_review_state(conn, candidate_revision_id, "review_required")
    conn.commit()
    return {
        "document_id": str(document_id),
        "current_revision_id": str(candidate_revision_id),
        "lost_confirmed_edits": lost,
        "review_state": "review_required",
    }
