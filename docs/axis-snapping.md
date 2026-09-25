# Axis inference and snapping (Run 09)

Stage `snap_primitives` operates in **page pixel space** after Run 08 `fit_primitives`. Thresholds come from the `snapping` section of `profiles/piping_isometric@1.0.0.yaml`.

## Stage

| Stage | Producer | Document artifacts | Job diagnostic |
|---|---|---|---|
| `snap_primitives` | `snap_primitives@1.0.0` | `documents/{id}/axes.json`, `documents/{id}/snapped-primitives.json` | `jobs/{jobId}/stages/snap_primitives/{hash}/overlay.png` |

Worker order: `normalize_page` → `separate_masks` → `detect_regions` → `extract_centerlines` → `fit_primitives` → **`snap_primitives`** → `fixture_process` (fixture scene publication unchanged).

## Inputs

- `primitives.json` — accepted/uncertain line candidates (pre-snap authority; never mutated)
- `masks.json` — optional `gridConfidence` for grid-assisted axis refinement
- `masks/grid.png` — optional grid mask for Hough orientation hint when confidence is high
- `regions.json` — dimension regions used to skip snapping when overlap is detected

## `axes.json`

- **Inference:** length-weighted primitive angles; vertical + two isometric directions at 120° spacing, rotated to match the page (`rotationDeg`)
- **Methods:** `primitive_histogram`, `grid_assisted`, or `insufficient_evidence`
- **`axes[]`:** `vertical`, `iso_a`, `iso_b` with `angleDeg`, `weight`, `confidence`
- **`modelConfidence`:** aggregate alignment score

## `snapped-primitives.json`

- **`candidates[]`:** one record per accepted/uncertain primitive (sorted by `primitiveId`)
- **`preSnap` / `postSnap`:** segment geometry; equal when preserved
- **`decisionReason`:** `snapped_to_axis`, `weak_axis_model`, `off_axis`, `endpoint_displacement`, `residual_too_high`, `dimension_region`, `low_evidence`, `preserved_uncertain`
- **`endpointAdjustments`:** optional post-snap corner nudges (no topology)

## Run 10 handoff

Run 10 consumes `snapped-primitives.json` for junction and pipe graph hypotheses. `primitives.json` remains the audit trail for pre-snap geometry.
