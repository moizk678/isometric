"""Tests for snap_primitives stage."""

from __future__ import annotations

import io
import math
import os
import unittest
import uuid
from pathlib import Path

import numpy as np
from isometric_pipeline.centerlines.stage import extract_centerlines
from isometric_pipeline.masks.util import encode_mask_png
from isometric_pipeline.primitives.artifact import PrimitivesMetadata
from isometric_pipeline.primitives.stage import fit_primitives
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.artifact import PageBBox, RegionCandidate
from isometric_pipeline.snapping.artifact import PagePoint, SegmentGeom
from isometric_pipeline.snapping.axes import (
    infer_axis_model,
    nearest_axis_angle,
    triad_angles_deg,
    undirected_angle_deg,
)
from isometric_pipeline.snapping.snap import _snap_segment_to_angle
from isometric_pipeline.snapping.stage import snap_primitives
from PIL import Image
from test_centerlines_and_primitives import DOC_ID, _masks_metadata, _page_from_mask

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "axis-snapping"
CENTERLINE_FIXTURES = (
    Path(__file__).resolve().parent / "fixtures" / "centerlines-and-primitives"
)


def _ensure_fixtures() -> None:
    if not (FIXTURES / "rotated-isometric-triad.png").is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "axis_snapping_generate", FIXTURES / "generate.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate_all()


def _decode_mask(png: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(png)) as image:
        return np.array(image.convert("L"))


def _run_fit_pipeline(mask_name: str, fixture_dir: Path = FIXTURES):
    mask = _decode_mask((fixture_dir / mask_name).read_bytes())
    page = _page_from_mask(mask)
    doc = str(uuid.UUID(DOC_ID))
    h, w = mask.shape
    geometry_png = encode_mask_png(mask)
    meta = _masks_metadata(doc, w, h)
    extracted = extract_centerlines(
        page,
        geometry_png,
        {},
        meta,
        None,
        document_id=doc,
        masks_json_uri=f"documents/{doc}/masks.json",
        regions_json_uri=None,
        centerlines_json_uri=f"documents/{doc}/centerlines.json",
    )
    fitted = fit_primitives(
        page,
        extracted.metadata,
        {"geometry": geometry_png},
        centerlines_json_uri=f"documents/{doc}/centerlines.json",
        masks_json_uri=f"documents/{doc}/masks.json",
        regions_json_uri=None,
        primitives_json_uri=f"documents/{doc}/primitives.json",
    )
    return page, fitted.metadata


def _blank_page(width: int = 400, height: int = 400) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(
        np.full((height, width, 3), 255, dtype=np.uint8), mode="RGB"
    ).save(buf, format="PNG")
    return buf.getvalue()


def _synthetic_rotated_primitives(rotation_deg: float = 15.0) -> PrimitivesMetadata:
    from isometric_pipeline.primitives.artifact import PagePoint, PrimitiveCandidate

    cx, cy = 200.0, 200.0
    length = 200.0
    prims: list[PrimitiveCandidate] = []
    for i, ang in enumerate(triad_angles_deg(rotation_deg)):
        rad = math.radians(ang)
        dx = math.cos(rad) * length / 2.0
        dy = math.sin(rad) * length / 2.0
        start = PagePoint(x=cx - dx, y=cy - dy)
        end = PagePoint(x=cx + dx, y=cy + dy)
        prims.append(
            PrimitiveCandidate(
                id=f"prim_{i:04d}",
                layer_id="geometry",
                kind="line",
                start=start,
                end=end,
                samples=[(start.x, start.y), (end.x, end.y)],
                residual_rms_px=0.4,
                stroke_width_px=5.0,
                fit_metric=0.98,
                confidence=0.95,
                status="accepted",
                centerline_edge_id=f"edge_{i}",
                component_id=f"comp_{i}",
                mask_uri="",
                evidence="synthetic",
            )
        )
    return PrimitivesMetadata(
        profile_version=DEFAULT_PIPING_PROFILE_VERSION,
        page_width_px=400,
        page_height_px=400,
        centerlines_metadata_uri="c",
        masks_metadata_uri="m",
        primitives=prims,
    )


def _snap_from_fitted(page: bytes, primitives: PrimitivesMetadata, **kwargs):
    doc = str(uuid.UUID(DOC_ID))
    return snap_primitives(
        page,
        primitives,
        primitives_json_uri=f"documents/{doc}/primitives.json",
        axes_json_uri=f"documents/{doc}/axes.json",
        snapped_primitives_json_uri=f"documents/{doc}/snapped-primitives.json",
        masks_json_uri=f"documents/{doc}/masks.json",
        **kwargs,
    )


class AxisSnappingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_fixtures()

    def test_profile_snapping_section_loads(self) -> None:
        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
        self.assertGreater(profile.snapping.max_snap_angle_deg, 0.0)

    def test_triad_rotation_score_is_deterministic(self) -> None:
        votes = [(30.0, 100.0), (90.0, 120.0), (150.0, 90.0)]
        from isometric_pipeline.primitives.artifact import (
            PagePoint,
            PrimitiveCandidate,
        )

        prims = []
        for i, (ang, length) in enumerate(votes):
            rad = math.radians(ang)
            prims.append(
                PrimitiveCandidate(
                    id=f"p{i}",
                    layer_id="geometry",
                    kind="line",
                    start=PagePoint(x=0.0, y=0.0),
                    end=PagePoint(
                        x=length * math.cos(rad),
                        y=length * math.sin(rad),
                    ),
                    samples=[(0.0, 0.0), (length * math.cos(rad), length * math.sin(rad))],
                    residual_rms_px=0.5,
                    stroke_width_px=4.0,
                    fit_metric=0.99,
                    confidence=0.95,
                    status="accepted",
                    centerline_edge_id=f"e{i}",
                    component_id=f"c{i}",
                    mask_uri="",
                    evidence="test",
                )
            )
        model = infer_axis_model(
            prims,
            load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION).snapping,
        )
        self.assertGreater(model.model_confidence, 0.3)
        self.assertEqual(len(model.axes), 3)

    def test_nearest_axis_angle_within_tolerance(self) -> None:
        _, dist = nearest_axis_angle(32.0, 0.0)
        self.assertLess(dist, 5.0)

    def test_rotated_isometric_triad_snaps(self) -> None:
        page = _blank_page()
        primitives = _synthetic_rotated_primitives(15.0)
        result = _snap_from_fitted(page, primitives)
        self.assertGreater(result.axes_metadata.model_confidence, 0.25)
        snapped = [c for c in result.snapped_metadata.candidates if c.status == "snapped"]
        self.assertGreaterEqual(len(snapped), 2)
        for cand in snapped:
            ang = undirected_angle_deg(
                cand.post_snap.end.x - cand.post_snap.start.x,
                cand.post_snap.end.y - cand.post_snap.start.y,
            )
            _, dist = nearest_axis_angle(ang, result.axes_metadata.rotation_deg)
            self.assertLess(dist, 5.0)

    def test_off_axis_line_preserved(self) -> None:
        page, primitives = _run_fit_pipeline("off-axis-45.png")
        result = _snap_from_fitted(page, primitives)
        off_axis = [
            c
            for c in result.snapped_metadata.candidates
            if c.decision_reason == "off_axis"
        ]
        self.assertGreaterEqual(len(off_axis), 1)

    def test_weak_evidence_preserves(self) -> None:
        page, primitives = _run_fit_pipeline("weak-evidence.png")
        result = _snap_from_fitted(page, primitives)
        self.assertTrue(
            result.axes_metadata.model_confidence
            < load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION).snapping.min_axis_model_confidence
            or all(c.status != "snapped" for c in result.snapped_metadata.candidates)
        )

    def test_dimension_region_skips_snap(self) -> None:
        page, primitives = _run_fit_pipeline(
            "horizontal-stroke.png", fixture_dir=CENTERLINE_FIXTURES
        )
        prim = next(p for p in primitives.primitives if p.status == "accepted")
        mx = (prim.start.x + prim.end.x) / 2.0
        my = (prim.start.y + prim.end.y) / 2.0
        from isometric_pipeline.regions.artifact import RegionsMetadata

        regions = RegionsMetadata(
            page_width_px=primitives.page_width_px,
            page_height_px=primitives.page_height_px,
            masks_metadata_uri="m",
            protection_mask_uri="p",
            geometry_ink_mask_uri="g",
            warnings=[],
            regions=[
                RegionCandidate(
                    id="dim_0",
                    kind="dimension",
                    bbox=PageBBox(x=mx - 40, y=my - 40, width=80, height=80),
                    score=0.9,
                    crop_uri="c",
                    evidence="test",
                )
            ],
        )
        result = _snap_from_fitted(page, primitives, regions=regions)
        dim_skipped = [
            c
            for c in result.snapped_metadata.candidates
            if c.decision_reason == "dimension_region"
        ]
        self.assertGreaterEqual(len(dim_skipped), 1)

    def test_snapped_candidates_trace_displacement(self) -> None:
        page, primitives = _run_fit_pipeline("noisy-stroke.png", CENTERLINE_FIXTURES)
        result = _snap_from_fitted(page, primitives)
        for cand in result.snapped_metadata.candidates:
            if cand.status != "snapped":
                continue
            self.assertGreaterEqual(cand.max_endpoint_displacement_px, 0.0)
            if cand.angle_delta_deg > 0.05:
                self.assertGreater(cand.max_endpoint_displacement_px, 0.0)

    def test_snap_uses_minimal_rotation_not_flip(self) -> None:
        seg = SegmentGeom(
            start=PagePoint(x=40.0, y=200.0),
            end=PagePoint(x=240.0, y=200.0),
        )
        snapped = _snap_segment_to_angle(seg, 30.0)
        dx = snapped.end.x - snapped.start.x
        self.assertGreater(dx, 0.0, "segment direction should not flip 180°")

    def test_endpoint_align_clusters_within_tolerance(self) -> None:
        from isometric_pipeline.snapping.align import align_snapped_endpoints
        from isometric_pipeline.snapping.artifact import SnappedPrimitiveCandidate

        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION).snapping
        base = SnappedPrimitiveCandidate(
            primitive_id="p0",
            layer_id="geometry",
            status="snapped",
            pre_snap=SegmentGeom(
                start=PagePoint(x=0.0, y=0.0), end=PagePoint(x=100.0, y=0.0)
            ),
            post_snap=SegmentGeom(
                start=PagePoint(x=100.0, y=0.0), end=PagePoint(x=200.0, y=0.0)
            ),
            axis_id="axis_vertical",
            angle_delta_deg=1.0,
            max_endpoint_displacement_px=1.0,
            residual_rms_px=0.5,
            decision_reason="snapped_to_axis",
            reason="test",
            evidence="test",
        )
        neighbor = base.model_copy(
            update={
                "primitive_id": "p1",
                "post_snap": SegmentGeom(
                    start=PagePoint(x=103.0, y=2.0),
                    end=PagePoint(x=103.0, y=102.0),
                ),
            }
        )
        aligned = align_snapped_endpoints([base, neighbor], profile)
        self.assertAlmostEqual(
            aligned[0].post_snap.start.x, aligned[1].post_snap.start.x, delta=0.5
        )

    def test_snap_stage_content_hash_stable(self) -> None:
        page = _blank_page()
        primitives = _synthetic_rotated_primitives(15.0)
        a = _snap_from_fitted(page, primitives)
        b = _snap_from_fitted(page, primitives)
        self.assertEqual(a.content_hash, b.content_hash)

    def test_tuning_report_optional(self) -> None:
        if os.environ.get("ISOMETRIC_TUNING_REPORT") != "1":
            return
        page, primitives = _run_fit_pipeline("rotated-isometric-triad.png")
        result = _snap_from_fitted(page, primitives)
        snapped = sum(1 for c in result.snapped_metadata.candidates if c.status == "snapped")
        total = len(result.snapped_metadata.candidates)
        print(f"tuning_report snapped={snapped}/{total}")


if __name__ == "__main__":
    unittest.main()
