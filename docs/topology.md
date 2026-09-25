# Junction and pipe topology (Run 10)

Stage `infer_topology` operates in **page pixel space** after Run 09 `snap_primitives`. Thresholds come from the `topology` section of `profiles/piping_isometric@1.0.0.yaml`.

## Stage

| Stage | Producer | Document artifact | Job diagnostic |
|---|---|---|---|
| `infer_topology` | `infer_topology@1.0.0` | `documents/{id}/topology.json` | `jobs/{jobId}/stages/infer_topology/{hash}/overlay.png` |

Worker order: `normalize_page` → `separate_masks` → `detect_regions` → `extract_centerlines` → `fit_primitives` → `snap_primitives` → **`infer_topology`** → `transcribe_regions` → `classify_symbol_regions` → `fixture_process` (fixture scene publication unchanged).

## Inputs

- `snapped-primitives.json` — `postSnap` geometry for non-`skipped` candidates
- `primitives.json` — provenance (`primitiveId`, `layer_id`, `component_id`, `centerline_edge_id`)
- `regions.json` — symbol regions block unsafe merges through protected areas
- `masks.json` and `masks/geometry-ink.png` / color layer masks — ink continuity for collinear merge and intersection scoring

## `topology.json`

- **`nodes[]`:** `endpoint`, `elbow`, `tee`, `crossing`, or `unknown` with page position and evidence
- **`edges[]`:** pipe segment candidates with `startNodeId`, `endNodeId`, `layerId`, geometry, and `sourcePrimitiveIds`
- **`hypotheses[]`:** competing intersection interpretations (e.g. `crossing` vs `tee`) with scored alternatives
- **`reviewItems[]`:** codes such as `topology.crossing_unresolved` and `topology.near_miss_endpoints`

Connectivity is expressed only through edge endpoint node IDs. Pixel intersection alone does not create a shared junction node.

## Run 11+ handoff

Runs 11–12 consume `topology.json` for OCR context and symbol port attachment. Scene assembly remains Run 14.
