# Run 12 — Engineering symbol candidates

**Agent brief:** Create a reusable piping symbol vocabulary and candidate classifier; leave uncertain marks unresolved.

**Depends on:** [Run 07](07-masks-and-regions.md) crops, [Run 10](10-topology.md) graph, and [Run 11](11-handwriting-ocr.md) nearby text. Read the spec's symbol-library section.

## Build

1. Extend the versioned symbol library with ball valve, block/bleed assembly, explicit tee/elbow fitting, flange, threaded connection, drop/riser, endpoint, flow arrow, equipment connection, and unknown. Define ports, anchor, orientation, allowed graph attachments, and aliases. A structural tee/elbow junction alone must not generate a second fitting symbol.
2. Implement template/shape or small-model candidate scoring behind a classifier interface. Combine crop shape, connected pipe context, and nearby OCR text as separate recorded evidence; avoid a single opaque confidence number.
3. Return top candidate labels, position/orientation proposed by deterministic image analysis, crop evidence, and an unknown option. Do not permit OCR text alone to force a symbol type.
4. Validate proposed named port-to-node attachments against the topology graph and pinned symbol definition. Conflicts create review items and do not silently alter connectivity.
5. Add diagnostic crops with overlayed candidate labels and a configurable profile list of allowed symbols.

## Deliverables

- Symbol profile/library entries, candidate classifier interface and baseline, port validator, and unknown-mark path.

## Exit checks

- Each supported synthetic symbol yields the intended candidate among top options and valid port geometry.
- Ambiguous or organization-specific marks remain `unknown`/reviewable.
- Nearby note text can change ranking but cannot create or delete a pipe edge.
- Classifier/provider absence produces a structured partial result, not pipeline failure.

## Out of scope and handoff

Do not invoke an LLM/Vision API or claim per-class accuracy without labeled drawings. Hand off candidate IDs, label vocabulary, port rules, and unresolved cases to [Run 13](13-dimensions-associations.md).
