# Run handoff — 12 Engineering symbol candidates

**Run file:** `implementation-phases/12-symbol-candidates.md`  
**Status:** complete (local verification via `./scripts/test-pipeline` and `./scripts/check`)  
**Next run:** `13-dimensions-associations.md`

## Delivered

- **Symbol library:** [`piping-symbols-1.1.0.json`](../packages/symbol-library/piping-symbols-1.1.0.json) with aliases and `allowedAttachments`; [`CONTRACT.md`](../packages/symbol-library/CONTRACT.md) updated; loader supports 1.0.0 (render) and 1.1.0 (classification).
- **Profile:** `symbols` section in [`profiles/piping_isometric@1.0.0.yaml`](../profiles/piping_isometric@1.0.0.yaml); `SymbolsProfile` in [`loader.py`](../packages/pipeline/isometric_pipeline/profiles/loader.py).
- **Pipeline:** `classify_symbol_regions` in [`symbol_candidates/`](../packages/pipeline/isometric_pipeline/symbol_candidates/) (adapter, template, ports, validate, diagnostics, stage).
- **Worker:** [`processor.py`](../services/worker/isometric_worker/processor.py) runs stage after `transcribe_regions`; [`stages.py`](../services/worker/isometric_worker/stages.py) order updated. Fixture scene publication unchanged.
- **Persistence keys:** `symbol-candidates.json` in [`keys.py`](../packages/persistence/isometric_persistence/keys.py).
- **Tests:** [`test_symbol_candidates.py`](../packages/pipeline/tests/test_symbol_candidates.py), fixtures under [`symbols/`](../packages/pipeline/tests/fixtures/symbols/).
- **Docs:** [`docs/symbol-candidates.md`](../docs/symbol-candidates.md).

## Contract changes

- New stage run: `classify_symbol_regions` with artifact `documents/{id}/symbol-candidates.json`.
- Symbol candidates expose separate shape/text/topology scores, port proposals validated against topology, and review items; OCR text ranks but does not force types when shape evidence is weak.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-pipeline` | Pass | 11 symbol-candidate tests + full suite (1 skipped TrOCR integration) |
| `./scripts/check` | Pass | ruff, pipeline, API, Playwright as configured |

## Data used

- Synthetic symbol PNG fixtures and `FakeSymbolClassifier` responses. No labeled real drawings; **per-class accuracy unmeasured**.

## Remaining work and risks

- Template classifier is a baseline; organization-specific tuning needs sample drawings (Run 17).
- Review items are artifact-only until Run 14 publishes DB review rows.
- Render/export still pins `piping-symbols@1.0.0` until scene assembly migrates library version in Run 14.

## Next-run starting point

- Read [`13-dimensions-associations.md`](13-dimensions-associations.md), [`docs/symbol-candidates.md`](../docs/symbol-candidates.md).
- Use `symbol-candidates.json`, `text-candidates.json`, and `topology.json` for dimension association.
