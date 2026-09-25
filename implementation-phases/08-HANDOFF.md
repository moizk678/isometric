# Run handoff — 08 Stroke centerlines and primitive fitting

**Run file:** `implementation-phases/08-centerlines-and-primitives.md`  
**Status:** complete (local verification via `./scripts/test-pipeline`)  
**Next run:** `09-axis-snapping.md`

## Delivered

- **Profile:** [`profiles/piping_isometric@1.0.0.yaml`](../profiles/piping_isometric@1.0.0.yaml) and loader in [`packages/pipeline/isometric_pipeline/profiles/`](../packages/pipeline/isometric_pipeline/profiles/).
- **Pipeline:** `extract_centerlines` in [`centerlines/`](../packages/pipeline/isometric_pipeline/centerlines/), `fit_primitives` in [`primitives/`](../packages/pipeline/isometric_pipeline/primitives/).
- **Worker:** [`processor.py`](../services/worker/isometric_worker/processor.py) runs both stages after `detect_regions`; [`stages.py`](../services/worker/isometric_worker/stages.py) order updated. Fixture scene publication unchanged.
- **Persistence keys:** `centerlines.json`, `primitives.json` in [`keys.py`](../packages/persistence/isometric_persistence/keys.py).
- **Tests:** [`test_centerlines_and_primitives.py`](../packages/pipeline/tests/test_centerlines_and_primitives.py), fixtures under [`centerlines-and-primitives/`](../packages/pipeline/tests/fixtures/centerlines-and-primitives/).
- **Docs:** [`docs/centerlines-and-primitives.md`](../docs/centerlines-and-primitives.md).

## Contract changes

- New stage runs: `extract_centerlines`, `fit_primitives` with artifact URIs `documents/{id}/centerlines.json` and `documents/{id}/primitives.json`.
- `PrimitiveCandidate` and centerline graph schemas (page space, profile version recorded).
- Dependency: `PyYAML` in [`requirements-dev.in`](../requirements-dev.in) for profile loading.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-pipeline` | Pass | Includes `test_centerlines_and_primitives` (9 tests) |
| `./scripts/test-api` | Pass | Worker runs new stages before fixture publish |
| `./scripts/check` | Run locally | ruff + full suite when `SUPABASE_DATABASE_URL` set |

## Data used

- Synthetic stroke PNG fixtures and chained Run 07 `text-blocks` fixture. No real drawings.

## Remaining work and risks

- Profile thresholds are initial defaults; calibration deferred to Run 17.
- Bent strokes may split into multiple straight legs rather than a single unresolved polyline.
- L-shaped routes produce multiple accepted segments at the corner; no arc primitive yet.

## Next-run starting point

- Read [`09-axis-snapping.md`](09-axis-snapping.md), [`docs/centerlines-and-primitives.md`](../docs/centerlines-and-primitives.md).
- Consume `primitives.json` accepted/uncertain line candidates; preserve pre-snap coordinates in new artifacts.
