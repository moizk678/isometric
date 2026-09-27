"""Tests for infer_topology stage."""

from __future__ import annotations

import io
import unittest
import uuid
from pathlib import Path

import numpy as np
from isometric_pipeline.masks.util import encode_mask_png
from isometric_pipeline.primitives.artifact import (
    PagePoint,
    PrimitiveCandidate,
    PrimitivesMetadata,
)
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.snapping.artifact import (
    PagePoint as SnapPoint,
)
from isometric_pipeline.snapping.artifact import (
    SegmentGeom,
    SnappedPrimitiveCandidate,
    SnappedPrimitivesMetadata,
)
from isometric_pipeline.topology.artifact import (
    EdgeCandidate,
    NodeCandidate,
    TopologyMetadata,
)
from isometric_pipeline.topology.artifact import (
    PagePoint as TopoPoint,
)
from isometric_pipeline.topology.stage import infer_topology
from isometric_pipeline.topology.validate import validate_topology
from PIL import Image

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "topology"
DOC_ID = "00000000-0000-4000-8000-000000000200"


def _ensure_fixtures() -> None:
    if not (FIXTURES / "disconnected-crossing.png").is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "topology_generate", FIXTURES / "generate.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate_all()


def _blank_page(width: int = 256, height: int = 256) -> bytes:
    rgb = np.full((height, width, 3), 255, dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(rgb, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


def _line_primitive(
    prim_id: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    layer_id: str = "geometry",
    component_id: str = "cmp_0",
) -> PrimitiveCandidate:
    return PrimitiveCandidate(
        id=prim_id,
        layer_id=layer_id,
        kind="line",
        start=PagePoint(x=x0, y=y0),
        end=PagePoint(x=x1, y=y1),
        samples=[(x0, y0), (x1, y1)],
        residual_rms_px=0.5,
        stroke_width_px=5.0,
        fit_metric=0.99,
        confidence=0.95,
        status="accepted",
        centerline_edge_id=f"edge_{prim_id}",
        component_id=component_id,
        mask_uri="masks/geometry",
        evidence="test",
    )


def _snapped_line(
    prim: PrimitiveCandidate,
) -> SnappedPrimitiveCandidate:
    geom = SegmentGeom(
        start=SnapPoint(x=prim.start.x, y=prim.start.y),
        end=SnapPoint(x=prim.end.x, y=prim.end.y),
    )
    return SnappedPrimitiveCandidate(
        primitive_id=prim.id,
        layer_id=prim.layer_id,
        status="preserved",
        pre_snap=geom,
        post_snap=geom,
        axis_id=None,
        angle_delta_deg=0.0,
        max_endpoint_displacement_px=0.0,
        residual_rms_px=prim.residual_rms_px,
        decision_reason="preserved_uncertain",
        reason="test",
        evidence="test",
    )


def _run_infer(
    primitives: list[PrimitiveCandidate],
    *,
    layer_masks: dict[str, bytes] | None = None,
    width: int = 256,
    height: int = 256,
) -> TopologyMetadata:
    doc = str(uuid.UUID(DOC_ID))
    prim_meta = PrimitivesMetadata(
        profile_version=DEFAULT_PIPING_PROFILE_VERSION,
        page_width_px=width,
        page_height_px=height,
        centerlines_metadata_uri=f"documents/{doc}/centerlines.json",
        masks_metadata_uri=f"documents/{doc}/masks.json",
        primitives=primitives,
    )
    snapped_meta = SnappedPrimitivesMetadata(
        profile_version=DEFAULT_PIPING_PROFILE_VERSION,
        page_width_px=width,
        page_height_px=height,
        primitives_metadata_uri=f"documents/{doc}/primitives.json",
        axes_metadata_uri=f"documents/{doc}/axes.json",
        candidates=[_snapped_line(p) for p in primitives],
    )
    result = infer_topology(
        _blank_page(width, height),
        snapped_meta,
        prim_meta,
        snapped_primitives_json_uri=f"documents/{doc}/snapped-primitives.json",
        primitives_json_uri=f"documents/{doc}/primitives.json",
        topology_json_uri=f"documents/{doc}/topology.json",
        layer_masks=layer_masks,
    )
    return result.metadata


class TopologyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_fixtures()

    def test_profile_topology_section_loads(self) -> None:
        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
        self.assertGreater(profile.topology.endpoint_cluster_tolerance_px, 0.0)

    def test_validate_rejects_dangling_node_reference(self) -> None:
        meta = TopologyMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=100,
            page_height_px=100,
            snapped_primitives_metadata_uri="a",
            primitives_metadata_uri="b",
            nodes=[
                NodeCandidate(
                    id="n1",
                    position=TopoPoint(x=0, y=0),
                    kind="endpoint",
                    status="proposed",
                    source_evidence="test",
                )
            ],
            edges=[
                EdgeCandidate(
                    id="e1",
                    start_node_id="n1",
                    end_node_id="missing",
                    layer_id="geometry",
                    start=TopoPoint(x=0, y=0),
                    end=TopoPoint(x=10, y=0),
                )
            ],
        )
        errors = validate_topology(meta)
        self.assertTrue(any("missing end node" in err for err in errors))

    def test_disconnected_crossing_keeps_four_endpoints(self) -> None:
        prims = [
            _line_primitive("h", 24, 128, 232, 128),
            _line_primitive("v", 128, 24, 128, 232),
        ]
        meta = _run_infer(prims)
        self.assertEqual(len(meta.nodes), 4)
        self.assertGreaterEqual(len(meta.hypotheses), 1)
        node_positions = {
            (round(n.position.x), round(n.position.y)) for n in meta.nodes
        }
        self.assertNotIn((128, 128), node_positions)
        for hyp in meta.hypotheses:
            crossing = next(a for a in hyp.alternatives if a.label == "crossing")
            self.assertGreater(crossing.score, 0.0)

    def test_true_tee_has_tee_node(self) -> None:
        prims = [
            _line_primitive("stem_top", 128, 40, 128, 128),
            _line_primitive("stem_bottom", 128, 128, 128, 216),
            _line_primitive("branch", 128, 128, 220, 128),
        ]
        meta = _run_infer(prims)
        kinds = {n.kind for n in meta.nodes}
        self.assertIn("tee", kinds)
        self.assertGreaterEqual(len(meta.edges), 2)

    def test_edge_endpoints_match_clustered_node_positions(self) -> None:
        prims = [
            _line_primitive("stem_top", 128, 40, 128, 127),
            _line_primitive("stem_bottom", 128, 129, 128, 216),
            _line_primitive("branch", 129, 128, 220, 128),
        ]
        meta = _run_infer(prims)
        nodes_by_id = {node.id: node for node in meta.nodes}
        for edge in meta.edges:
            start = nodes_by_id[edge.start_node_id].position
            end = nodes_by_id[edge.end_node_id].position
            self.assertAlmostEqual(edge.start.x, start.x, places=6)
            self.assertAlmostEqual(edge.start.y, start.y, places=6)
            self.assertAlmostEqual(edge.end.x, end.x, places=6)
            self.assertAlmostEqual(edge.end.y, end.y, places=6)

    def test_elbow_corner(self) -> None:
        prims = [
            _line_primitive("a", 60, 180, 60, 100),
            _line_primitive("b", 60, 100, 180, 100),
        ]
        meta = _run_infer(prims)
        self.assertIn("elbow", {n.kind for n in meta.nodes})

    def test_near_miss_does_not_merge_endpoints(self) -> None:
        prims = [
            _line_primitive("left", 40, 128, 110, 128),
            _line_primitive("right", 122, 128, 216, 128),
        ]
        meta = _run_infer(prims)
        self.assertGreaterEqual(len(meta.nodes), 4)
        codes = {item.code for item in meta.review_items}
        self.assertIn("topology.near_miss_endpoints", codes)

    def test_elbow_preserved_after_collinear_merge(self) -> None:
        # Two collinear vertical fragments merge; horizontal leg stays a separate edge.
        prims = [
            _line_primitive("v_top", 60, 180, 60, 130),
            _line_primitive("v_bottom", 60, 120, 60, 100),
            _line_primitive("h", 60, 100, 180, 100),
        ]
        mask = np.zeros((256, 256), dtype=np.uint8)
        mask[126:131, 60:121] = 255
        meta = _run_infer(prims, layer_masks={"geometry": encode_mask_png(mask)})
        merged = [e for e in meta.edges if len(e.source_primitive_ids) >= 2]
        self.assertTrue(merged, "expected collinear vertical merge")
        kinds = {n.kind for n in meta.nodes}
        self.assertIn("elbow", kinds)

    def test_collinear_gap_merge(self) -> None:
        prims = [
            _line_primitive("a", 40, 128, 110, 128),
            _line_primitive("b", 120, 128, 216, 128),
        ]
        mask = np.zeros((256, 256), dtype=np.uint8)
        mask[126:131, 110:121] = 255
        meta = _run_infer(prims, layer_masks={"geometry": encode_mask_png(mask)})
        merged_edges = [e for e in meta.edges if len(e.source_primitive_ids) >= 2]
        self.assertTrue(merged_edges or len(meta.edges) == 1)

    def test_different_color_crossing(self) -> None:
        prims = [
            _line_primitive("red", 30, 128, 226, 128, layer_id="color_0"),
            _line_primitive("blue", 128, 30, 128, 226, layer_id="color_1"),
        ]
        meta = _run_infer(prims)
        self.assertGreaterEqual(len(meta.hypotheses), 1)
        hyp = meta.hypotheses[0]
        crossing = next(a for a in hyp.alternatives if a.label == "crossing")
        tee = next(a for a in hyp.alternatives if a.label == "tee")
        self.assertGreater(crossing.score, tee.score)

    def test_infer_topology_content_hash_stable(self) -> None:
        prims = [
            _line_primitive("a", 60, 180, 60, 100),
            _line_primitive("b", 60, 100, 180, 100),
        ]
        doc = str(uuid.UUID(DOC_ID))
        prim_meta = PrimitivesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=256,
            page_height_px=256,
            centerlines_metadata_uri=f"documents/{doc}/centerlines.json",
            masks_metadata_uri=f"documents/{doc}/masks.json",
            primitives=prims,
        )
        snapped_meta = SnappedPrimitivesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=256,
            page_height_px=256,
            primitives_metadata_uri=f"documents/{doc}/primitives.json",
            axes_metadata_uri=f"documents/{doc}/axes.json",
            candidates=[_snapped_line(p) for p in prims],
        )
        page = _blank_page()
        r1 = infer_topology(
            page,
            snapped_meta,
            prim_meta,
            snapped_primitives_json_uri="s",
            primitives_json_uri="p",
            topology_json_uri="t",
        )
        r2 = infer_topology(
            page,
            snapped_meta,
            prim_meta,
            snapped_primitives_json_uri="s",
            primitives_json_uri="p",
            topology_json_uri="t",
        )
        self.assertEqual(r1.content_hash, r2.content_hash)


if __name__ == "__main__":
    unittest.main()
