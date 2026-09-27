"""Drawing reading lane integration tests."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from isometric_api.app import create_app
from isometric_persistence.config import DatabaseSettings, resolve_database_url
from isometric_persistence.db import DatabasePool
from isometric_persistence.keys import document_page_key
from isometric_persistence.errors import PersistenceError
from isometric_persistence.migrate import apply_migrations
from isometric_persistence.repositories.jobs import JobRepository
from isometric_worker.processor import process_job
from PIL import Image


def tiny_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color="white").save(buf, format="PNG")
    return buf.getvalue()


def require_database() -> str:
    try:
        return resolve_database_url()
    except RuntimeError:
        raise unittest.SkipTest("SUPABASE_DATABASE_URL is not set") from None


class DrawingReadingIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db_url = require_database()
        cls.artifact_root = Path(tempfile.mkdtemp(prefix="isometric-reading-artifacts-"))
        os.environ["ARTIFACT_ROOT"] = str(cls.artifact_root)
        os.environ["SUPABASE_DATABASE_URL"] = cls.db_url
        os.environ["SKIP_INLINE_WORKER"] = "1"
        os.environ["ISOMETRIC_WORKER_FIXTURE_ONLY"] = "1"
        cls.pool = DatabasePool(DatabaseSettings(url=cls.db_url))
        with cls.pool.connection() as conn:
            apply_migrations(conn)
            conn.commit()
        cls.client = TestClient(create_app())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.pool.close()
        os.environ.pop("SKIP_INLINE_WORKER", None)
        os.environ.pop("ISOMETRIC_WORKER_FIXTURE_ONLY", None)
        os.environ.pop("ISOMETRIC_FAKE_DRAWING_READING", None)
        os.environ.pop("VISION_ENABLED", None)

    def setUp(self) -> None:
        os.environ.pop("ISOMETRIC_FAKE_DRAWING_READING", None)
        os.environ.pop("VISION_ENABLED", None)

    def _headers(self, owner: str = "owner-reading") -> dict[str, str]:
        return {"X-Owner-Id": owner}

    def _upload(self, *, run_pipeline: bool = True) -> tuple[str, str]:
        files = {"file": ("page.png", tiny_png(), "image/png")}
        response = self.client.post(
            "/api/v1/documents",
            files=files,
            data={"profile_id": "piping_isometric", "options_json": "{}"},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 202)
        body = response.json()
        document_id = body["document_id"]
        pipeline_job_id = body["job_id"]
        store = self.client.app.state.runtime.store
        if run_pipeline:
            process_job(self.pool, store, uuid.UUID(pipeline_job_id))
            jobs = JobRepository()
            with self.pool.connection() as conn:
                pipeline = jobs.get(conn, uuid.UUID(pipeline_job_id))
            self.assertIsNotNone(pipeline)
            assert pipeline is not None
            self.assertEqual(
                pipeline.state,
                "succeeded",
                pipeline.error_code,
            )
            try:
                store.read(document_page_key(uuid.UUID(document_id)))
            except (FileNotFoundError, PersistenceError) as exc:
                self.fail(f"page.png missing after pipeline: {exc}")
        return document_id, pipeline_job_id

    def _ensure_page(self, document_id: str, pipeline_job_id: str) -> None:
        store = self.client.app.state.runtime.store
        key = document_page_key(uuid.UUID(document_id))
        try:
            store.read(key)
            return
        except (FileNotFoundError, PersistenceError):
            process_job(self.pool, store, uuid.UUID(pipeline_job_id))
        try:
            store.read(key)
        except (FileNotFoundError, PersistenceError) as exc:
            self.fail(f"page.png missing after pipeline retry: {exc}")

    def _reading_job_id(self, document_id: str) -> uuid.UUID:
        jobs = JobRepository()
        with self.pool.connection() as conn:
            row = jobs.get_newest_reading_job(conn, uuid.UUID(document_id))
        self.assertIsNotNone(row)
        assert row is not None
        return row.id

    def _process_reading(
        self, document_id: str, pipeline_job_id: str | None = None
    ) -> None:
        if pipeline_job_id is not None:
            self._ensure_page(document_id, pipeline_job_id)
        reading_job_id = self._reading_job_id(document_id)
        jobs = JobRepository()
        store = self.client.app.state.runtime.store
        for _ in range(5):
            process_job(self.pool, store, reading_job_id)
            with self.pool.connection() as conn:
                row = jobs.get(conn, reading_job_id)
            self.assertIsNotNone(row)
            assert row is not None
            if row.state not in {"queued", "running"}:
                return
        self.fail(f"drawing_reading job {reading_job_id} stuck in {row.state}")

    def test_upload_enqueues_reading_job(self) -> None:
        files = {"file": ("page.png", tiny_png(), "image/png")}
        response = self.client.post(
            "/api/v1/documents",
            files=files,
            data={"profile_id": "piping_isometric", "options_json": "{}"},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 202)
        document_id = response.json()["document_id"]
        with self.pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT kind FROM drawing.jobs
                WHERE document_id = %s
                ORDER BY created_at ASC
                """,
                (uuid.UUID(document_id),),
            ).fetchall()
        kinds = sorted(row["kind"] for row in rows)
        self.assertEqual(kinds, ["drawing_reading", "pipeline"])
        self.assertEqual(len(rows), 2)

    def test_idempotent_upload_does_not_duplicate_jobs(self) -> None:
        key = "reading-idem-key"
        headers = {**self._headers(), "Idempotency-Key": key}
        files = {"file": ("page.png", tiny_png(), "image/png")}
        first = self.client.post(
            "/api/v1/documents",
            files=files,
            data={"profile_id": "piping_isometric", "options_json": "{}"},
            headers=headers,
        )
        second = self.client.post(
            "/api/v1/documents",
            files=files,
            data={"profile_id": "piping_isometric", "options_json": "{}"},
            headers=headers,
        )
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        document_id = first.json()["document_id"]
        with self.pool.connection() as conn:
            count = conn.execute(
                "SELECT count(*) AS c FROM drawing.jobs WHERE document_id = %s",
                (uuid.UUID(document_id),),
            ).fetchone()
        self.assertEqual(count["c"], 2)

    def test_reprocess_enqueues_reading_job(self) -> None:
        document_id, _ = self._upload(run_pipeline=False)
        response = self.client.post(
            f"/api/v1/documents/{document_id}/reprocess",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 202)
        with self.pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT kind FROM drawing.jobs
                WHERE document_id = %s AND kind = 'drawing_reading'
                """,
                (uuid.UUID(document_id),),
            ).fetchall()
        self.assertEqual(len(rows), 2)

    def test_vision_disabled_completes_without_http(self) -> None:
        document_id, pipeline_job_id = self._upload()
        reading = self.client.get(
            f"/api/v1/documents/{document_id}/drawing-reading",
            headers=self._headers(),
        )
        self.assertEqual(reading.status_code, 200)
        self.assertEqual(reading.json()["status"], "pending")
        self._process_reading(document_id, pipeline_job_id)
        reading = self.client.get(
            f"/api/v1/documents/{document_id}/drawing-reading",
            headers=self._headers(),
        )
        self.assertEqual(reading.json()["status"], "disabled")

    def test_fake_valid_table_ready(self) -> None:
        os.environ["VISION_ENABLED"] = "1"
        os.environ["ISOMETRIC_FAKE_DRAWING_READING"] = "valid"
        document_id, _ = self._upload()
        self._process_reading(document_id, pipeline_job_id)
        reading = self.client.get(
            f"/api/v1/documents/{document_id}/drawing-reading",
            headers=self._headers(),
        )
        body = reading.json()
        self.assertEqual(body["status"], "ready", body)
        self.assertEqual(len(body["groups"]), 4)
        self.assertEqual(body["groups"][0]["rows"][0]["reading"], '6"-150#')

    def test_invalid_workers_falls_through_to_gemini(self) -> None:
        os.environ["VISION_ENABLED"] = "1"
        os.environ["ISOMETRIC_FAKE_DRAWING_READING"] = "invalid_then_valid"
        document_id, _ = self._upload()
        self._process_reading(document_id, pipeline_job_id)
        reading = self.client.get(
            f"/api/v1/documents/{document_id}/drawing-reading",
            headers=self._headers(),
        )
        body = reading.json()
        self.assertEqual(body["status"], "ready", body)
        self.assertEqual(body.get("provider"), "fake_gemini")

    def test_both_providers_fail_leaves_scene(self) -> None:
        os.environ["VISION_ENABLED"] = "1"
        os.environ["ISOMETRIC_FAKE_DRAWING_READING"] = "fail"
        document_id, pipeline_job_id = self._upload()
        self._process_reading(document_id, pipeline_job_id)
        reading = self.client.get(
            f"/api/v1/documents/{document_id}/drawing-reading",
            headers=self._headers(),
        )
        self.assertEqual(reading.json()["status"], "unavailable")
        pipeline = self.client.get(
            f"/api/v1/jobs/{pipeline_job_id}",
            headers=self._headers(),
        )
        self.assertEqual(pipeline.json()["state"], "succeeded")
        self.assertIsNotNone(pipeline.json()["result_revision_id"])

    def test_missing_page_when_pipeline_terminal(self) -> None:
        document_id, _ = self._upload()
        page_key = document_page_key(uuid.UUID(document_id))
        page_path = self.artifact_root / page_key
        if page_path.exists():
            page_path.unlink()
        self._process_reading(document_id)
        reading = self.client.get(
            f"/api/v1/documents/{document_id}/drawing-reading",
            headers=self._headers(),
        )
        body = reading.json()
        self.assertEqual(body["status"], "unavailable")
        self.assertEqual(body["error_code"], "missing_page")

    def test_absent_when_no_reading_job(self) -> None:
        document_id = uuid.uuid4()
        response = self.client.get(
            f"/api/v1/documents/{document_id}/drawing-reading",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 404)
