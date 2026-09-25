# Run 09 — Isometric axis inference and geometry snapping

**Agent brief:** Clean hand-drawn angles while preserving the original primitive and evidence for every modification.

**Depends on:** [Run 08](08-centerlines-and-primitives.md). Read architecture section 3 and the piping profile rules.

## Build

1. Estimate dominant page axes from length-weighted primitive angles, optionally using a reliable grid estimate. Support vertical plus two isometric directions, but derive their rotation from the page rather than assuming exact screen angles.
2. Snap a line only if angle delta, endpoint displacement, fit residual, and nearby evidence pass profile thresholds. Record pre-snap and post-snap geometry, chosen axis, measurements, and decision reason.
3. Add constrained endpoint alignment for likely shared corners without yet declaring connectivity. Avoid changing an annotated dimension value or scaling the whole sketch.
4. Preserve unsnapped candidates when the axis model is weak, conflicting, or the stroke is likely a dimension/callout. Emit before/after overlays.
5. Version the profile thresholds and add a small tuning report on the available labeled fixtures; keep the held-out set untouched.

## Deliverables

- Axis model, snapped primitive artifact, decision log, and diagnostic overlay.

## Exit checks

- Rotated isometric fixtures infer rotated axes and straighten noisy lines within defined tolerances.
- A deliberately off-axis line remains off-axis; low-evidence cases retain the original primitive with a warning.
- Every modified endpoint can be traced back to its original point and displacement.
- Snap operation is deterministic and `make test-pipeline` passes.

## Out of scope and handoff

Do not connect crossing lines or force dimension-consistent lengths. Hand off axis/primitive contracts and uncertain endpoint cases to [Run 10](10-topology.md).
