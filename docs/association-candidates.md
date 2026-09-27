# Dimension and annotation associations (Run 13)

Stage `associate_markup` runs in **page pixel space** after Run 12 `classify_symbol_regions`. Thresholds come from the `associations` section of `profiles/piping_isometric@1.0.0.yaml`.

## Stage contract

| Stage | Producer | Artifact | Diagnostics |
|---|---|---|---|
| `associate_markup` | `associate_markup@1.0.0` | `documents/{id}/association-candidates.json` | `jobs/{jobId}/stages/associate_markup/{hash}/overlay.png` |

Worker order: `normalize_page` → `separate_masks` → `detect_regions` → `extract_centerlines` → `fit_primitives` → `snap_primitives` → `infer_topology` → `transcribe_regions` → `classify_symbol_regions` → **`associate_markup`** → **`assemble_scene`** (`fixture_process` when `ISOMETRIC_WORKER_FIXTURE_ONLY=1`).

## Inputs

- Rectified `page.png`
- `regions.json` with text, dimension, arrow, and symbol region candidates
- `geometry-ink.png` (via masks / regions metadata)
- `topology.json` for pipe edge/node target proposals
- `text-candidates.json` for OCR text and parsed dimension hints
- `symbol-candidates.json` for symbol anchor targets

This stage **does not** modify topology, primitives, or pipe geometry.

## `association-candidates.json`

- **`dimensionGeometry[]`:** witness lines, optional arrow evidence (separate from pipe topology edges)
- **`dimensionCandidates[]`:** links text candidates to witness endpoints, preserves OCR `parsedDimension` / `displayText`, and ranked `targetRefs` (topology edges)
- **`annotationTargets[]`:** note text with optional `leaderPolyline`, ranked target alternatives (symbol / topology refs)
- **`relationships[]`:** `measures`, `annotates`, and `callout_targets` with `interpretation` (`proposed` / `unresolved` / `rejected`) and evidence
- **`reviewItems[]`:** codes such as `dimension.no_witness_line`, `dimension.missing_arrow`, `dimension.unit_conflict`, `dimension.multiple_targets`, `annotation.no_leader`, `annotation.ambiguous_target`, `association.unresolved`, `association.upstream_missing`

## Candidate ID prefixes (Run 14)

| Prefix | Meaning |
|---|---|
| `dim_geo_*` | Detected dimension line geometry |
| `dim_{textCandidateId}` | Structured dimension candidate |
| `ann_{textCandidateId}` | Annotation / callout target candidate |
| `rel_*` | Relationship candidate (deterministic hash) |

## Downstream

Run 14 assembles scene `Dimension`, `Annotation`, and `Relationship` objects from these candidates and promotes review items to revision snapshots.
