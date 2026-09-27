# Pipeline integration (Run 14)

Stage **`assemble_scene`** runs after `associate_markup`. It builds a validated `DrawingScene`, renders SVG/preview, and publishes a revision (worker) or writes diagnostic files (CLI).

## Stage order

`normalize_page` → `separate_masks` → `detect_regions` → **`trace_ink`** → `extract_centerlines` → `fit_primitives` → `snap_primitives` → `infer_topology` → `transcribe_regions` → `classify_symbol_regions` → `associate_markup` → **`assemble_scene`**

See also [`docs/trace-export.md`](trace-export.md) for the raster-faithful trace export.

`fixture_process` remains available when `ISOMETRIC_WORKER_FIXTURE_ONLY=1`.

## Assembly

- Package: `packages/pipeline/isometric_pipeline/scene_assembly/`
- Deterministic scene UUIDs: `scene_ids.scene_object_id(document_id, candidate_id)`
- Resolves topology, symbols, OCR text, association dimensions/relationships, and unknown regions
- Merges review items from topology, OCR, symbols, and associations into revision review rows
- Profile thresholds: `assembly` section in `profiles/piping_isometric@1.0.0.yaml`

## Publish modes

| Case | `advance_current_revision` | `current_revision_id` |
|------|---------------------------|------------------------|
| First job on document | true | moves to new revision |
| Machine revision chain | true | moves when CAS matches parent |
| Reprocess while reviewed current | false | unchanged; candidate revision stored |

Reprocess: `POST /api/v1/documents/{id}/reprocess` enqueues a new job with `options_hash=reprocess`. When the current revision is human-reviewed, confirmed scene objects are pinned onto the candidate (see [`docs/review-editor.md`](review-editor.md)).

## Artifacts

| Artifact | Key |
|----------|-----|
| Scene revision | `documents/{id}/revisions/{revision_id}/scene.json` |
| Job manifest | `jobs/{job_id}/pipeline-manifest.json` |

## Diagnostic CLI

```bash
./scripts/run-pipeline-diagnostic path/to/sketch.png --output-dir .private/diagnostic
```

Writes `manifest.json`, `scene.json`, `export.svg`, `preview.png`, and `unresolved.json`.
