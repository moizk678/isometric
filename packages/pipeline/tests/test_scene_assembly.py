"""Tests for scene assembly from pipeline artifacts."""

from __future__ import annotations

import io
import unittest
import uuid

import numpy as np
from isometric_pipeline.normalize.artifact import (
    NormalizeDiagnostics,
    NormalizePageMetadata,
    RasterArtifactRef,
)
from isometric_pipeline.primitives.artifact import PagePoint, PrimitiveCandidate
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
    resolve_piping_profile_version,
)
from isometric_pipeline.render import (
    STYLE_PROFILE_VERSION,
    SYMBOL_LIBRARY_VERSION,
    load_symbol_library,
    render_svg,
)
from isometric_pipeline.scene_assembly import assemble_scene
from isometric_pipeline.scene_assembly.context import AssemblyContext
from isometric_pipeline.snapping.artifact import (
    PagePoint as SnapPoint,
)
from isometric_pipeline.snapping.artifact import (
    SegmentGeom,
    SnappedPrimitiveCandidate,
    SnappedPrimitivesMetadata,
)
from isometric_pipeline.topology.stage import infer_topology
from PIL import Image

DOC_ID = uuid.UUID("00000000-0000-4000-8000-000000000600")
REV_ID = uuid.UUID("00000000-0000-4000-8000-000000000601")


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
) -> PrimitiveCandidate:
    return PrimitiveCandidate(
        id=prim_id,
        layer_id="geometry",
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
        component_id="cmp_0",
        mask_uri="masks/geometry",
        evidence="test",
    )


def _snapped_line(prim: PrimitiveCandidate) -> SnappedPrimitiveCandidate:
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


class SceneAssemblyTest(unittest.TestCase):
    def test_profile_assembly_section_loads(self) -> None:
        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
        self.assertGreater(profile.assembly.min_symbol_combined_score, 0.0)

    def test_resolve_profile_id_from_api_form(self) -> None:
        self.assertEqual(
            resolve_piping_profile_version("piping_isometric"),
            DEFAULT_PIPING_PROFILE_VERSION,
        )
        load_piping_profile("piping_isometric")

    def test_topology_only_assembles_valid_scene_and_svg(self) -> None:
        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
        prims = [
            _line_primitive("a", 60, 180, 60, 100),
            _line_primitive("b", 60, 100, 180, 100),
        ]
        from isometric_pipeline.primitives.artifact import PrimitivesMetadata

        prim_meta = PrimitivesMetadata(
            profile_version=profile.version,
            page_width_px=256,
            page_height_px=256,
            centerlines_metadata_uri="documents/x/centerlines.json",
            masks_metadata_uri="documents/x/masks.json",
            primitives=prims,
        )
        snapped_meta = SnappedPrimitivesMetadata(
            profile_version=profile.version,
            page_width_px=256,
            page_height_px=256,
            primitives_metadata_uri="documents/x/primitives.json",
            axes_metadata_uri="documents/x/axes.json",
            candidates=[_snapped_line(p) for p in prims],
        )
        topology = infer_topology(
            _blank_page(),
            snapped_meta,
            prim_meta,
            snapped_primitives_json_uri="documents/x/snapped-primitives.json",
            primitives_json_uri="documents/x/primitives.json",
            topology_json_uri="documents/x/topology.json",
        )
        normalize = NormalizePageMetadata(
            source_width_px=256,
            source_height_px=256,
            display_width_px=256,
            display_height_px=256,
            page_width_px=256,
            page_height_px=256,
            orientation=1,
            source_to_display=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            display_to_source=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            display_to_page=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            page_to_display=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            source_to_page=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            page_to_source=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            display_artifact=RasterArtifactRef(
                uri="d/display.png",
                coordinate_space="display",
                width_px=256,
                height_px=256,
                media_type="image/png",
            ),
            page_artifact=RasterArtifactRef(
                uri="d/page.png",
                coordinate_space="page",
                width_px=256,
                height_px=256,
                media_type="image/png",
            ),
            display_hash="a",
            page_hash="b",
            diagnostics=NormalizeDiagnostics(
                blur_score=1.0,
                contrast=1.0,
                shadow_heavy=False,
                boundary_confidence=1.0,
                rectified=False,
            ),
            warnings=[],
        )
        symbol_library = load_symbol_library(profile.symbols.library_version)
        ctx = AssemblyContext(
            document_id=DOC_ID,
            revision_id=REV_ID,
            parent_revision_id=None,
            profile=profile,
            symbol_library=symbol_library,
            normalize=normalize,
            snapped=snapped_meta,
            topology=topology.metadata,
        )
        result = assemble_scene(ctx)
        self.assertGreater(result.metrics["pipe_count"], 0)
        self.assertGreater(result.metrics["junction_count"], 0)
        svg = render_svg(
            result.scene,
            symbol_library.version,
            STYLE_PROFILE_VERSION,
        ).svg
        self.assertIn(b"<svg", svg)

    def test_profile_symbol_library_covers_classifier_symbols(self) -> None:
        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
        library = load_symbol_library(profile.symbols.library_version)
        for symbol_id in ("flow_arrow", "flange", "drop"):
            self.assertIsNotNone(
                library.port_names(symbol_id),
                symbol_id,
            )
        legacy = load_symbol_library(SYMBOL_LIBRARY_VERSION)
        self.assertIsNone(legacy.port_names("flow_arrow"))

    def test_local_pipeline_white_page(self) -> None:
        from isometric_pipeline.scene_assembly.local_pipeline import run_local_pipeline

        buf = io.BytesIO()
        Image.new("RGB", (64, 64), color="white").save(buf, format="PNG")
        result = run_local_pipeline(buf.getvalue())
        self.assertIsNotNone(result.assembled.scene_json)

    def test_annotation_without_resolved_target_omits_target_object_id(self) -> None:
        from isometric_pipeline.associate_markup.artifact import (
            AnnotationAlternative,
            AnnotationTargetCandidate,
            AssociationCandidatesMetadata,
        )
        from isometric_pipeline.ocr.artifact import (
            PageBBox,
            TextCandidate,
            TextCandidatesMetadata,
        )

        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
        normalize = NormalizePageMetadata(
            source_width_px=256,
            source_height_px=256,
            display_width_px=256,
            display_height_px=256,
            page_width_px=256,
            page_height_px=256,
            orientation=1,
            source_to_display=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            display_to_source=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            display_to_page=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            page_to_display=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            source_to_page=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            page_to_source=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            display_artifact=RasterArtifactRef(
                uri="d/display.png",
                coordinate_space="display",
                width_px=256,
                height_px=256,
                media_type="image/png",
            ),
            page_artifact=RasterArtifactRef(
                uri="d/page.png",
                coordinate_space="page",
                width_px=256,
                height_px=256,
                media_type="image/png",
            ),
            display_hash="a",
            page_hash="b",
            diagnostics=NormalizeDiagnostics(
                blur_score=1.0,
                contrast=1.0,
                shadow_heavy=False,
                boundary_confidence=1.0,
                rectified=False,
            ),
            warnings=[],
        )
        text = TextCandidatesMetadata(
            profile_version=profile.version,
            page_width_px=256,
            page_height_px=256,
            regions_metadata_uri="r",
            model={"name": "fake", "revision": None, "preprocessing": {}},
            candidates=[
                TextCandidate(
                    id="txt_amb",
                    region_id="region_note",
                    region_kind="text",
                    bbox=PageBBox(x=20, y=20, width=40, height=20),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="note",
                    normalized_text="note",
                    status="proposed",
                )
            ],
        )
        associations = AssociationCandidatesMetadata(
            profile_version=profile.version,
            page_width_px=256,
            page_height_px=256,
            regions_metadata_uri="r",
            annotation_targets=[
                AnnotationTargetCandidate(
                    id="ann_amb",
                    text_candidate_id="txt_amb",
                    region_id="region_note",
                    alternatives=[
                        AnnotationAlternative(
                            ref_kind="symbol_candidate",
                            ref_id="sym_a",
                            score=0.7,
                            evidence="test",
                        ),
                        AnnotationAlternative(
                            ref_kind="symbol_candidate",
                            ref_id="sym_b",
                            score=0.65,
                            evidence="test",
                        ),
                    ],
                    status="proposed",
                )
            ],
        )
        ctx = AssemblyContext(
            document_id=DOC_ID,
            revision_id=REV_ID,
            parent_revision_id=None,
            profile=profile,
            symbol_library=load_symbol_library(SYMBOL_LIBRARY_VERSION),
            normalize=normalize,
            text=text,
            associations=associations,
        )
        result = assemble_scene(ctx)
        annotations = [o for o in result.scene.objects if o.type == "annotation"]
        self.assertEqual(len(annotations), 1)
        self.assertIsNone(annotations[0].target_object_id)


if __name__ == "__main__":
    unittest.main()
