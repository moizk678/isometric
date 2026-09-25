# Run 11 — Handwriting detection and OCR candidates

**Agent brief:** Turn protected handwritten regions into evidence-backed text candidates. Do not silently correct engineering terms or replace unreadable text with a guess.

**Depends on:** [Run 07](07-masks-and-regions.md) regions and [Run 10](10-topology.md) object context. Read architecture sections 2 and 4 for candidate/evidence boundaries.

## Build

1. Add a handwriting OCR adapter with a locally runnable implementation or pinned model and a fake for tests. Record model name/version and preprocessing parameters in stage metadata.
2. Crop and deskew text regions in rectified page coordinates; retain the source-image crop reference. Return raw text, character/word alternatives when available, scores, rotation, and bounding region.
3. Add a versioned piping vocabulary and normalization pass that proposes capitalization, units, and common terms while preserving the raw transcription. Use nearby graph/symbol context only to rank alternatives, not to invent missing words.
4. Parse simple feet/inches dimension strings into candidate value/unit without attaching them to geometry. Distinguish `1'`, `1"`, illegible marks, and low-confidence punctuation.
5. Emit `TextCandidate` artifacts and review items for low confidence or conflicting readings. Include an explicit unknown/unreadable outcome.

## Deliverables

- OCR adapter, preprocessing, candidate schema, vocabulary rules, dimension-text parser, and crop diagnostics.

## Exit checks

- Fixtures cover rotated handwriting, abbreviations, uncertain words, feet/inches marks, and text crossing a line.
- Raw and normalized text survive serialization separately; low-confidence alternatives remain visible.
- OCR failure leaves the stage partial with reviewable crops rather than a fabricated transcription.
- Tests run without a live provider; if no real handwriting dataset exists, record that accuracy is unmeasured.

## Out of scope and handoff

Do not associate dimensions to pipes or use an LLM/Vision API. Hand off candidate schema, model/version, vocabulary path, and known OCR failure crops to [Run 12](12-symbol-candidates.md).
