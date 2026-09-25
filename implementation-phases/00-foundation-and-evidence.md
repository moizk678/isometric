# Run 00 — Foundation and evidence registry

**Agent brief:** Establish a reproducible development workspace and the evidence contract for later CV work. This run does not implement image interpretation.

**Depends on:** [architecture](../implementation_architecture.md), [spec](../hand_drawn_to_svg_system_spec.md), and the current repository contents. There is no prior implementation run.

## Build

1. Inspect the workspace, record the available runtimes, and establish version control if it is still absent. Scaffold `apps/web`, `services/api`, `services/worker`, `packages/pipeline`, `packages/evaluation`, `profiles`, `supabase/migrations`, and `infra/local` without generating unused application features.
2. Set package/runtime versions, a root `Makefile` or equivalent with `check`, `test-api`, `test-pipeline`, and `test-web` commands, formatting/lint configuration, and a small CI workflow. Tests may initially be smoke checks but must actually run.
3. Create a configuration contract (`.env.example`) with names and descriptions only. Keep credentials out of source control. Distinguish local PostgreSQL from Supabase staging/production URLs, artifact storage, queue, and optional vision provider settings.
4. Add `packages/evaluation/datasets/manifest.schema.json` and a manifest template with drawing ID, rights/consent, source type, profile, difficulty tags, split, annotation URI, and checksum. Write concise labeling rules for route centerlines, crossing vs junction, symbols, text, dimensions, and unknown marks.
5. Add a few **synthetic** fixtures for transforms, connected/disconnected crossings, note crops, and dimensions. Do not present them as real engineering drawings. Inventory any real drawings available to the project; `system-design/reference.jpg` is a UI reference, not a sketch sample. Keep real drawings in private, access-controlled, untracked storage with recorded consent and deletion owner.
6. Record unresolved dependencies in a short `docs/architecture-decisions/000-initial-assumptions.md`: drawing samples, organization symbol convention, OCR/provider credentials, artifact bucket/queue host, API/worker host, and auth provider.

## Deliverables

- Reproducible install and shared check commands documented in root `README.md`.
- Initial repo skeleton and CI smoke check.
- Dataset manifest/schema, labeling guide, synthetic fixtures, and explicit data inventory.
- No secrets or actual source drawings committed without permission/consent.

## Exit checks

- Fresh checkout/install instructions run cleanly on a developer machine or documented container.
- Shared `check` command passes; CI runs the same command.
- Manifest accepts valid fixture entries and rejects missing checksum, split, or consent fields.
- Data inventory truthfully says whether a real, labeled piping sketch exists.
- No real drawing or crop appears in Git, CI logs, or a public artifact location.

## Out of scope and handoff

Do not choose OCR/vision models or claim accuracy. Hand off runtime versions, commands, package paths, available datasets, and any blocked real-data gate to [Run 01](01-scene-contract.md).
