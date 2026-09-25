# Run 10 — Junction and pipe topology hypotheses

**Agent brief:** Build a pipe graph from snapped primitives, explicitly distinguishing connections from visual crossings.

**Depends on:** [Run 09](09-axis-snapping.md), plus protected symbol regions from [Run 07](07-masks-and-regions.md). Read architecture scene invariants.

## Build

1. Propose endpoints, elbows, tees, crossings, and symbol attachment points using distance, angle, color, continuity, occlusion, and protected-region evidence.
2. Merge compatible collinear fragments only when gap and intervening evidence allow it. Split segments at confirmed connection nodes while preserving stable candidate IDs and source references.
3. Represent competing hypotheses for ambiguous intersections. A crossing uses distinct node IDs until evidence or reviewer action changes the endpoint-node graph; do not create a parallel `connects` relation.
4. Output typed node/edge candidates, relationship candidates, scores by evidence category, and review items for unresolved topology. Validate that pipe ends reference existing nodes.
5. Add graph diagnostics that overlay node kinds, edges, and unresolved intersections on the source page.

## Deliverables

- Topology candidate graph, review-item generation for ambiguous connections, and graph validation tests.

## Exit checks

- Fixtures cover isolated crossing, true tee, elbow, near-miss endpoints, same-color continuation, and different-color crossing.
- No crossing becomes connected solely from pixel intersection.
- Graph serialization retains unresolved alternatives and all source evidence.
- A local graph check catches dangling node IDs; `make test-pipeline` passes.

## Out of scope and handoff

Do not classify valves or resolve topology with an LLM. Hand off node/edge candidate IDs, crossing review codes, and diagnostic examples to [Run 11](11-handwriting-ocr.md).
