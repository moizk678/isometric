# Run 08 — Stroke centerlines and primitive fitting

**Agent brief:** Turn route ink masks into candidate centerline segments with original evidence. Keep false-positive control visible.

**Depends on:** [Run 07](07-masks-and-regions.md). Read architecture section 3.

## Build

1. Clean the geometry mask conservatively, skeletonize it, and identify endpoints, branch pixels, short spurs, and connected components per color layer.
2. Fit straight-line candidates with robust methods; keep sampled centerline points, fitted endpoints, residual error, stroke width estimate, layer ID, and source crop/evidence. Preserve curved marks as unresolved source evidence until an arc schema and renderer are added.
3. Split only at observed branch candidates or strong geometric breakpoints. Do not merge gaps across protected symbol/text regions yet.
4. Reject or mark uncertain tiny components using versioned profile thresholds, not hardcoded global constants. Emit diagnostics showing raw mask, skeleton, and fitted primitives.
5. Add a `PrimitiveCandidate` artifact contract consumed by later snapping/topology stages.

## Deliverables

- Centerline graph and fitted primitive candidates, thresholds in the piping profile, and diagnostic overlays.

## Exit checks

- Synthetic straight, sloped, bent, thick, broken, and noisy strokes yield sensible centerlines and bounded fit residuals.
- Text-like protected regions do not become confident route segments.
- Each candidate has source evidence and pre-fit samples; a rejected component remains inspectable in diagnostics.
- No topology connection is inferred here; `make test-pipeline` passes.

## Out of scope and handoff

Do not snap to isometric axes or create final pipe graph nodes. Hand off primitive schema and residual metrics to [Run 09](09-axis-snapping.md).
