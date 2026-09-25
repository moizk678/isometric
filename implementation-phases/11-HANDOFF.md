# Run handoff — 11 Handwriting detection and OCR candidates

**Run file:** `implementation-phases/11-handwriting-ocr.md`  
**Status:** complete (local verification via `./scripts/test-pipeline`)  
**Next run:** `12-symbol-candidates.md`

## Delivered

- **Profile:** `ocr` section in [`profiles/piping_isometric@1.0.0.yaml`](../profiles/piping_isometric@1.0.0.yaml); `OcrProfile` in [`profiles/loader.py`](../packages/pipeline/isometric_pipeline/profiles/loader.py).
- **Pipeline:** `transcribe_regions` in [`ocr/`](../packages/pipeline/isometric_pipeline/ocr/) (adapter, preprocess, vocabulary, dimensions, context, validate, diagnostics, stage).
- **Worker:** [`processor.py`](../services/worker/isometric_worker/processor.py) runs `transcribe_regions` after `infer_topology`; [`stages.py`](../services/worker/isometric_worker/stages.py) order updated. Fixture scene publication unchanged.
- **Persistence keys:** `text-candidates.json` in [`keys.py`](../packages/persistence/isometric_persistence/keys.py).
- **Dependencies:** `torch==2.6.0`, `transformers==4.49.0` in [`requirements-dev.lock`](../requirements-dev.lock).
- **Tests:** [`test_handwriting_ocr.py`](../packages/pipeline/tests/test_handwriting_ocr.py), fixtures under [`ocr/`](../packages/pipeline/tests/fixtures/ocr/).
- **Docs:** [`docs/handwriting-ocr.md`](../docs/handwriting-ocr.md).

## Contract changes

- New stage run: `transcribe_regions` with artifact `documents/{id}/text-candidates.json`.
- Text candidates retain raw vs normalized text, alternatives, dimension parse hints, and review items; unreadable OCR yields partial status without fabricated transcription.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-pipeline` | Pass | 13 OCR tests + full suite (1 skipped TrOCR integration) |
| `./scripts/test-api` | Not re-run this session | Worker path includes `transcribe_regions` |
| `./scripts/check` | Not re-run this session | ruff on changed files recommended before merge |

## Data used

- Synthetic OCR PNG fixtures and `FakeOcrEngine` responses. No real handwriting dataset; **accuracy unmeasured**.

## Remaining work and risks

- TrOCR may misread engineering shorthand; vocabulary ranking and review items mitigate but do not guarantee accuracy.
- Worker memory/CPU cost when TrOCR loads on first crop; document min resources for deployment (Run 19).
- Review items are artifact-only until Run 14 publishes DB review rows.

## Next-run starting point

- Read [`12-symbol-candidates.md`](12-symbol-candidates.md), [`docs/handwriting-ocr.md`](../docs/handwriting-ocr.md).
- Use `text-candidates.json` and region crop URIs alongside `topology.json` for symbol classification context.
