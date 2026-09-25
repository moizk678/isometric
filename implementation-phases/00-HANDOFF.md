# Run handoff — 00 Foundation and evidence registry

**Run file:** `implementation-phases/00-foundation-and-evidence.md`
**Status:** complete locally and on hosted CI (`origin` → `https://github.com/moizk678/isometric.git`).
**Next run:** `01-scene-contract.md`

## Delivered

- Initialized local Git and scaffolded web, API, worker, pipeline, evaluation, profile, migration, and local-infrastructure paths without application features.
- Pinned Python 3.12.12, Node 26.0.0, pnpm 10.23.0, and exact Python development dependencies. `./scripts/setup` installs; `./scripts/check` is shared with CI.
- Added dataset manifest schema and template, labeling guide, metric definitions, four generated synthetic PNG fixtures, transform/connectivity/text/dimension truth, and an explicit data inventory.
- Moved two real PNGs to access-restricted `.private/drawings/`, recorded user-stated permission and project-owner deletion responsibility, and excluded them from Git. Both are unlabeled with unassigned split.

## Contract changes

- Dataset manifest v1.0.0 requires a stable drawing ID, image URI, rights/consent record, source type, profile, tags, split, label status, annotation URI or null, and image SHA-256. Non-synthetic entries require approved consent status; unlabeled entries require a null annotation URI.
- Synthetic fixture contract v1.0.0 distinguishes connected from disconnected crossings and records raw-to-display-to-page transforms. No scene, API, database, or profile threshold contract exists yet.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| Clean virtual environment plus `./scripts/setup` | Pass | Locked Python packages and frozen pnpm workspace installed. |
| `./scripts/test-api` | Pass | API import test and worker import smoke check. |
| `./scripts/test-pipeline` | Pass | Transform composition/invertibility and six evidence tests, including required-field rejection and fixture hashes. |
| `./scripts/test-web` | Pass | Web workspace reads the shared evidence contract. |
| `./scripts/check` | Pass | Ruff lint/format and all tests. |
| Private manifest schema and SHA-256 validation | Pass | Two entries valid, hashes match, both unlabeled. |
| Git staged-file and ignore inspection | Pass | No real PNG/crop or secret staged. |
| Hosted CI | Pass | GitHub Actions run `36176905064` on `main` at commit `eaf84d8` (Check workflow: `./scripts/setup`, `./scripts/check`). |

## Data used

- Synthetic fixture version 1.0.0: four generated raster contract inputs. These establish no real-sketch accuracy.
- Two local, real, unlabeled user-supplied samples; neither was used in automated tests. `system-design/reference.jpg` remains a UI reference.

## Remaining work and risks

- Project owner: verify original sample provenance and rights-holder details before broader sharing or real-data evaluation; recruit an engineering reviewer and label a representative dataset for Run 17.
- Project owner: Supabase, artifact storage, queue, provider, deployment, auth, and organization symbol decisions remain open in ADR 000.

## Next-run starting point

- Read the schema and fixture conventions under `packages/evaluation`, then implement Run 01's Pydantic scene contract in `packages/pipeline`. Use `./scripts/setup` and `./scripts/check`; add generated scene schema/types checks to the latter. Keep the real PNGs untracked and separate from synthetic fixtures.
