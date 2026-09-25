# Run handoff — 06 Safe image ingestion and page normalization

**Run file:** `implementation-phases/06-page-normalization.md`  
**Status:** complete (local verification via `./scripts/check`)  
**Next run:** `07-masks-and-regions.md`

## Delivered

- **Pipeline:** `normalize_page` in [`packages/pipeline/isometric_pipeline/normalize/`](../packages/pipeline/isometric_pipeline/normalize/), shared 3×3 math in [`geometry/transforms.py`](../packages/pipeline/isometric_pipeline/geometry/transforms.py), EXIF frame in [`ingest/exif_frame.py`](../packages/pipeline/isometric_pipeline/ingest/exif_frame.py) (worker [`fixture_fit.py`](../services/worker/isometric_worker/fixture_fit.py) re-exports behavior).
- **Dependencies:** `numpy`, `opencv-python-headless` in [`requirements-dev.in`](../requirements-dev.in) / lockfile.
- **Worker:** [`processor.py`](../services/worker/isometric_worker/processor.py) runs `normalize_page` before fixture publish; [`stages.py`](../services/worker/isometric_worker/stages.py) names stages; fixture scene matrices unchanged (`sourceToPage == sourceToDisplay`).
- **API:** [`GET /documents/{id}/display`](../services/api/isometric_api/routes.py) serves cached `documents/{id}/display.png` with EXIF fallback.
- **Tests:** [`test_normalize_page.py`](../packages/pipeline/tests/test_normalize_page.py), fixtures under [`page-normalization/`](../packages/pipeline/tests/fixtures/page-normalization/), API test for cached display in [`test_api_followups.py`](../services/api/tests/test_api_followups.py).
- **Docs:** [`docs/page-normalization.md`](../docs/page-normalization.md), [`docs/web.md`](../docs/web.md) display section updated.

## Contract changes

- New artifact keys: `document_display_key`, `document_page_key`, `document_normalize_metadata_key` in [`keys.py`](../packages/persistence/isometric_persistence/keys.py).
- Job `stage_runs` for `normalize_page` with `status` `succeeded` or `partial`, `warnings` including `page_boundary_low_confidence` when unrectified.
- Fixture revision publication unchanged; page rectification metadata is stored in `normalize.json` for Run 07+.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-pipeline` | Pass | Includes `test_normalize_page` (9 tests) |
| `./scripts/test-api` | Pass | `test_display_served_from_normalize_artifact_after_upload` |
| `./scripts/check` | Pass (exit 0) | ruff, persistence 10, API 47, pipeline 183 + evaluation 6, Vitest 64, Playwright 26/26 |

## Data used

- Synthetic PNG/JPEG fixtures only (`page-normalization/` generator). No real drawings.

## Remaining work and risks

- Rectification thresholds are constants in `normalize/page.py`; profile YAML tuning deferred to Run 17.
- Run 07 consumes **page** coordinate space from `page.png` and `normalize.json` transforms.

## Next-run starting point

- Read [`07-masks-and-regions.md`](07-masks-and-regions.md), [`docs/page-normalization.md`](../docs/page-normalization.md).
- Stage input: rectified page RGB from `documents/{id}/page.png`; mask dimensions must match `page_width_px` / `page_height_px` in metadata.
