"""Run pipeline stages in memory and assemble a scene (no persistence)."""

from __future__ import annotations

import uuid

from dataclasses import dataclass

from isometric_pipeline.associate_markup.stage import associate_markup
from isometric_pipeline.centerlines.stage import extract_centerlines
from isometric_pipeline.masks.stage import separate_masks
from isometric_pipeline.normalize.page import NormalizeLimits, normalize_page
from isometric_pipeline.ocr.stage import transcribe_regions
from isometric_pipeline.primitives.stage import fit_primitives
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.stage import detect_regions
from isometric_pipeline.trace import trace_ink
from isometric_pipeline.render.symbols import load_symbol_library
from isometric_pipeline.scene_assembly.assemble import AssemblyResult, assemble_scene
from isometric_pipeline.scene_assembly.context import AssemblyContext
from isometric_pipeline.snapping.stage import snap_primitives
from isometric_pipeline.symbol_candidates.stage import classify_symbol_regions
from isometric_pipeline.topology.stage import infer_topology


@dataclass(frozen=True)
class LocalPipelineResult:
    assembled: AssemblyResult
    trace_svg: bytes


def run_local_pipeline(
    source_bytes: bytes,
    *,
    document_id: uuid.UUID | None = None,
    revision_id: uuid.UUID | None = None,
    profile_version: str = DEFAULT_PIPING_PROFILE_VERSION,
) -> LocalPipelineResult:
    doc_id = document_id or uuid.uuid4()
    rev_id = revision_id or uuid.uuid5(
        uuid.UUID("8d8a0c3e-6b1a-4f0e-9c2d-1a7e5b4c9d20"), str(doc_id)
    )
    doc = str(doc_id)
    profile = load_piping_profile(profile_version)
    prefix = f"documents/{doc}"

    normalized = normalize_page(
        source_bytes,
        limits=NormalizeLimits(),
        display_uri=f"{prefix}/display.png",
        page_uri=f"{prefix}/page.png",
    )
    page_png = normalized.page_png
    separated = separate_masks(
        page_png,
        document_id=doc,
        page_uri=f"{prefix}/page.png",
        masks_json_uri=f"{prefix}/masks.json",
    )
    regions = detect_regions(
        page_png,
        separated.metadata,
        separated.masks["retained_ink"],
        separated.masks["black_ink"],
        document_id=doc,
        masks_json_uri=f"{prefix}/masks.json",
    )
    traced = trace_ink(
        geometry_ink_png=regions.geometry_ink_png,
        masks_metadata=regions.updated_masks_metadata,
        color_layer_masks=separated.color_layer_masks,
        black_ink_png=separated.masks["black_ink"],
        unclassified_ink_png=separated.masks["unclassified_ink"],
        profile=profile,
    )
    extracted = extract_centerlines(
        page_png,
        regions.geometry_ink_png,
        separated.color_layer_masks,
        regions.updated_masks_metadata,
        regions.regions_metadata,
        document_id=doc,
        masks_json_uri=f"{prefix}/masks.json",
        regions_json_uri=f"{prefix}/regions.json",
        centerlines_json_uri=f"{prefix}/centerlines.json",
        protection_png=regions.protection_png,
        profile_version=profile_version,
    )
    layer_masks: dict[str, bytes] = {"geometry": regions.geometry_ink_png}
    layer_masks.update(separated.color_layer_masks)
    fitted = fit_primitives(
        page_png,
        extracted.metadata,
        layer_masks,
        centerlines_json_uri=f"{prefix}/centerlines.json",
        masks_json_uri=f"{prefix}/masks.json",
        regions_json_uri=f"{prefix}/regions.json",
        primitives_json_uri=f"{prefix}/primitives.json",
        profile_version=profile_version,
    )
    snapped = snap_primitives(
        page_png,
        fitted.metadata,
        primitives_json_uri=f"{prefix}/primitives.json",
        axes_json_uri=f"{prefix}/axes.json",
        snapped_primitives_json_uri=f"{prefix}/snapped-primitives.json",
        masks_json_uri=f"{prefix}/masks.json",
        regions=regions.regions_metadata,
        regions_json_uri=f"{prefix}/regions.json",
        grid_mask_png=separated.masks.get("grid"),
        grid_confidence=separated.metadata.diagnostics.grid_confidence,
        profile_version=profile_version,
    )
    topology = infer_topology(
        page_png,
        snapped.snapped_metadata,
        fitted.metadata,
        snapped_primitives_json_uri=f"{prefix}/snapped-primitives.json",
        primitives_json_uri=f"{prefix}/primitives.json",
        topology_json_uri=f"{prefix}/topology.json",
        layer_masks=separated.color_layer_masks,
    )
    ocr = transcribe_regions(
        page_png,
        regions.regions_metadata,
        regions_json_uri=f"{prefix}/regions.json",
        text_candidates_json_uri=f"{prefix}/text-candidates.json",
        region_crops=regions.crop_pngs,
        topology=topology.metadata,
        topology_json_uri=f"{prefix}/topology.json",
        profile_version=profile_version,
    )
    symbols = classify_symbol_regions(
        page_png,
        regions.regions_metadata,
        regions_json_uri=f"{prefix}/regions.json",
        symbol_candidates_json_uri=f"{prefix}/symbol-candidates.json",
        region_crops=regions.crop_pngs,
        topology=topology.metadata,
        topology_json_uri=f"{prefix}/topology.json",
        text_candidates=ocr.metadata,
        text_candidates_json_uri=f"{prefix}/text-candidates.json",
        profile_version=profile_version,
    )
    associations = associate_markup(
        page_png,
        regions.regions_metadata,
        regions_json_uri=f"{prefix}/regions.json",
        association_candidates_json_uri=f"{prefix}/association-candidates.json",
        geometry_ink_png=regions.geometry_ink_png,
        masks_metadata_uri=f"{prefix}/masks.json",
        topology=topology.metadata,
        topology_json_uri=f"{prefix}/topology.json",
        text_candidates=ocr.metadata,
        text_candidates_json_uri=f"{prefix}/text-candidates.json",
        symbol_candidates=symbols.metadata,
        symbol_candidates_json_uri=f"{prefix}/symbol-candidates.json",
        profile_version=profile_version,
    )

    ctx = AssemblyContext(
        document_id=doc_id,
        revision_id=rev_id,
        parent_revision_id=None,
        profile=profile,
        symbol_library=load_symbol_library(profile.symbols.library_version),
        normalize=normalized.metadata,
        masks=regions.updated_masks_metadata,
        regions=regions.regions_metadata,
        snapped=snapped.snapped_metadata,
        topology=topology.metadata,
        text=ocr.metadata,
        symbols=symbols.metadata,
        associations=associations.metadata,
        warnings=list(normalized.warnings),
    )
    return LocalPipelineResult(assembled=assemble_scene(ctx), trace_svg=traced.svg)
