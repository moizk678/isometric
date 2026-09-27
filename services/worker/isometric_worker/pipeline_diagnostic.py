"""Run deterministic pipeline stages on one image and write diagnostic artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.render import (
    STYLE_PROFILE_VERSION,
    SYMBOL_LIBRARY_VERSION,
    load_symbol_library,
    rasterize_preview,
    render_svg,
)
from isometric_pipeline.scene import load_scene
from isometric_pipeline.scene_assembly.local_pipeline import run_local_pipeline
from isometric_pipeline.scene_assembly.manifest import (
    PipelineManifest,
    StageManifestEntry,
)

from isometric_worker.stages import ASSEMBLE_SCENE_VERSION, PIPELINE_VERSION


def _write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_bytes(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run pipeline diagnostic on one image")
    parser.add_argument("image", type=Path, help="PNG or JPEG input")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".private/diagnostic"),
        help="Directory for manifest, scene, exports",
    )
    parser.add_argument(
        "--document-id",
        type=uuid.UUID,
        default=None,
        help="Synthetic document UUID for assembly IDs",
    )
    args = parser.parse_args(argv)
    source_bytes = args.image.read_bytes()
    doc_id = args.document_id or uuid.uuid4()
    profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
    try:
        pipeline_result = run_local_pipeline(
            source_bytes,
            document_id=doc_id,
            profile_version=profile.version,
        )
        assembled = pipeline_result.assembled
    except Exception as exc:
        print(f"pipeline failed: {exc}", file=sys.stderr)
        return 1

    catalog = load_symbol_library(profile.symbols.library_version)
    scene = load_scene(assembled.scene_json, catalog=catalog)
    svg = render_svg(scene, SYMBOL_LIBRARY_VERSION, STYLE_PROFILE_VERSION).svg
    preview = rasterize_preview(svg).png

    out = args.output_dir
    _write(out / "scene.json", assembled.scene_json)
    _write(out / "export.svg", svg)
    _write(out / "export-trace.svg", pipeline_result.trace_svg)
    _write(out / "preview.png", preview)
    unresolved = [
        {
            "issueKey": item.issue_key,
            "issueType": item.issue_type,
            "severity": item.severity,
            "objectId": item.object_id,
        }
        for item in assembled.review_items
    ]
    _write(out / "unresolved.json", json.dumps(unresolved, indent=2) + "\n")
    manifest = PipelineManifest(
        pipeline_version=PIPELINE_VERSION,
        profile_version=profile.version,
        stages=(
            StageManifestEntry(
                stage="assemble_scene",
                producer_version=ASSEMBLE_SCENE_VERSION,
                input_hash=str(assembled.metrics.get("object_count", 0)),
                artifact_uri=str(out / "scene.json"),
                status="succeeded",
                warnings=assembled.warnings,
            ),
        ),
    )
    _write(out / "manifest.json", manifest.to_bytes().decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
