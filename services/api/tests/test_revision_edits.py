"""Run 15 revision edit and resolve API tests."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from isometric_api.app import create_app
from isometric_persistence.config import DatabaseSettings, resolve_database_url
from isometric_persistence.db import DatabasePool
from isometric_persistence.migrate import apply_migrations
from isometric_persistence.repositories.revisions import RevisionRepository
from isometric_worker.processor import FIXTURE_SCENE, process_job
from test_upload_jobs import require_database, tiny_png


def _annotation_id() -> str:
    fixture = json.loads(FIXTURE_SCENE.read_text(encoding="utf-8"))
    for obj in fixture["objects"]:
        if obj["type"] == "annotation":
            return obj["id"]
    raise AssertionError("fixture has no annotation")


class RevisionEditsIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db_url = require_database()
        cls.artifact_root = Path(tempfile.mkdtemp(prefix="isometric-revision-edits-"))
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

    def _headers(self, owner: str = "owner-edits") -> dict[str, str]:
        return {"X-Owner-Id": owner}

    def _upload_and_get_revision(self, owner: str) -> tuple[str, str]:
        files = {"file": ("page.png", tiny_png(), "image/png")}
        response = self.client.post(
            "/api/v1/documents",
            files=files,
            data={"profile_id": "piping_isometric", "options_json": "{}"},
            headers=self._headers(owner),
        )
        self.assertEqual(response.status_code, 202)
        document_id = response.json()["document_id"]
        job_id = response.json()["job_id"]
        process_job(
            self.pool,
            self.client.app.state.runtime.store,
            uuid.UUID(job_id),
        )
        detail = self.client.get(
            f"/api/v1/documents/{document_id}",
            headers=self._headers(owner),
        ).json()
        revision_id = detail["current_revision_id"]
        assert revision_id is not None
        return document_id, revision_id

    def test_edits_require_if_match(self) -> None:
        document_id, revision_id = self._upload_and_get_revision(f"if-match-{uuid.uuid4()}")
        ann_id = _annotation_id()
        response = self.client.post(
            f"/api/v1/documents/{document_id}/revisions/{revision_id}/edits",
            headers=self._headers(),
            json={
                "commands": [
                    {
                        "type": "update_annotation_text",
                        "objectId": ann_id,
                        "normalizedText": "edited",
                    }
                ]
            },
        )
        self.assertEqual(response.status_code, 428)

    def test_annotation_edit_creates_new_revision(self) -> None:
        owner = f"edit-{uuid.uuid4()}"
        document_id, revision_id = self._upload_and_get_revision(owner)
        ann_id = _annotation_id()
        response = self.client.post(
            f"/api/v1/documents/{document_id}/revisions/{revision_id}/edits",
            headers={**self._headers(owner), "If-Match": revision_id},
            json={
                "commands": [
                    {
                        "type": "update_annotation_text",
                        "objectId": ann_id,
                        "normalizedText": "edited label",
                    }
                ]
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotEqual(body["revision_id"], revision_id)
        detail = self.client.get(
            f"/api/v1/documents/{document_id}",
            headers=self._headers(owner),
        ).json()
        self.assertEqual(detail["current_revision_id"], body["revision_id"])
        scene = self.client.get(
            f"/api/v1/documents/{document_id}/revisions/{body['revision_id']}/scene",
            headers=self._headers(owner),
        ).json()
        ann = next(obj for obj in scene["objects"] if obj["id"] == ann_id)
        self.assertEqual(ann["normalizedText"], "edited label")
        self.assertEqual(ann["interpretation"]["state"], "confirmed")

    def test_stale_if_match_returns_409(self) -> None:
        owner = f"stale-{uuid.uuid4()}"
        document_id, revision_id = self._upload_and_get_revision(owner)
        ann_id = _annotation_id()
        headers = {**self._headers(owner), "If-Match": revision_id}
        first = self.client.post(
            f"/api/v1/documents/{document_id}/revisions/{revision_id}/edits",
            headers=headers,
            json={
                "commands": [
                    {
                        "type": "update_annotation_text",
                        "objectId": ann_id,
                        "normalizedText": "first",
                    }
                ]
            },
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            f"/api/v1/documents/{document_id}/revisions/{revision_id}/edits",
            headers=headers,
            json={
                "commands": [
                    {
                        "type": "update_annotation_text",
                        "objectId": ann_id,
                        "normalizedText": "second",
                    }
                ]
            },
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "revision_conflict")


if __name__ == "__main__":
    unittest.main()
