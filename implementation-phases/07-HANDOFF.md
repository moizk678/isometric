# Run handoff — 07 Grid, ink, color, and protected regions

**Run file:** `implementation-phases/07-masks-and-regions.md`  
**Status:** complete (local verification via `./scripts/check`)  
**Next run:** `08-centerlines-and-primitives.md`

## Delivered

- **Pipeline:** `separate_masks` in [`packages/pipeline/isometric_pipeline/masks/`](../packages/pipeline/isometric_pipeline/masks/), `detect_regions` in [`regions/`](../packages/pipeline/isometric_pipeline/regions/).
- **Worker:** [`processor.py`](../services/worker/isometric_worker/processor.py) runs both stages after `normalize_page`; [`stages.py`](../services/worker/isometric_worker/stages.py) order updated. Fixture scene publication unchanged.
- **Persistence keys:** mask, crop, `masks.json`, and `regions.json` helpers in [`keys.py`](../packages/persistence/isometric_persistence/keys.py).
- **Tests:** [`test_masks_and_regions.py`](../packages/pipeline/tests/test_masks_and_regions.py), fixtures under [`masks-and-regions/`](../packages/pipeline/tests/fixtures/masks-and-regions/).
- **Docs:** [`docs/masks-and-regions.md`](../docs/masks-and-regions.md).

## Contract changes

- New stage runs: `separate_masks`, `detect_regions` with artifact URIs `documents/{id}/masks.json` and `documents/{id}/regions.json`.
- Document-scoped mask PNGs, color layer masks, and region crops under `documents/{id}/masks/` and `documents/{id}/crops/`.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-pipeline` | Pass | Includes `test_masks_and_regions` (6 tests) |
| `./scripts/test-api` | Pass | 47 tests; worker runs `separate_masks` + `detect_regions` before fixture publish |
| `./scripts/check` | Pass (exit 0) | ruff, persistence, API, pipeline, Vitest, Playwright 26/26 |

## Data used

- Synthetic PNG fixtures only (`masks-and-regions/` generator). No real drawings.

## Remaining work and risks

- Grid and region heuristics use module constants; profile YAML tuning deferred to Run 17.
- Region classification is heuristic only (no OCR or symbol typing).

## Next-run starting point

- Read [`08-centerlines-and-primitives.md`](08-centerlines-and-primitives.md), [`docs/masks-and-regions.md`](../docs/masks-and-regions.md).
- Skeletonize `documents/{id}/masks/geometry-ink.png` and per-color layer masks; respect `protection.png` and region boxes.
