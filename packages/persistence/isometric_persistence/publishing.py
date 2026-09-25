"""Publish scene revisions: artifacts first, then database CAS."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from psycopg import Connection

from .artifacts import ArtifactStore, sha256_hex
from .errors import ConflictError, PersistenceError
from .keys import revision_export_key, revision_scene_key
from .repositories.reconciler import ArtifactReconciler
from .repositories.revisions import RevisionRepository


@dataclass(frozen=True)
class PublishExport:
    kind: str
    format: str
    data: bytes
    renderer_version: str


@dataclass(frozen=True)
class PublishResult:
    revision_id: uuid.UUID
    scene_key: str
    scene_checksum_sha256: str


class RevisionPublisher:
    def __init__(
        self,
        store: ArtifactStore,
        revisions: RevisionRepository | None = None,
    ) -> None:
        self._store = store
        self._revisions = revisions or RevisionRepository()
        self._reconciler = ArtifactReconciler(store)

    def publish(
        self,
        conn: Connection[Any],
        *,
        document_id: uuid.UUID,
        expected_parent_revision_id: uuid.UUID | None,
        schema_version: str,
        scene_bytes: bytes,
        author_type: str,
        review_state: str,
        validation_status: str,
        exports: list[PublishExport],
        carry_review_items_from: uuid.UUID | None = None,
        intent_grace_seconds: int = 300,
        write_artifacts: bool = True,
        revision_id: uuid.UUID | None = None,
    ) -> PublishResult:
        revision_id = revision_id or uuid.uuid4()
        scene_key = revision_scene_key(document_id, revision_id)
        scene_checksum = sha256_hex(scene_bytes)
        export_specs: list[tuple[str, str, str, str]] = []
        artifact_keys = [scene_key]
        for item in exports:
            key = revision_export_key(document_id, revision_id, item.format)
            artifact_keys.append(key)
            export_specs.append(
                (item.kind, key, sha256_hex(item.data), item.renderer_version)
            )

        grace_until = datetime.now(UTC) + timedelta(seconds=intent_grace_seconds)
        intent_id = self._reconciler.register_publication_intent(
            conn,
            document_id=document_id,
            expected_parent_revision_id=expected_parent_revision_id,
            artifact_keys=artifact_keys,
            grace_until=grace_until,
        )
        conn.commit()

        if write_artifacts:
            try:
                self._store.write_immutable(scene_key, scene_bytes)
                for item, (_kind, key, checksum, _renderer) in zip(
                    exports, export_specs, strict=True
                ):
                    self._store.write_immutable(
                        key, item.data, expected_checksum=checksum
                    )
            except PersistenceError:
                with conn.transaction():
                    conn.execute(
                        "DELETE FROM drawing.publication_intents WHERE id = %s",
                        (intent_id,),
                    )
                raise

        try:
            with conn.transaction():
                self._revisions.insert_revision(
                    conn,
                    revision_id=revision_id,
                    document_id=document_id,
                    parent_revision_id=expected_parent_revision_id,
                    schema_version=schema_version,
                    scene_uri=scene_key,
                    scene_checksum_sha256=scene_checksum,
                    author_type=author_type,
                    review_state=review_state,
                    validation_status=validation_status,
                )
                for _item, (kind, key, checksum, renderer_version) in zip(
                    exports, export_specs, strict=True
                ):
                    self._revisions.insert_export(
                        conn,
                        export_id=uuid.uuid4(),
                        revision_id=revision_id,
                        kind=kind,
                        uri=key,
                        checksum_sha256=checksum,
                        renderer_version=renderer_version,
                    )
                if carry_review_items_from is not None:
                    self._revisions.copy_review_items_forward(
                        conn,
                        source_revision_id=carry_review_items_from,
                        target_revision_id=revision_id,
                    )
                self._revisions.compare_and_swap_current(
                    conn,
                    document_id=document_id,
                    expected_parent_revision_id=expected_parent_revision_id,
                    new_revision_id=revision_id,
                )
                conn.execute(
                    "DELETE FROM drawing.publication_intents WHERE id = %s",
                    (intent_id,),
                )
        except ConflictError:
            raise
        except Exception:
            raise

        stored_checksum = self._store.checksum(scene_key)
        if stored_checksum != scene_checksum:
            raise PersistenceError(
                "artifact_checksum_mismatch",
                "scene artifact checksum does not match published metadata",
            )

        return PublishResult(
            revision_id=revision_id,
            scene_key=scene_key,
            scene_checksum_sha256=scene_checksum,
        )
