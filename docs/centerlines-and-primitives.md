# Centerlines and primitives (Run 08)

Stages `extract_centerlines` and `fit_primitives` operate in **page pixel space** after Run 07 masks and regions. Thresholds come from `profiles/piping_isometric@1.0.0.yaml` (loaded as `piping_isometric@1.0.0`).

## Stages

| Stage | Producer | Document artifact | Job diagnostic |
|---|---|---|---|
| `extract_centerlines` | `extract_centerlines@1.0.0` | `documents/{id}/centerlines.json` | `jobs/{jobId}/stages/extract_centerlines/{hash}/overlay.png` |
| `fit_primitives` | `fit_primitives@1.0.0` | `documents/{id}/primitives.json` | `jobs/{jobId}/stages/fit_primitives/{hash}/overlay.png` |

Worker order: `normalize_page` → `separate_masks` → `detect_regions` → **`extract_centerlines`** → **`fit_primitives`** → `fixture_process` (fixture scene publication unchanged).

## Inputs

- `masks/geometry-ink.png` and optional `masks/color/{layerId}.png` from Run 07
- `masks.json`, `regions.json` (region boxes are cleared again before skeletonization)
- Versioned profile `piping_isometric@1.0.0`

## `centerlines.json`

- **Layers:** `geometry` plus each color layer with mask URI and counts
- **Components:** accepted ink blobs with page `bbox` and optional crop URI
- **Rejected components:** tiny or empty-skeleton blobs with `reason` (inspectable in metadata)
- **Nodes / edges:** skeleton graph in page coordinates; each `edge` has ordered `samples`

## `primitives.json`

- **`PrimitiveCandidate`:** straight `line` with fitted `start`/`end`, pre-fit `samples`, `residualRmsPx`, `strokeWidthPx`, `fitMetric` (R²), `confidence`, `status` (`accepted` / `uncertain` / `rejected`), and mask `evidence`
- **`UnresolvedEvidence`:** non-straight strokes (e.g. bends) kept as sample polylines until arc primitives exist
- **`rejections`:** edges that failed length/residual thresholds

## Run 09 handoff

Run 09 reads `primitives.json` accepted/uncertain line candidates (unsnapped page coordinates). It does not use topology from `centerlines.json`; connectivity is still out of scope.
