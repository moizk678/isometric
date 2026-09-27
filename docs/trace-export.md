# Trace export (raster-faithful SVG)

The **trace export** is a separate vectorization path from the [semantic SVG renderer](svg-renderer.md). It turns cleaned page ink into editable strokes that visually match the scan, without requiring a validated `DrawingScene`.

## When to use which export

| Export | Purpose |
| --- | --- |
| **Trace** (`trace.svg`) | Raster-faithful linework; available early in the pipeline |
| **Semantic** (`svg`) | Reconstructed pipes, symbols, annotations for engineering edit/review |

Both can ship on the same revision. Trace does not replace semantic validation or review items.

## Pipeline stage

`trace_ink` runs **after** `detect_regions` and **before** `extract_centerlines`. It reads:

- `documents/{id}/masks/geometry-ink.png`
- Per-color masks intersected with geometry ink
- `black_ink` and optional `unclassified_ink`

Vectorization uses skeleton polylines per layer (see `packages/pipeline/isometric_pipeline/trace/`).

## Artifacts

| Artifact | Key |
| --- | --- |
| Latest document trace | `documents/{document_id}/trace.svg` |
| Job stage artifact | `jobs/{job_id}/stages/trace_ink/{hash}/trace.svg` |
| Revision export | `documents/{document_id}/exports/{revision_id}/trace.svg` |

Trace stage failures are **non-fatal**: the job logs a warning and continues the semantic pipeline.

## API

- `GET /api/v1/documents/{document_id}/trace` — latest document trace (no revision required)
- `GET /api/v1/documents/{document_id}/revisions/{revision_id}/exports/trace` — trace copied at publish time

Same SVG CSP as semantic exports (`default-src 'none'`).

## Profile

`trace:` section in `profiles/piping_isometric@*.yaml` controls stroke width, simplification, and path caps.

## Workbench

The workbench shows **Original**, **Trace**, and **Semantic** canvases. Trace defaults on narrow layouts so a recognizable drawing appears even when semantic export is sparse.
