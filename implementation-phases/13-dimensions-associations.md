# Run 13 — Dimensions, arrows, and annotation targets

**Agent brief:** Link recognized labels and marks to geometry without changing measured pipe geometry.

**Depends on:** [Runs 10–12](12-symbol-candidates.md). Read architecture section 3 and scene object definitions.

## Build

1. Detect dimension lines, extension/witness lines, arrowheads, and callout leaders from region/mask artifacts. Keep these separate from pipe edges.
2. Associate parsed dimension text from Run 11 to likely witness endpoints using proximity, orientation, arrow evidence, and text location. Produce structured value/unit plus `displayText` and source evidence.
3. Associate annotations to symbol, pipe, junction, or equipment candidates using leader target first, then spatial and semantic context. Store alternatives when more than one target is plausible.
4. Create explicit relationship candidates (`measures`, `annotates`, `callout_targets`) with evidence and unknown/unresolved states. Never auto-calibrate scale or resize a pipe to match a handwritten dimension.
5. Generate review items for conflicting units, multiple plausible targets, missing arrows, and dimension text with no supported line.

## Deliverables

- Dimension/callout/association candidate artifacts, evidence scoring, and review-item rules.

## Exit checks

- Fixtures cover a clean dimension, a note with leader, a note without leader, overlapping note/pipe ink, and ambiguous target choice.
- A `20 ft` text value remains `20 ft` even if its pixel span is inconsistent; no geometry changes in this stage.
- Relationships reference existing candidate IDs; unresolved associations remain explicit.
- `make test-pipeline` passes with diagnostics showing source and candidate targets.

## Out of scope and handoff

Do not assemble a published scene revision or infer an engineering scale. Hand off candidate relationships and conflict codes to [Run 14](14-pipeline-integration.md).
