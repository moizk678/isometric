# Handwriting OCR and text candidates (Run 11)

Stage `transcribe_regions` runs in **page pixel space** after Run 10 `infer_topology`. Thresholds and vocabulary come from the `ocr` section of `profiles/piping_isometric@1.0.0.yaml`.

## Stage contract

| Stage | Producer | Artifact | Diagnostics |
|---|---|---|---|
| `transcribe_regions` | `transcribe_regions@1.0.0` | `documents/{id}/text-candidates.json` | `jobs/{jobId}/stages/transcribe_regions/{hash}/overlay.png` |

Worker order: `normalize_page` → `separate_masks` → `detect_regions` → `extract_centerlines` → `fit_primitives` → `snap_primitives` → `infer_topology` → **`transcribe_regions`** → `classify_symbol_regions` → `associate_markup` → `fixture_process` (fixture scene publication unchanged).

## Inputs

- Rectified `page.png`
- `regions.json` with `text` and `dimension` region candidates and stored crop PNGs
- Optional `topology.json` for nearby node/edge context (ranking only; no invented text)

## `text-candidates.json`

- **`candidates[]`:** `TextCandidate` with separate `rawText` and `normalizedText`, OCR/vocabulary `alternatives`, optional `parsedDimension`, `cropUri`, and `rotationDeg`
- **`reviewItems[]`:** codes such as `ocr.low_confidence`, `ocr.conflicting_readings`, `ocr.unreadable`, `ocr.dimension_ambiguous`
- **`model`:** TrOCR model id/revision and preprocessing parameters

## OCR backend

- Production path: lazy-loaded `microsoft/trocr-base-handwritten` via `transformers`
- CI/tests: `FakeOcrEngine` (no Hub download); API tests set `ISOMETRIC_FAKE_OCR=1` for the inline worker
- Optional live check: `ISOMETRIC_TROCR_INTEGRATION=1` unittest

Real handwriting accuracy is **unmeasured** until labeled samples exist (Run 17).

## Downstream

Runs 12–14 consume text candidates for symbol context and dimension association. Scene assembly remains Run 14.
