# Run 20 — First-release verification and decision record

**Agent brief:** Verify the complete piping-isometric workflow against the frozen test set and staged deployment; make a documented release decision.

**Depends on:** [Runs 00–19](19-deployment-operations.md), especially the real-drawing report from Run 17 and staging evidence from Run 19.

## Build

1. Execute the frozen acceptance suite from upload through normalized page, masks, geometry, OCR, symbols, dimensions, semantic scene, review, and final SVG. Include clean scans, difficult photos, unknown symbols, and ambiguous crossings. Use acceptance thresholds and review-burden limits recorded before inspecting held-out results.
2. Check critical semantic errors individually. No false pipe connection, wrong dimension, or wrong valve may be presented as confirmed without review in the acceptance set. Preserve unresolved items and the review path.
3. Verify export reproducibility, SVG safety/editability, revision conflict handling, reprocessing without overwriting corrections, source traceability, and provider-disabled behavior. Verify the provider-enabled path only if live integration was approved and completed; otherwise keep it disabled and mark the feature as unavailable in the release record.
4. Complete UI acceptance against `system-design`: normal/hover/focus/disabled/loading/empty/error states, keyboard and touch, narrow widths, 200% zoom, contrast, reduced motion, and long labels.
5. Verify staging operations: auth boundaries, retention/deletion, queue recovery, migration version, backup/recovery evidence, and observability/alert coverage.
6. Write a release record with exact artifact/profile/model/renderer versions, dataset/report version, passed and failed gates, known limits, and a go/no-go decision. If approved, publish the documented production deployment sequence; do not treat this document as authorization to deploy.

## Deliverables

- Signed-off acceptance report or explicit no-go report, reproducible version manifest, user-facing known limitations, and production rollout/rollback checklist.

## Exit checks

- Every acceptance claim has a command, artifact, screenshot, metric report, or manual-review record.
- No unreviewed critical semantic error remains in the held-out acceptance set.
- Review burden and quality metrics meet the predeclared thresholds; an all-review workflow does not pass as automatic reconstruction.
- Real-drawing quality, security, staging, and UI gates are all complete; missing evidence yields no-go, not a presumed pass.
- The release record names the next bounded work for any failure and confirms whether production deployment was separately authorized and performed.

## Out of scope and handoff

PDF, multi-page, DXF, other engineering profiles, BOM, and CAD synchronization belong to a later expansion program. Hand off the first-release record and prioritized failure backlog to that program only after this gate is complete.
