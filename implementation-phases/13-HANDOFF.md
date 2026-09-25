# Run handoff — 13 Dimensions and associations

**Run file:** `implementation-phases/13-dimensions-associations.md`  
**Status:** complete (local verification via `./scripts/test-pipeline`)  
**Next run:** `14-pipeline-integration.md`

## Delivered

- **Profile:** `associations` section in [`profiles/piping_isometric@1.0.0.yaml`](../profiles/piping_isometric@1.0.0.yaml); `AssociationsProfile` in [`profiles/loader.py`](../packages/pipeline/isometric_pipeline/profiles/loader.py).
- **Pipeline:** `associate_markup` in [`associate_markup/`](../packages/pipeline/isometric_pipeline/associate_markup/) (geometry, dimensions, annotations, relationships, validate, diagnostics, stage).
- **Worker:** [`processor.py`](../services/worker/isometric_worker/processor.py) runs stage after `classify_symbol_regions`; [`stages.py`](../services/worker/isometric_worker/stages.py) order updated. Fixture scene publication unchanged.
- **Persistence keys:** `association-candidates.json` in [`keys.py`](../packages/persistence/isometric_persistence/keys.py).
- **Tests:** [`test_associate_markup.py`](../packages/pipeline/tests/test_associate_markup.py), fixtures under [`associations/`](../packages/pipeline/tests/fixtures/associations/).
- **Docs:** [`docs/association-candidates.md`](../docs/association-candidates.md).

## Contract changes

- New stage run: `associate_markup` with artifact `documents/{id}/association-candidates.json`.
- Emits dimension geometry, dimension candidates, annotation targets, relationship candidates, and review items without changing pipe topology or scale.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-pipeline` | Pass | 10 association tests + full suite (1 skipped TrOCR integration) |
| `./scripts/check` | Pass | ruff, pipeline, API, Playwright as configured |

## Data used

- Synthetic association PNG/mask fixtures and in-memory OCR/topology/symbol metadata. No labeled real drawings; association accuracy unmeasured.

## Remaining work and risks

- Markup geometry detection is heuristic; organization-specific dimension styles need tuning (Run 17).
- Review items are artifact-only until Run 14 publishes DB review rows.
- Leader tracing can fail on faint or overlapping ink; review codes surface unresolved cases.

## Next-run starting point

- Read [`14-pipeline-integration.md`](14-pipeline-integration.md), [`docs/association-candidates.md`](../docs/association-candidates.md).
- Map `dim_*`, `ann_*`, and `rel_*` candidates into scene objects and revision review planner.
