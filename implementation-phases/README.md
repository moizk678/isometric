# Agentic implementation runs

This directory breaks the [implementation architecture](../implementation_architecture.md) into bounded, sequential development runs for the first production release. The [system specification](../hand_drawn_to_svg_system_spec.md) defines product behavior; [system-design/design.md](../system-design/design.md) is the UI design authority. A run ends with working code, verification evidence, and a handoff. It does not end when only scaffolding or a plan exists.

The [critical review](CRITICAL_REVIEW.md) records architecture and run-plan defects found before implementation, their corrections, and the remaining external decisions.

## How to use a run file

1. Work through the files in numeric order. Read this file, the chosen run file, its listed dependencies, and only the relevant source/design files.
2. Inspect the current repository before editing. The paths in these files are target contracts; use the established path if an earlier run chose an equivalent structure and recorded it.
3. Implement only the run's scope and the small integration changes required to make it work. Do not build future runs opportunistically.
4. Run the verification listed in the file plus the repository's shared checks. Record commands, results, limitations, and changed contracts in a handoff using [HANDOFF_TEMPLATE.md](HANDOFF_TEMPLATE.md).
5. Mark the run complete in [PROGRESS.md](PROGRESS.md) only after its exit criteria pass. Carry unresolved work into a named follow-up; do not silently mark it done.

Use synthetic fixtures to verify contracts and edge cases, but never report synthetic success as real-sketch accuracy. The repository currently contains the spec and UI design reference, but no labeled engineering-sketch dataset and no Git repository. Run 00 records these facts and establishes the development baseline. Real-image quality gates in runs 17 and 20 remain open until consented drawings are available.

## Sequence

| Run | File | Result | Architecture phase |
|---|---|---|---|
| 00 | [Foundation and evidence](00-foundation-and-evidence.md) | Reproducible workspace, fixture registry, evaluation definitions | 0 |
| 01 | [Scene contract](01-scene-contract.md) | Versioned semantic schema and validators | 1 |
| 02 | [SVG renderer](02-svg-renderer.md) | Pure, safe scene-to-SVG and preview path | 1 |
| 03 | [Supabase persistence](03-supabase-persistence.md) | Migrations, repositories, revision transactions | 1 |
| 04 | [Upload and job API](04-upload-and-jobs.md) | Upload, queue, worker lifecycle, status API | 1 |
| 05 | [Web foundation](05-web-foundation.md) | Upload/list/status and fixture review shell | 1 |
| 06 | [Page normalization](06-page-normalization.md) | Safe decode, orientation, rectification, transforms | 2 |
| 07 | [Masks and regions](07-masks-and-regions.md) | Grid/color masks and protected candidate regions | 2 |
| 08 | [Centerlines and primitives](08-centerlines-and-primitives.md) | Stroke skeletons and fitted route primitives | 2 |
| 09 | [Axis inference and snapping](09-axis-snapping.md) | Evidence-backed isometric snapping | 2 |
| 10 | [Topology](10-topology.md) | Graph hypotheses and unresolved crossings | 2 |
| 11 | [Handwriting OCR](11-handwriting-ocr.md) | Text crops, alternatives, vocabulary normalization | 3 |
| 12 | [Symbol candidates](12-symbol-candidates.md) | Profile library and bounded symbol classification | 3 |
| 13 | [Dimensions and associations](13-dimensions-associations.md) | Structured dimensions and note targets | 3 |
| 14 | [Pipeline integration](14-pipeline-integration.md) | Candidate outputs assembled into validated revisions | 3 |
| 15 | [Review editor](15-review-editor.md) | Semantic correction, revision history, final export | 3 |
| 16 | [Vision ambiguity lane](16-vision-ambiguity.md) | Optional constrained LLM/Vision suggestions | 4 |
| 17 | [Evaluation and calibration](17-evaluation-calibration.md) | Held-out metrics and calibrated review policy | 5 |
| 18 | [Security and privacy](18-security-privacy.md) | Auth, authorization, retention, secret boundaries | 5 |
| 19 | [Deployment and operations](19-deployment-operations.md) | Staging deployment, migrations, telemetry, recovery | 5 |
| 20 | [Release verification](20-release-verification.md) | End-to-end acceptance and release record | 5 |

Runs 00–05 establish a working vertical slice before image interpretation. Runs 06–14 add deterministic extraction, OCR, and scene assembly. Run 15 completes human correction. Run 16 adds optional vision interpretation. Runs 17–20 determine whether the product is safe and ready to release. Phase 6 expansion from the architecture is intentionally outside this first-release sequence; it needs separate bounded runs after the initial profile has measured results.

## Shared contracts for every run

- **Coordinates:** rectified page pixels for scene geometry; immutable-input pixels before EXIF for source evidence. Preserve both transforms and label every stage's coordinate space.
- **Authority:** scene JSON is the saved document; SVG/PNG are derived. The LLM never provides geometry or topology.
- **Connectivity:** shared endpoint node IDs and symbol ports are the only scene connectivity source; pixel overlap is insufficient.
- **State:** job processing state, revision review state, and immutable export records are separate.
- **Privacy:** originals, crops, provider calls, and exports are private; credentials stay server-side.
- **Review:** unknown is valid; uncertain connectivity or engineering meaning is never silently confirmed.
- **Database:** Supabase Cloud hosts deployed PostgreSQL; FastAPI/worker own data access. Local tests may use local PostgreSQL.
- **UI:** use `system-design` in product mode; engineering colors remain drawing data.
- **Reproducibility:** pin schema, profile, model, pipeline, symbol, prompt, and renderer versions in artifacts or job metadata as applicable. Do not treat object storage and PostgreSQL as one atomic transaction.
- **Verification:** meaningful tests for changed behavior, one end-to-end or fixture demonstration where applicable, and a concise handoff.

## Stop and handoff rules

An agent may choose routine implementation details within the architecture. If a required credential, real drawing, symbol standard, or hosting choice is absent, implement and test the adapter or contract with local fakes where possible. Record the exact missing input and the blocked acceptance item. Never fabricate a provider response, measured accuracy, or successful cloud deployment. A phase that cannot meet its exit criteria stays open in `PROGRESS.md`; later independent work may proceed against its verified contracts, but release cannot claim the blocked gate passed.

Every run's handoff must name the next run, changed APIs/schemas, fixtures or data used, tests executed, remaining risks, and any decision that changes the architecture. Use the [handoff template](HANDOFF_TEMPLATE.md).
