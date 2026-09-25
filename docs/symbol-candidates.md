# Engineering symbol candidates (Run 12)

Stage `classify_symbol_regions` runs in **page pixel space** after Run 11 `transcribe_regions`. Thresholds and allowed symbol IDs come from the `symbols` section of `profiles/piping_isometric@1.0.0.yaml`. The classifier uses symbol library `piping-symbols@1.1.0` (render exports for fixture scenes remain on `piping-symbols@1.0.0` until Run 14).

## Stage contract

| Stage | Producer | Artifact | Diagnostics |
|---|---|---|---|
| `classify_symbol_regions` | `classify_symbol_regions@1.0.0` | `documents/{id}/symbol-candidates.json` | `jobs/{jobId}/stages/classify_symbol_regions/{hash}/overlay.png` |

Worker order: `normalize_page` → `separate_masks` → `detect_regions` → `extract_centerlines` → `fit_primitives` → `snap_primitives` → `infer_topology` → `transcribe_regions` → **`classify_symbol_regions`** → `fixture_process` (fixture scene publication unchanged).

## Inputs

- Rectified `page.png`
- `regions.json` with `symbol` and `arrow` region candidates and stored crop PNGs
- `topology.json` for port attachment proposals and topology evidence scores
- `text-candidates.json` for nearby OCR (ranking only; cannot force a type without shape evidence)

## `symbol-candidates.json`

- **`candidates[]`:** `SymbolCandidate` with separate `alternatives[]` (`shapeScore`, `textScore`, `topologyScore`), proposed `anchor`, `rotationDeg`, `proposedPortAttachments`, and `nearbyTextCandidateIds`
- **`reviewItems[]`:** codes such as `symbol.low_margin`, `symbol.port_conflict`, `symbol.structural_junction_only`, `symbol.classifier_unavailable`, `symbol.ocr_insufficient_evidence`
- **`symbolLibraryVersion`:** pinned library used for labels and ports
- **`classifier`:** backend id (`template` in production path) and parameters

## Classifier backend

- Production path: `TemplateSymbolClassifier` (shape descriptors + topology/text evidence)
- CI/tests: `FakeSymbolClassifier` (no model download)
- Missing or failing backend: structured `partial` result with `symbol.classifier_unavailable` review items

Per-class accuracy on real organization drawings is **unmeasured** until labeled samples exist (Run 17).

## Downstream

Runs 13–14 consume symbol candidates for dimension association and scene assembly.
