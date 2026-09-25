"""Run 04 API and worker integration tests."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from isometric_api.app import create_app
from isometric_persistence.config import DatabaseSettings, resolve_database_url
from isometric_persistence.db import DatabasePool
from isometric_persistence.migrate import apply_migrations
from isometric_persistence.repositories.jobs import JobRepository
from isometric_persistence.repositories.revisions import RevisionRepository
from isometric_worker.processor import process_job, revision_id_for_job
from isometric_worker.queue import LocalJobQueue
from isometric_worker.runner import run_once
from PIL import Image


def tiny_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color="white").save(buf, format="PNG")
    return buf.getvalue()


def tiny_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color="white").save(buf, format="JPEG")
    return buf.getvalue()


def require_database() -> str:
    try:
        return resolve_database_url()
    except RuntimeError:
        raise unittest.SkipTest("SUPABASE_DATABASE_URL is not set") from None


class UploadJobsIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db_url = require_database()
        cls.artifact_root = Path(tempfile.mkdtemp(prefix="isometric-api-artifacts-"))
        os.environ["ARTIFACT_ROOT"] = str(cls.artifact_root)
        os.environ["SUPABASE_DATABASE_URL"] = cls.db_url
        cls.pool = DatabasePool(DatabaseSettings(url=cls.db_url))
        with cls.pool.connection() as conn:
            apply_migrations(conn)
            conn.commit()
        cls.client = TestClient(create_app())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.pool.close()

    def _headers(self, owner: str = "owner-a") -> dict[str, str]:
        return {"X-Owner-Id": owner}

    def _upload(
        self,
        *,
        owner: str = "owner-a",
        key: str | None = None,
        data: bytes | None = None,
        options_json: str = "{}",
        filename: str = "page.png",
        mime: str = "image/png",
        client: TestClient | None = None,
    ):
        http = client or self.client
        files = {"file": (filename, data or tiny_png(), mime)}
        headers = self._headers(owner)
        if key:
            headers["Idempotency-Key"] = key
        return http.post(
            "/api/v1/documents",
            files=files,
            data={"profile_id": "piping_isometric", "options_json": options_json},
            headers=headers,
        )

    def test_valid_upload_reaches_fixture_revision_with_exports(self) -> None:
        response = self._upload()
        self.assertEqual(response.status_code, 202)
        body = response.json()
        job_id = body["job_id"]
        document_id = body["document_id"]
        job = self.client.get(f"/api/v1/jobs/{job_id}", headers=self._headers())
        self.assertEqual(job.status_code, 200)
        job_body = job.json()
        self.assertEqual(job_body["state"], "succeeded")
        self.assertIsNotNone(job_body["result_revision_id"])
        self.assertEqual(job_body["review_state"], "review_required")
        self.assertEqual(job_body["progress"]["stage"], "complete")
        self.assertNotIn("percent", job_body["progress"])
        revision_id = job_body["result_revision_id"]
        scene = self.client.get(
            f"/api/v1/documents/{document_id}/revisions/{revision_id}/scene",
            headers=self._headers(),
        )
        self.assertEqual(scene.status_code, 200)
        svg = self.client.get(
            f"/api/v1/documents/{document_id}/revisions/{revision_id}/exports/svg",
            headers=self._headers(),
        )
        png = self.client.get(
            f"/api/v1/documents/{document_id}/revisions/{revision_id}/exports/preview",
            headers=self._headers(),
        )
        self.assertEqual(svg.status_code, 200)
        self.assertEqual(png.status_code, 200)
        self.assertTrue(svg.content.startswith(b"<svg"))
        self.assertTrue(png.content.startswith(b"\x89PNG"))

    def test_invalid_file_is_rejected(self) -> None:
        response = self._upload(data=b"not-an-image")
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["code"], "unsupported_media_type")

    def test_idempotent_upload_returns_same_job(self) -> None:
        key = f"idem-{uuid.uuid4()}"
        first = self._upload(key=key)
        second = self._upload(key=key)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json()["document_id"], second.json()["document_id"])
        self.assertEqual(first.json()["job_id"], second.json()["job_id"])

    def test_idempotency_key_conflict(self) -> None:
        key = f"idem-{uuid.uuid4()}"
        self._upload(key=key)
        other = tiny_png() + b"x"
        response = self._upload(key=key, data=other)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "idempotency_conflict")

    def test_idempotency_options_conflict(self) -> None:
        key = f"idem-{uuid.uuid4()}"
        self._upload(key=key, options_json="{}")
        response = self._upload(key=key, options_json='{"flag":true}')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "idempotency_conflict")

    def test_unauthorized_without_owner_header(self) -> None:
        response = self.client.post(
            "/api/v1/documents",
            files={"file": ("page.png", tiny_png(), "image/png")},
            data={"profile_id": "piping_isometric", "options_json": "{}"},
        )
        self.assertEqual(response.status_code, 401)

    def test_unauthorized_get_document_without_header(self) -> None:
        created = self._upload(owner="get-unauth")
        document_id = created.json()["document_id"]
        denied = self.client.get(f"/api/v1/documents/{document_id}")
        self.assertEqual(denied.status_code, 401)

    def test_forbidden_for_other_owner(self) -> None:
        created = self._upload(owner="owner-a")
        document_id = created.json()["document_id"]
        denied = self.client.get(
            f"/api/v1/documents/{document_id}",
            headers=self._headers("owner-b"),
        )
        self.assertEqual(denied.status_code, 403)

    def test_forbidden_source_and_revisions_for_other_owner(self) -> None:
        created = self._upload(owner="iso-a")
        document_id = created.json()["document_id"]
        headers = self._headers("iso-b")
        source = self.client.get(
            f"/api/v1/documents/{document_id}/source", headers=headers
        )
        revisions = self.client.get(
            f"/api/v1/documents/{document_id}/revisions", headers=headers
        )
        self.assertEqual(source.status_code, 403)
        self.assertEqual(revisions.status_code, 403)

    def test_cancel_before_publication(self) -> None:
        os.environ["SKIP_INLINE_WORKER"] = "1"
        try:
            app = create_app()
            client = TestClient(app)
            created = client.post(
                "/api/v1/documents",
                files={"file": ("page.png", tiny_png(), "image/png")},
                data={"profile_id": "piping_isometric", "options_json": "{}"},
                headers=self._headers("cancel-owner"),
            )
            self.assertEqual(created.status_code, 202)
            job_id = created.json()["job_id"]
            canceled = client.post(
                f"/api/v1/jobs/{job_id}/cancel", headers=self._headers("cancel-owner")
            )
            self.assertEqual(canceled.status_code, 200)
            store = app.state.runtime.store
            process_job(self.pool, store, uuid.UUID(job_id))
            job = client.get(
                f"/api/v1/jobs/{job_id}", headers=self._headers("cancel-owner")
            )
            self.assertEqual(job.json()["state"], "canceled")
            doc = client.get(
                f"/api/v1/documents/{created.json()['document_id']}",
                headers=self._headers("cancel-owner"),
            )
            self.assertIsNone(doc.json()["current_revision_id"])
        finally:
            os.environ.pop("SKIP_INLINE_WORKER", None)

    def test_duplicate_queue_delivery_does_not_duplicate_revision(self) -> None:
        created = self._upload(owner="dup-owner")
        document_id = created.json()["document_id"]
        job_id = uuid.UUID(created.json()["job_id"])
        store = self.client.app.state.runtime.store
        process_job(self.pool, store, job_id)
        process_job(self.pool, store, job_id)
        revs = RevisionRepository()
        with self.pool.connection() as conn:
            rows = revs.list_for_document(conn, uuid.UUID(document_id))
        self.assertEqual(len(rows), 1)

    def test_list_documents_only_returns_caller_items(self) -> None:
        self._upload(owner="list-a")
        listed = self.client.get("/api/v1/documents", headers=self._headers("list-b"))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["items"], [])

    def test_list_includes_review_state_for_owner(self) -> None:
        owner = f"list-review-{uuid.uuid4()}"
        self._upload(owner=owner)
        listed = self.client.get("/api/v1/documents", headers=self._headers(owner))
        self.assertEqual(listed.status_code, 200)
        items = listed.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["review_state"], "review_required")

    def test_cancel_on_running_job_with_expired_lease(self) -> None:
        os.environ["SKIP_INLINE_WORKER"] = "1"
        try:
            app = create_app()
            client = TestClient(app)
            created = client.post(
                "/api/v1/documents",
                files={"file": ("page.png", tiny_png(), "image/png")},
                data={"profile_id": "piping_isometric", "options_json": "{}"},
                headers=self._headers("cancel-lease-owner"),
            )
            job_id = uuid.UUID(created.json()["job_id"])
            document_id = created.json()["document_id"]
            jobs = JobRepository()
            with self.pool.connection() as conn:
                jobs.claim(conn, job_id=job_id)
                jobs.request_cancel(conn, job_id)
                conn.execute(
                    """
                    UPDATE drawing.jobs
                    SET lease_expires_at = now() - interval '1 minute'
                    WHERE id = %s
                    """,
                    (job_id,),
                )
                conn.commit()
            queue = LocalJobQueue()
            run_once(self.pool, app.state.runtime.store, queue)
            job = client.get(
                f"/api/v1/jobs/{job_id}", headers=self._headers("cancel-lease-owner")
            )
            self.assertEqual(job.json()["state"], "canceled")
            doc = client.get(
                f"/api/v1/documents/{document_id}",
                headers=self._headers("cancel-lease-owner"),
            )
            self.assertIsNone(doc.json()["current_revision_id"])
        finally:
            os.environ.pop("SKIP_INLINE_WORKER", None)

    def test_expired_lease_recovery_succeeds(self) -> None:
        os.environ["SKIP_INLINE_WORKER"] = "1"
        try:
            app = create_app()
            client = TestClient(app)
            created = client.post(
                "/api/v1/documents",
                files={"file": ("page.png", tiny_png(), "image/png")},
                data={"profile_id": "piping_isometric", "options_json": "{}"},
                headers=self._headers("lease-owner"),
            )
            job_id = uuid.UUID(created.json()["job_id"])
            document_id = uuid.UUID(created.json()["document_id"])
            jobs = JobRepository()
            with self.pool.connection() as conn:
                claimed = jobs.claim(conn, job_id=job_id)
                conn.commit()
            self.assertIsNotNone(claimed)
            with self.pool.connection() as conn:
                conn.execute(
                    """
                    UPDATE drawing.jobs
                    SET lease_expires_at = now() - interval '1 minute'
                    WHERE id = %s
                    """,
                    (job_id,),
                )
                conn.commit()
            queue = LocalJobQueue()
            run_once(self.pool, app.state.runtime.store, queue)
            job = client.get(
                f"/api/v1/jobs/{job_id}", headers=self._headers("lease-owner")
            )
            self.assertEqual(job.json()["state"], "succeeded")
            revs = RevisionRepository()
            with self.pool.connection() as conn:
                rows = revs.list_for_document(conn, document_id)
            self.assertEqual(len(rows), 1)
        finally:
            os.environ.pop("SKIP_INLINE_WORKER", None)

    def test_retry_completes_job_when_revision_already_published(self) -> None:
        os.environ["SKIP_INLINE_WORKER"] = "1"
        try:
            app = create_app()
            client = TestClient(app)
            created = client.post(
                "/api/v1/documents",
                files={"file": ("page.png", tiny_png(), "image/png")},
                data={"profile_id": "piping_isometric", "options_json": "{}"},
                headers=self._headers("retry-owner"),
            )
            job_id = uuid.UUID(created.json()["job_id"])
            document_id = uuid.UUID(created.json()["document_id"])
            store = app.state.runtime.store
            process_job(self.pool, store, job_id)
            revision_id = revision_id_for_job(job_id)
            with self.pool.connection() as conn:
                conn.execute(
                    """
                    UPDATE drawing.jobs
                    SET state = 'running',
                        result_revision_id = NULL,
                        lease_expires_at = now() - interval '1 minute'
                    WHERE id = %s
                    """,
                    (job_id,),
                )
                conn.commit()
            queue = LocalJobQueue()
            run_once(self.pool, store, queue)
            job = client.get(
                f"/api/v1/jobs/{job_id}", headers=self._headers("retry-owner")
            )
            self.assertEqual(job.json()["state"], "succeeded")
            self.assertEqual(job.json()["result_revision_id"], str(revision_id))
            revs = RevisionRepository()
            with self.pool.connection() as conn:
                rows = revs.list_for_document(conn, document_id)
            self.assertEqual(len(rows), 1)
        finally:
            os.environ.pop("SKIP_INLINE_WORKER", None)

    def test_processing_invalid_leaves_no_revision(self) -> None:
        os.environ["SKIP_INLINE_WORKER"] = "1"
        try:
            app = create_app()
            client = TestClient(app)
            created = client.post(
                "/api/v1/documents",
                files={"file": ("page.png", tiny_png(), "image/png")},
                data={"profile_id": "piping_isometric", "options_json": "{}"},
                headers=self._headers("invalid-owner"),
            )
            job_id = uuid.UUID(created.json()["job_id"])
            document_id = uuid.UUID(created.json()["document_id"])
            store = app.state.runtime.store
            with patch(
                "isometric_worker.processor.load_scene",
                side_effect=ValueError("bad scene"),
            ):
                process_job(self.pool, store, job_id)
            job = client.get(
                f"/api/v1/jobs/{job_id}", headers=self._headers("invalid-owner")
            )
            self.assertEqual(job.json()["state"], "failed")
            self.assertEqual(job.json()["error_code"], "processing_invalid")
            revs = RevisionRepository()
            with self.pool.connection() as conn:
                rows = revs.list_for_document(conn, document_id)
            self.assertEqual(len(rows), 0)
        finally:
            os.environ.pop("SKIP_INLINE_WORKER", None)

    def test_transient_failure_requeues_then_exhausts(self) -> None:
        os.environ["SKIP_INLINE_WORKER"] = "1"
        try:
            app = create_app()
            client = TestClient(app)
            created = client.post(
                "/api/v1/documents",
                files={"file": ("page.png", tiny_png(), "image/png")},
                data={"profile_id": "piping_isometric", "options_json": "{}"},
                headers=self._headers("transient-owner"),
            )
            job_id = uuid.UUID(created.json()["job_id"])
            store = app.state.runtime.store
            queue = LocalJobQueue()
            with patch(
                "isometric_worker.processor.RevisionPublisher.publish",
                side_effect=OSError("disk full"),
            ):
                process_job(self.pool, store, job_id, queue=queue)
            job = client.get(
                f"/api/v1/jobs/{job_id}", headers=self._headers("transient-owner")
            )
            self.assertEqual(job.json()["state"], "queued")
            with patch(
                "isometric_worker.processor.RevisionPublisher.publish",
                side_effect=OSError("disk full"),
            ):
                process_job(self.pool, store, job_id, queue=queue)
                process_job(self.pool, store, job_id, queue=queue)
            job = client.get(
                f"/api/v1/jobs/{job_id}", headers=self._headers("transient-owner")
            )
            self.assertEqual(job.json()["state"], "failed")
            self.assertEqual(job.json()["error_code"], "worker_exhausted")
        finally:
            os.environ.pop("SKIP_INLINE_WORKER", None)

    def test_missing_scene_artifact(self) -> None:
        created = self._upload(owner="missing-artifact")
        document_id = created.json()["document_id"]
        job = self.client.get(
            f"/api/v1/jobs/{created.json()['job_id']}",
            headers=self._headers("missing-artifact"),
        )
        revision_id = job.json()["result_revision_id"]
        revs = RevisionRepository()
        with self.pool.connection() as conn:
            rev = revs.get_revision(conn, uuid.UUID(revision_id))
        assert rev is not None
        scene_path = self.artifact_root / rev.scene_uri
        scene_path.unlink()
        scene = self.client.get(
            f"/api/v1/documents/{document_id}/revisions/{revision_id}/scene",
            headers=self._headers("missing-artifact"),
        )
        self.assertEqual(scene.status_code, 404)
        self.assertEqual(scene.json()["code"], "missing_artifact")
        with self.pool.connection() as conn:
            rows = revs.list_for_document(conn, uuid.UUID(document_id))
        self.assertEqual(len(rows), 1)

    def test_image_too_large(self) -> None:
        os.environ["MAX_PIXELS"] = "100"
        try:
            client = TestClient(create_app())
            response = self._upload(client=client)
            self.assertEqual(response.status_code, 413)
            self.assertEqual(response.json()["code"], "image_too_large")
        finally:
            os.environ.pop("MAX_PIXELS", None)

    def test_payload_too_large(self) -> None:
        os.environ["MAX_UPLOAD_BYTES"] = "10"
        try:
            client = TestClient(create_app())
            response = self._upload(client=client)
            self.assertEqual(response.status_code, 413)
            self.assertEqual(response.json()["code"], "payload_too_large")
        finally:
            os.environ.pop("MAX_UPLOAD_BYTES", None)

    def test_jpeg_upload_succeeds(self) -> None:
        response = self._upload(
            owner="jpeg-owner",
            data=tiny_jpeg(),
            filename="page.jpg",
            mime="image/jpeg",
        )
        self.assertEqual(response.status_code, 202)
        job = self.client.get(
            f"/api/v1/jobs/{response.json()['job_id']}",
            headers=self._headers("jpeg-owner"),
        )
        self.assertEqual(job.json()["state"], "succeeded")


if __name__ == "__main__":
    unittest.main()
