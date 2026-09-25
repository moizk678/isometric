# Run 17 — Real-drawing evaluation and confidence calibration

**Agent brief:** Measure the pipeline on held-out engineering sketches and set review policy from evidence. This run cannot be marked complete using only synthetic fixtures.

**Depends on:** [Runs 00 and 14–16](16-vision-ambiguity.md). A consented, labeled real-sketch dataset is required for the exit gate. Read architecture sections 9 and 12.

## Build

1. Freeze dataset split and annotation version before tuning. Include scan/photo, clean/messy, color/monochrome, grid/no-grid, and ambiguous cases. Keep training/tuning data separate from held-out test pages. Use only consented, access-controlled real drawings in an offline evaluation environment until Run 18 security is complete. Have the product owner and engineering reviewer approve acceptance thresholds and acceptable human review burden before inspecting held-out results; an agent must not invent this sign-off.
2. Implement or finish metric calculators: route centerline recall under a declared distance tolerance, endpoint and angle error, topology edge/node precision and recall, OCR CER/WER and engineering term accuracy, symbol per-class precision/recall, dimension value/unit/association accuracy, and review minutes/corrections per page.
3. Record critical semantic errors separately: false confirmed pipe connection, wrong confirmed valve type, and wrong confirmed dimension value. Include source crops and scene IDs for every such failure.
4. Calibrate task-specific scores and review thresholds on tuning data, then run the frozen test set once per candidate release. Compare vision-enabled and disabled variants on accuracy, review burden, latency/cost, and critical errors if live vision has passed Run 16. Otherwise evaluate the deterministic path and label vision benefit unmeasured.
5. Produce an evaluation report with dataset composition, annotation agreement or known ambiguity, metric definitions, confidence intervals, failure examples, and threshold/profile versions.

## Deliverables

- Reproducible benchmark command, frozen manifests, labeled ground truth references, calibration configuration, and held-out report.

## Exit checks

- Metrics rerun from pinned artifacts and yield the same result within documented numeric tolerance.
- No test-set labels leak into threshold tuning; synthetic fixture results are reported separately.
- Thresholds are justified by measured errors and review burden, not provider self-scores or the spec's aspirational percentages.
- A system that flags nearly every critical object is reported as high review burden, not a successful automatic conversion.
- Critical errors and unresolved cases are reported individually; release gate status is explicit.
- If real labeled pages are unavailable, leave this run blocked and specify the exact data needed.

## Out of scope and handoff

Do not silently lower acceptance criteria or claim production accuracy from an unlabeled sample. Hand off calibrated profile, benchmark report, and release-blocking failures to [Run 18](18-security-privacy.md).
