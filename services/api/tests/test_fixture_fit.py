"""W1B fixture scene fit: EXIF frames, scaled geometry, and review items."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from isometric_api.app import create_app
from isometric_persistence.config import DatabaseSettings
from isometric_persistence.db import DatabasePool
from isometric_persistence.migrate import apply_migrations
from isometric_persistence.repositories.revisions import RevisionRepository
from isometric_pipeline.render import SYMBOL_LIBRARY_VERSION, load_symbol_library
from isometric_pipeline.scene import load_scene
from isometric_worker import processor
from isometric_worker.fixture_fit import (
    orientation_matrices,
    read_source_frame,
    severity_for_score,
)
from isometric_worker.processor import FIXTURE_SCENE, process_job, revision_id_for_job
from PIL import ExifTags, Image, ImageOps

IDENTITY = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
FIXTURE = json.loads(FIXTURE_SCENE.read_text(encoding="utf-8"))
MACHINE_OBJECT_IDS = sorted(
    obj["id"]
    for obj in FIXTURE["objects"]
    if obj["interpretation"]["state"] == "machine"
)


def encode(size: tuple[int, int], fmt: str, orientation: int | None = None) -> bytes:
    image = Image.new("RGB", size, color="white")
    buf = io.BytesIO()
    if orientation is None:
        image.save(buf, format=fmt)
    else:
        exif = Image.Exif()
        exif[ExifTags.Base.Orientation] = orientation
        image.save(buf, format=fmt, exif=exif.tobytes())
    return buf.getvalue()


def apply(matrix: list[float], x: float, y: float) -> tuple[float, float]:
    w = matrix[6] * x + matrix[7] * y + matrix[8]
    return (
        (matrix[0] * x + matrix[1] * y + matrix[2]) / w,
        (matrix[3] * x + matrix[4] * y + matrix[5]) / w,
    )


class OrientationMatrixTest(unittest.TestCase):
    def test_every_orientation_matches_exif_transpose_pixels(self) -> None:
        width, height = 40, 20
        for orientation in range(1, 9):
            with self.subTest(orientation=orientation):
                image = Image.new("RGB", (width, height), color="white")
                image.paste((255, 0, 0), (4, 2, 10, 6))
                exif = Image.Exif()
                exif[ExifTags.Base.Orientation] = orientation
                buf = io.BytesIO()
                image.save(buf, format="PNG", exif=exif.tobytes())
                data = buf.getvalue()

                frame = read_source_frame(data)
                with Image.open(io.BytesIO(data)) as opened:
                    display = ImageOps.exif_transpose(opened)
                assert display is not None
                self.assertEqual(frame.orientation, orientation)
                self.assertEqual(
                    (frame.source_width_px, frame.source_height_px), (40, 20)
                )
                self.assertEqual(
                    (frame.display_width_px, frame.display_height_px), display.size
                )
                dx, dy = apply(frame.source_to_display, 7.0, 4.0)
                self.assertEqual(display.getpixel((int(dx), int(dy))), (255, 0, 0))
                sx, sy = apply(frame.display_to_source, dx, dy)
                self.assertAlmostEqual(sx, 7.0)
                self.assertAlmostEqual(sy, 4.0)

    def test_orientation_six_is_ninety_degrees_clockwise(self) -> None:
        forward, inverse = orientation_matrices(6, 48, 32)
        self.assertEqual(forward, [0.0, -1.0, 32.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0])
        self.assertEqual(inverse, [0.0, 1.0, 0.0, -1.0, 0.0, 32.0, 0.0, 0.0, 1.0])

    def test_unknown_orientation_is_identity(self) -> None:
        self.assertEqual(orientation_matrices(0, 10, 20), (IDENTITY, IDENTITY))
        self.assertEqual(orientation_matrices(9, 10, 20), (IDENTITY, IDENTITY))

    def test_severity_thresholds(self) -> None:
        self.assertEqual(severity_for_score(0.49), "high")
        self.assertEqual(severity_for_score(0.5), "medium")
        self.assertEqual(severity_for_score(0.89), "medium")
        self.assertEqual(severity_for_score(0.9), "low")
        self.assertEqual(severity_for_score(None), "high")


def require_database() -> str:
    url = os.environ.get("LOCAL_DATABASE_URL")
    if not url:
        raise unittest.SkipTest("LOCAL_DATABASE_URL is not set")
    return url


class FixtureFitIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db_url = require_database()
        cls.artifact_root = Path(tempfile.mkdtemp(prefix="isometric-fit-artifacts-"))
        os.environ["ARTIFACT_ROOT"] = str(cls.artifact_root)
        os.environ["LOCAL_DATABASE_URL"] = cls.db_url
        pool = DatabasePool(DatabaseSettings(url=cls.db_url))
        with pool.connection() as conn:
            apply_migrations(conn)
            conn.commit()
        pool.close()
        cls.app = create_app()
        cls.client = TestClient(cls.app)
        cls.catalog = load_symbol_library(SYMBOL_LIBRARY_VERSION)

    def setUp(self) -> None:
        os.environ["SKIP_INLINE_WORKER"] = "1"
        self.addCleanup(os.environ.pop, "SKIP_INLINE_WORKER", None)
        self.owner = f"fit-{uuid.uuid4()}"
        self.pool = DatabasePool(DatabaseSettings(url=self.db_url))
        self.addCleanup(self.pool.close)

    def _headers(self) -> dict[str, str]:
        return {"X-Owner-Id": self.owner}

    def _upload(
        self, data: bytes, filename: str, mime: str
    ) -> tuple[uuid.UUID, uuid.UUID]:
        response = self.client.post(
            "/api/v1/documents",
            files={"file": (filename, data, mime)},
            data={"profile_id": "piping_isometric", "options_json": "{}"},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 202, response.text)
        body = response.json()
        return uuid.UUID(body["document_id"]), uuid.UUID(body["job_id"])

    def _process(self, data: bytes, filename: str, mime: str) -> dict[str, Any]:
        document_id, job_id = self._upload(data, filename, mime)
        process_job(self.pool, self.app.state.runtime.store, job_id)
        job = self.client.get(f"/api/v1/jobs/{job_id}", headers=self._headers()).json()
        self.assertEqual(job["state"], "succeeded", job)
        revision_id = job["result_revision_id"]
        self.assertEqual(revision_id, str(revision_id_for_job(job_id)))
        scene = self.client.get(
            f"/api/v1/documents/{document_id}/revisions/{revision_id}/scene",
            headers=self._headers(),
        )
        self.assertEqual(scene.status_code, 200)
        load_scene(scene.text, catalog=self.catalog)
        return json.loads(scene.text)

    def _assert_scaled(self, scene: dict[str, Any]) -> None:
        page = scene["page"]
        sx = page["widthPx"] / FIXTURE["page"]["widthPx"]
        sy = page["heightPx"] / FIXTURE["page"]["heightPx"]
        fixture_objects = {obj["id"]: obj for obj in FIXTURE["objects"]}
        for obj in scene["objects"]:
            original = fixture_objects[obj["id"]]
            if obj["type"] == "junction":
                self.assertAlmostEqual(
                    obj["position"]["x"], original["position"]["x"] * sx, places=5
                )
                self.assertAlmostEqual(
                    obj["position"]["y"], original["position"]["y"] * sy, places=5
                )
            if obj["type"] == "annotation":
                self.assertAlmostEqual(
                    obj["anchor"]["x"], original["anchor"]["x"] * sx, places=5
                )
                self.assertAlmostEqual(
                    obj["anchor"]["y"], original["anchor"]["y"] * sy, places=5
                )
            polygon = obj["interpretation"]["evidence"][0]["sourcePolygon"]
            fixture_polygon = original["interpretation"]["evidence"][0]["sourcePolygon"]
            for point, fixture_point in zip(polygon, fixture_polygon, strict=True):
                self.assertLessEqual(0, point["x"])
                self.assertLessEqual(point["x"], page["sourceWidthPx"])
                self.assertLessEqual(0, point["y"])
                self.assertLessEqual(point["y"], page["sourceHeightPx"])
                px, py = apply(page["sourceToDisplay"], point["x"], point["y"])
                self.assertAlmostEqual(px, fixture_point["x"] * sx, places=5)
                self.assertAlmostEqual(py, fixture_point["y"] * sy, places=5)

    def test_identity_png(self) -> None:
        scene = self._process(encode((40, 40), "PNG"), "page.png", "image/png")
        page = scene["page"]
        self.assertEqual(
            (
                page["sourceWidthPx"],
                page["sourceHeightPx"],
                page["displayWidthPx"],
                page["displayHeightPx"],
                page["widthPx"],
                page["heightPx"],
            ),
            (40, 40, 40, 40, 40, 40),
        )
        for key in (
            "sourceToDisplay",
            "displayToSource",
            "sourceToPage",
            "pageToSource",
        ):
            self.assertEqual(page[key], IDENTITY)
        self._assert_scaled(scene)

    def test_exif_orientation_six_jpeg(self) -> None:
        data = encode((48, 32), "JPEG", orientation=6)
        scene = self._process(data, "rotated.jpg", "image/jpeg")
        page = scene["page"]
        self.assertEqual((page["sourceWidthPx"], page["sourceHeightPx"]), (48, 32))
        self.assertEqual((page["displayWidthPx"], page["displayHeightPx"]), (32, 48))
        self.assertEqual((page["widthPx"], page["heightPx"]), (32, 48))
        self.assertNotEqual(page["sourceToDisplay"], IDENTITY)
        self.assertEqual(
            page["sourceToDisplay"], [0.0, -1.0, 32.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        )
        self.assertEqual(
            page["displayToSource"], [0.0, 1.0, 0.0, -1.0, 0.0, 32.0, 0.0, 0.0, 1.0]
        )
        self.assertEqual(page["sourceToPage"], page["sourceToDisplay"])
        self.assertEqual(page["pageToSource"], page["displayToSource"])
        self._assert_scaled(scene)

    def test_non_square_jpeg(self) -> None:
        scene = self._process(encode((64, 24), "JPEG"), "wide.jpg", "image/jpeg")
        page = scene["page"]
        self.assertEqual((page["sourceWidthPx"], page["sourceHeightPx"]), (64, 24))
        self.assertEqual((page["displayWidthPx"], page["displayHeightPx"]), (64, 24))
        self.assertEqual((page["widthPx"], page["heightPx"]), (64, 24))
        self.assertEqual(page["sourceToPage"], IDENTITY)
        self._assert_scaled(scene)
        junction = next(o for o in scene["objects"] if o["type"] == "junction")
        self.assertAlmostEqual(junction["position"]["x"], 40.0 * 64 / 200)
        self.assertAlmostEqual(junction["position"]["y"], 120.0 * 24 / 200)

    def _assert_one_revision_with_items(self, document_id: uuid.UUID) -> None:
        revs = RevisionRepository()
        with self.pool.connection() as conn:
            rows = revs.list_for_document(conn, document_id)
            self.assertEqual(len(rows), 1)
            items = revs.list_review_items(conn, rows[0]["id"])
        self.assertEqual(len(items), len(MACHINE_OBJECT_IDS))
        self.assertEqual(sorted(i["object_id"] for i in items), MACHINE_OBJECT_IDS)
        self.assertEqual(len({i["issue_key"] for i in items}), len(items))
        for item in items:
            self.assertEqual(item["issue_type"], "fixture_low_confidence")
            self.assertEqual(item["severity"], "medium")
            self.assertEqual(item["state"], "open")
            self.assertEqual(
                item["issue_key"], f"fixture_low_confidence:{item['object_id']}"
            )

    def test_duplicate_delivery_yields_one_revision_and_review_items(self) -> None:
        document_id, job_id = self._upload(
            encode((40, 40), "PNG"), "page.png", "image/png"
        )
        store = self.app.state.runtime.store
        process_job(self.pool, store, job_id)
        process_job(self.pool, store, job_id)
        self._assert_one_revision_with_items(document_id)

    def test_republish_race_rolls_back_duplicate_review_items(self) -> None:
        document_id, job_id = self._upload(
            encode((40, 40), "PNG"), "page.png", "image/png"
        )
        store = self.app.state.runtime.store
        process_job(self.pool, store, job_id)
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
        real = processor._complete_if_revision_exists
        calls = {"n": 0}

        def miss_first_check(*args: Any, **kwargs: Any) -> bool:
            calls["n"] += 1
            if calls["n"] == 1:
                return False
            return real(*args, **kwargs)

        with patch.object(processor, "_complete_if_revision_exists", miss_first_check):
            process_job(self.pool, store, job_id)
        self.assertEqual(calls["n"], 2)
        job = self.client.get(f"/api/v1/jobs/{job_id}", headers=self._headers()).json()
        self.assertEqual(job["state"], "succeeded")
        self.assertEqual(job["result_revision_id"], str(revision_id_for_job(job_id)))
        self._assert_one_revision_with_items(document_id)


if __name__ == "__main__":
    unittest.main()
