"""Run 03 exit checks for persistence and artifacts."""

from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from isometric_persistence.artifacts import (
    ArtifactChecksumMismatch,
    ArtifactWriteError,
    FilesystemArtifactStore,
    sha256_hex,
)
from isometric_persistence.config import DatabaseSettings, resolve_database_url
from isometric_persistence.db import DatabasePool
from isometric_persistence.errors import ConflictError
from isometric_persistence.keys import revision_scene_key
from isometric_persistence.migrate import apply_migrations
from isometric_persistence.publishing import RevisionPublisher
from isometric_persistence.repositories.documents import DocumentRepository
from isometric_persistence.repositories.jobs import JobRepository
from isometric_persistence.repositories.reconciler import ArtifactReconciler
from isometric_persistence.repositories.revisions import RevisionRepository

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scene-schema"
    / "fixtures"
    / "valid"
    / "annotation.json"
)


def require_database() -> DatabaseSettings:
    try:
        return DatabaseSettings(url=resolve_database_url())
    except RuntimeError:
        raise unittest.SkipTest("SUPABASE_DATABASE_URL is not set") from None


class PersistenceExitChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = require_database()
        cls.pool = DatabasePool(cls.settings)
        with cls.pool.connection() as conn:
            apply_migrations(conn)
            conn.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.pool.close()

    def setUp(self) -> None:
        self.artifact_root = Path(tempfile.mkdtemp(prefix="isometric-artifacts-"))
        self.store = FilesystemArtifactStore(self.artifact_root)
        self.document_id = uuid.uuid4()
        self.docs = DocumentRepository()
        with self.pool.connection() as conn:
            self.docs.create(
                conn,
                document_id=self.document_id,
                owner_id="test-owner",
                source_hash="abc",
                source_uri=f"documents/{self.document_id}/original",
                source_mime="image/png",
            )
            conn.commit()

    def test_migrations_replay_without_drift(self) -> None:
        with self.pool.connection() as conn:
            second = apply_migrations(conn)
            conn.commit()
        self.assertEqual(second, [])

    def test_publish_writes_artifacts_before_pointer(self) -> None:
        scene = FIXTURE_PATH.read_bytes()
        publisher = RevisionPublisher(self.store)
        with self.pool.connection() as conn:
            result = publisher.publish(
                conn,
                document_id=self.document_id,
                expected_parent_revision_id=None,
                schema_version="1.0",
                scene_bytes=scene,
                author_type="machine",
                review_state="in_review",
                validation_status="valid",
                exports=[],
            )
            conn.commit()
        with self.pool.connection() as conn:
            doc = self.docs.get(conn, self.document_id)
        self.assertEqual(doc.current_revision_id, result.revision_id)
        self.assertTrue(self.store.exists(result.scene_key))

    def test_storage_failure_leaves_prior_revision(self) -> None:
        scene = FIXTURE_PATH.read_bytes()
        publisher = RevisionPublisher(self.store)
        with self.pool.connection() as conn:
            first = publisher.publish(
                conn,
                document_id=self.document_id,
                expected_parent_revision_id=None,
                schema_version="1.0",
                scene_bytes=scene,
                author_type="machine",
                review_state="in_review",
                validation_status="valid",
                exports=[],
            )
            conn.commit()

        failing_store = mock.Mock(spec=self.store)
        failing_store.write_immutable.side_effect = ArtifactWriteError("k", "disk full")
        failing_publisher = RevisionPublisher(failing_store)
        with self.pool.connection() as conn:
            with self.assertRaises(ArtifactWriteError):
                failing_publisher.publish(
                    conn,
                    document_id=self.document_id,
                    expected_parent_revision_id=first.revision_id,
                    schema_version="1.0",
                    scene_bytes=scene,
                    author_type="machine",
                    review_state="in_review",
                    validation_status="valid",
                    exports=[],
                )
        with self.pool.connection() as conn:
            doc = self.docs.get(conn, self.document_id)
        self.assertEqual(doc.current_revision_id, first.revision_id)

    def test_database_failure_leaves_reclaimable_orphan(self) -> None:
        scene = FIXTURE_PATH.read_bytes()
        publisher = RevisionPublisher(self.store)
        with mock.patch.object(
            RevisionRepository,
            "insert_revision",
            side_effect=RuntimeError("database unavailable"),
        ):
            with self.pool.connection() as conn:
                with self.assertRaises(RuntimeError):
                    publisher.publish(
                        conn,
                        document_id=self.document_id,
                        expected_parent_revision_id=None,
                        schema_version="1.0",
                        scene_bytes=scene,
                        author_type="machine",
                        review_state="in_review",
                        validation_status="valid",
                        exports=[],
                    )
        orphan_keys = [
            key
            for key in self.store.list_keys()
            if key.startswith(f"documents/{self.document_id}/revisions/")
        ]
        self.assertEqual(len(orphan_keys), 1)
        with self.pool.connection() as conn:
            doc = self.docs.get(conn, self.document_id)
            conn.execute(
                """
                UPDATE drawing.publication_intents
                SET grace_until = now() - interval '1 hour'
                WHERE document_id = %s
                """,
                (self.document_id,),
            )
            conn.commit()
            report = ArtifactReconciler(self.store).dry_run(conn)
        self.assertIsNone(doc.current_revision_id)
        self.assertIn(orphan_keys[0], report.unreferenced_keys)

    def test_concurrent_parent_edits_one_conflict(self) -> None:
        scene = FIXTURE_PATH.read_bytes()
        publisher = RevisionPublisher(self.store)
        with self.pool.connection() as conn:
            parent = publisher.publish(
                conn,
                document_id=self.document_id,
                expected_parent_revision_id=None,
                schema_version="1.0",
                scene_bytes=scene,
                author_type="machine",
                review_state="in_review",
                validation_status="valid",
                exports=[],
            )
            conn.commit()

        winner_id = uuid.uuid4()
        loser_id = uuid.uuid4()
        revs = RevisionRepository()
        with self.pool.connection() as conn_a, self.pool.connection() as conn_b:
            with conn_a.transaction():
                revs.insert_revision(
                    conn_a,
                    revision_id=winner_id,
                    document_id=self.document_id,
                    parent_revision_id=parent.revision_id,
                    schema_version="1.0",
                    scene_uri=revision_scene_key(self.document_id, winner_id),
                    scene_checksum_sha256=sha256_hex(scene),
                    author_type="human",
                    review_state="in_review",
                    validation_status="valid",
                )
                revs.compare_and_swap_current(
                    conn_a,
                    document_id=self.document_id,
                    expected_parent_revision_id=parent.revision_id,
                    new_revision_id=winner_id,
                )
            with conn_b.transaction():
                revs.insert_revision(
                    conn_b,
                    revision_id=loser_id,
                    document_id=self.document_id,
                    parent_revision_id=parent.revision_id,
                    schema_version="1.0",
                    scene_uri=revision_scene_key(self.document_id, loser_id),
                    scene_checksum_sha256=sha256_hex(scene),
                    author_type="human",
                    review_state="in_review",
                    validation_status="valid",
                )
                with self.assertRaises(ConflictError):
                    revs.compare_and_swap_current(
                        conn_b,
                        document_id=self.document_id,
                        expected_parent_revision_id=parent.revision_id,
                        new_revision_id=loser_id,
                    )

        with self.pool.connection() as conn:
            doc = self.docs.get(conn, self.document_id)
        self.assertEqual(doc.current_revision_id, winner_id)

    def test_checksum_mismatch_detected(self) -> None:
        data = b"scene"
        key = "test/checksum"
        self.store.write_immutable(key, data)
        with self.assertRaises(ArtifactChecksumMismatch):
            self.store.write_immutable(key, b"other")

    def test_artifact_keys_not_overwritten(self) -> None:
        data = b"same"
        key = "immutable/key"
        first = self.store.write_immutable(key, data)
        second = self.store.write_immutable(key, data)
        self.assertEqual(first.checksum_sha256, second.checksum_sha256)

    def test_job_and_outbox_committed_together(self) -> None:
        jobs = JobRepository()
        job_id = uuid.uuid4()
        event_key = f"job-created-{job_id}"
        with self.pool.connection() as conn:
            jobs.create_with_outbox(
                conn,
                job_id=job_id,
                document_id=self.document_id,
                state="queued",
                input_hash="in",
                options_hash="opt",
                pipeline_version="0",
                profile_version="piping_isometric",
                event_key=event_key,
            )
            conn.commit()
        with self.pool.connection() as conn:
            row = conn.execute(
                "SELECT id FROM drawing.outbox_events WHERE event_key = %s",
                (event_key,),
            ).fetchone()
        self.assertIsNotNone(row)

    def test_job_logs_append_and_list_order(self) -> None:
        jobs = JobRepository()
        job_id = uuid.uuid4()
        event_key = f"job-logs-{job_id}"
        with self.pool.connection() as conn:
            jobs.create_with_outbox(
                conn,
                job_id=job_id,
                document_id=self.document_id,
                state="queued",
                input_hash="in",
                options_hash="opt",
                pipeline_version="0",
                profile_version="piping_isometric",
                event_key=event_key,
            )
            jobs.append_job_log(
                conn,
                job_id=job_id,
                stage="normalize_page",
                message="Starting normalize_page",
            )
            jobs.append_job_log(
                conn,
                job_id=job_id,
                stage="normalize_page",
                message="Finished normalize_page",
                detail={"blur_score": 1.2},
            )
            conn.commit()
        with self.pool.connection() as conn:
            logs = jobs.list_job_logs(conn, job_id)
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].message, "Starting normalize_page")
        self.assertEqual(logs[1].detail.get("blur_score"), 1.2)

    def test_reconciler_finds_orphan(self) -> None:
        scene = FIXTURE_PATH.read_bytes()
        orphan_key = "orphan/unreferenced.json"
        self.store.write_immutable(orphan_key, b"{}")
        publisher = RevisionPublisher(self.store)
        with self.pool.connection() as conn:
            publisher.publish(
                conn,
                document_id=self.document_id,
                expected_parent_revision_id=None,
                schema_version="1.0",
                scene_bytes=scene,
                author_type="machine",
                review_state="in_review",
                validation_status="valid",
                exports=[],
            )
            conn.commit()
            report = ArtifactReconciler(self.store).dry_run(conn)
        self.assertIn(orphan_key, report.unreferenced_keys)
        referenced = {k for k in self.store.list_keys() if k != orphan_key}
        for key in referenced:
            self.assertNotIn(key, report.unreferenced_keys)

    def test_review_issue_key_stable_across_revision(self) -> None:
        scene = FIXTURE_PATH.read_bytes()
        issue_key = f"stable-issue-{self.document_id}"
        revs = RevisionRepository()
        publisher = RevisionPublisher(self.store, revisions=revs)
        with self.pool.connection() as conn:
            first = publisher.publish(
                conn,
                document_id=self.document_id,
                expected_parent_revision_id=None,
                schema_version="1.0",
                scene_bytes=scene,
                author_type="machine",
                review_state="in_review",
                validation_status="valid",
                exports=[],
            )
            revs.insert_review_item(
                conn,
                issue_key=issue_key,
                revision_id=first.revision_id,
                issue_type="symbol",
                severity="high",
                state="open",
            )
            conn.commit()
        with self.pool.connection() as conn:
            second = publisher.publish(
                conn,
                document_id=self.document_id,
                expected_parent_revision_id=first.revision_id,
                schema_version="1.0",
                scene_bytes=scene,
                author_type="human",
                review_state="in_review",
                validation_status="valid",
                exports=[],
                carry_review_items_from=first.revision_id,
            )
            conn.commit()
            rows = conn.execute(
                """
                SELECT issue_key, revision_id
                FROM drawing.review_items
                WHERE issue_key = %s
                ORDER BY created_at
                """,
                (issue_key,),
            ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["issue_key"], issue_key)
        self.assertEqual(rows[1]["issue_key"], issue_key)
        self.assertEqual(rows[1]["revision_id"], second.revision_id)

    def test_publish_without_advancing_current(self) -> None:
        scene = FIXTURE_PATH.read_bytes()
        publisher = RevisionPublisher(self.store)
        with self.pool.connection() as conn:
            first = publisher.publish(
                conn,
                document_id=self.document_id,
                expected_parent_revision_id=None,
                schema_version="1.0",
                scene_bytes=scene,
                author_type="human",
                review_state="ready",
                validation_status="valid",
                exports=[],
            )
            conn.commit()
        with self.pool.connection() as conn:
            doc = DocumentRepository().get(conn, self.document_id)
            self.assertEqual(doc.current_revision_id, first.revision_id)
        with self.pool.connection() as conn:
            candidate = publisher.publish(
                conn,
                document_id=self.document_id,
                expected_parent_revision_id=first.revision_id,
                schema_version="1.0",
                scene_bytes=scene,
                author_type="machine",
                review_state="review_required",
                validation_status="valid",
                exports=[],
                advance_current_revision=False,
            )
            conn.commit()
        with self.pool.connection() as conn:
            doc = DocumentRepository().get(conn, self.document_id)
            self.assertEqual(doc.current_revision_id, first.revision_id)
            self.assertNotEqual(candidate.revision_id, first.revision_id)


if __name__ == "__main__":
    unittest.main()
