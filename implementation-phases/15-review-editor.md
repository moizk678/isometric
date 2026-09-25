# Run 15 — Semantic review and correction editor

**Agent brief:** Let a reviewer resolve uncertainty and edit the scene safely, with a complete revision trail and regenerated exports.

**Depends on:** [Runs 05 and 14](14-pipeline-integration.md). Read architecture section 7 and the relevant `system-design` workbench, forms, controls, panels, feedback, responsive, and accessibility files.

## Build

1. Implement server edit commands for annotation text/position, symbol type/orientation, junction position, connect/disconnect via endpoint node IDs or symbol ports, layer color, and dimension display text. Validate the resulting graph and scene before committing a new revision.
2. Implement review-item resolution with `confirm`, `correct`, and `acknowledge unknown`; preserve the source evidence, alternatives, actor, timestamp, and prior value. Carry unaffected unresolved issue keys into every new revision and reevaluate affected items. Acknowledging an engineering-critical unknown does not count as confirmation or unlock a finalized export. Confirmed user edits must survive later reprocessing.
3. Add `If-Match`/expected-revision conflict handling, undo through a new revision, and clear draft/final export states. Let a reviewer explicitly adopt a reprocessed machine candidate after comparing it with the reviewed current revision and showing confirmed edits that would be lost; do not auto-merge confirmed edits. A finalized export requires all critical review items confirmed or corrected.
4. Extend the workbench with selection in either view, synchronized evidence highlighting, review queue, properties panel, semantic controls, and keyboard-accessible graph actions. Keep UI layout and states aligned with `system-design` product mode.
5. Preserve unsaved text on network failure, show pending/saved/error states, and retain selection/scroll when navigating between review items.

## Deliverables

- Edit and resolution APIs, revision events, regenerated SVG/preview, and functional review workbench.

## Exit checks

- A reviewer can correct OCR, change a symbol, and disconnect a mistaken pipe; each edit creates a valid revision and updated SVG.
- Two reviewers editing the same parent cannot silently overwrite each other; one gets a resolvable conflict.
- Critical unresolved items block the finalized label but remain available in a draft preview/export.
- Editing one item leaves unrelated unresolved issues visible on the new revision; adopting a candidate requires fresh review of its unresolved items.
- Keyboard, touch, narrow layout, 200% zoom, and failure-recovery checks pass; source evidence remains accessible.

## Out of scope and handoff

Do not let the frontend persist direct SVG DOM edits. Do not add LLM/Vision here. Hand off edit command schemas, revision behavior, and representative review sessions to [Run 16](16-vision-ambiguity.md).
