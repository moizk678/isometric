"""Run 05 W1A API follow-up tests."""

from __future__ import annotations

import io
import os
import threading
import unittest
import uuid
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

from fastapi.testclient import TestClient
from isometric_api.app import create_app
from isometric_persistence.config import DatabaseSettings
from isometric_persistence.db import DatabasePool
from isometric_persistence.migrate import apply_migrations
from PIL import Image


def tiny_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color="white").save(buf, format="PNG")
    return buf.getvalue()


def exif_rotated_jpeg() -> tuple[bytes, tuple[int, int]]:
    """JPEG 100x50 with EXIF orientation 6 (90° CW); display size is 50x100."""
    img = Image.new("RGB", (100, 50), color="blue")
    exif = img.getexif()
    exif[274] = 6
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue(), (50, 100)


def require_database() -> str:
    url = os.environ.get("LOCAL_DATABASE_URL")
    if not url:
        raise unittest.SkipTest("LOCAL_DATABASE_URL is not set")
    return url


class ApiFollowupsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db_url = require_database()
        cls.artifact_root = Path(mkdtemp(prefix="isometric-w1a-artifacts-"))
        os.environ["ARTIFACT_ROOT"] = str(cls.artifact_root)
        os.environ["LOCAL_DATABASE_URL"] = cls.db_url
        pool = DatabasePool(DatabaseSettings(url=cls.db_url))
        with pool.connection() as conn:
            apply_migrations(conn)
            conn.commit()
        pool.close()
        cls.client = TestClient(create_app())

    def _headers(self, owner: str = "w1a-owner") -> dict[str, str]:
        return {"X-Owner-Id": owner}

    def _upload(
        self,
        *,
        owner: str = "w1a-owner",
        key: str | None = None,
        data: bytes | None = None,
        filename: str = "drawings/iso-42.png",
    ):
        files = {"file": (filename, data or tiny_png(), "image/png")}
        headers = self._headers(owner)
        if key:
            headers["Idempotency-Key"] = key
        return self.client.post(
            "/api/v1/documents",
            files=files,
            data={"profile_id": "piping_isometric", "options_json": "{}"},
            headers=headers,
        )

    def test_filename_and_profile_round_trip(self) -> None:
        owner = f"meta-{uuid.uuid4()}"
        created = self._upload(owner=owner, filename="nested/path/my-drawing.png")
        self.assertEqual(created.status_code, 202)
        document_id = created.json()["document_id"]

        detail = self.client.get(
            f"/api/v1/documents/{document_id}", headers=self._headers(owner)
        )
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertEqual(body["original_filename"], "my-drawing.png")
        self.assertEqual(body["profile_id"], "piping_isometric")

        listed = self.client.get("/api/v1/documents", headers=self._headers(owner))
        item = next(
            i for i in listed.json()["items"] if i["document_id"] == document_id
        )
        self.assertEqual(item["original_filename"], "my-drawing.png")
        self.assertEqual(item["profile_id"], "piping_isometric")

    def test_invalid_request_envelope(self) -> None:
        response = self.client.post(
            "/api/v1/documents",
            data={"profile_id": "piping_isometric", "options_json": "{}"},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["code"], "invalid_request")
        self.assertIn("message", body)
        self.assertIn("request_id", body)
        self.assertEqual(response.headers.get("X-Request-Id"), body["request_id"])

    def test_internal_error_envelope(self) -> None:
        os.environ["ENABLE_API_TEST_HOOKS"] = "1"
        try:
            client = TestClient(create_app(), raise_server_exceptions=False)
            response = client.get(
                "/api/v1/__test__/internal-error", headers=self._headers()
            )
            self.assertEqual(response.status_code, 500)
            body = response.json()
            self.assertEqual(body["code"], "internal_error")
            self.assertIn("request_id", body)
            self.assertEqual(response.headers.get("X-Request-Id"), body["request_id"])
        finally:
            os.environ.pop("ENABLE_API_TEST_HOOKS", None)

    def test_concurrent_same_key_upload_not_500(self) -> None:
        owner = f"race-{uuid.uuid4()}"
        key = f"race-key-{uuid.uuid4()}"
        results: list[int] = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                response = self._upload(owner=owner, key=key)
                results.append(response.status_code)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        for status in results:
            self.assertIn(status, (202, 409))

    def test_unique_violation_simulation_returns_202_or_409(self) -> None:
        owner = f"uv-{uuid.uuid4()}"
        key = f"uv-key-{uuid.uuid4()}"
        first = self._upload(owner=owner, key=key)
        self.assertEqual(first.status_code, 202)

        from psycopg.errors import UniqueViolation

        call_count = 0
        real_create = __import__(
            "isometric_persistence.repositories.documents",
            fromlist=["DocumentRepository"],
        ).DocumentRepository.create

        def flaky_create(self, conn, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise UniqueViolation("duplicate key")
            return real_create(self, conn, **kwargs)

        with patch(
            "isometric_api.routes.DocumentRepository.create",
            flaky_create,
        ):
            second = self._upload(owner=owner, key=key)
        self.assertIn(second.status_code, (202, 409))
        self.assertNotEqual(second.status_code, 500)

    def test_display_exif_transpose_png_dimensions(self) -> None:
        owner = f"display-{uuid.uuid4()}"
        jpeg, expected_size = exif_rotated_jpeg()
        created = self.client.post(
            "/api/v1/documents",
            files={"file": ("rotated.jpg", jpeg, "image/jpeg")},
            data={"profile_id": "piping_isometric", "options_json": "{}"},
            headers=self._headers(owner),
        )
        self.assertEqual(created.status_code, 202)
        document_id = created.json()["document_id"]
        display = self.client.get(
            f"/api/v1/documents/{document_id}/display",
            headers=self._headers(owner),
        )
        self.assertEqual(display.status_code, 200)
        self.assertTrue(display.content.startswith(b"\x89PNG"))
        with Image.open(io.BytesIO(display.content)) as png:
            self.assertEqual(png.size, expected_size)

    def test_job_updated_at_and_review_item_count(self) -> None:
        owner = f"job-meta-{uuid.uuid4()}"
        created = self._upload(owner=owner)
        job_id = created.json()["job_id"]
        job = self.client.get(f"/api/v1/jobs/{job_id}", headers=self._headers(owner))
        self.assertEqual(job.status_code, 200)
        body = job.json()
        self.assertEqual(body["state"], "succeeded")
        self.assertIsNotNone(body.get("updated_at"))
        self.assertIn("T", body["updated_at"])
        self.assertIn("review_item_count", body)
        self.assertIsInstance(body["review_item_count"], int)
        self.assertGreaterEqual(body["review_item_count"], 0)


if __name__ == "__main__":
    unittest.main()
