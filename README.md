# Isometric sketch conversion workspace

This repository is the foundation for converting single-page piping-isometric sketches into an editable semantic scene and SVG. Run 00 establishes packages, checks, and an evidence registry. It does not recognize images or make accuracy claims. The [implementation sequence](implementation-phases/README.md) defines later work.

## Native setup

Install Python **3.12.12**, Node **26.0.0**, and pnpm **10.23.0**. On a fresh checkout, run:

```sh
./scripts/setup
./scripts/check
```

`setup` creates `.venv`, installs pinned Python development dependencies from `requirements-dev.lock`, and installs the pnpm workspace from `pnpm-lock.yaml`. Run 03 checks require `LOCAL_DATABASE_URL` (see [persistence](docs/persistence.md)). Keep environment values in an untracked `.env`; `.env.example` documents names only.

Individual checks:

```sh
./scripts/test-api
./scripts/test-pipeline
./scripts/test-web
```

`./scripts/check` also runs Ruff lint and format checks. GitHub Actions runs the same setup and check scripts on `main`. The Git remote is `https://github.com/moizk678/isometric.git`; hosted CI run [36176905064](https://github.com/moizk678/isometric/actions/runs/36176905064) passed on commit `eaf84d8` (Check workflow).

## Layout and data

The [DrawingScene contract](docs/scene-contract.md) documents coordinate spaces, invariants, issue codes, and schema tooling for Run 01. The [SVG renderer](docs/svg-renderer.md) documents deterministic export, preview rasterization, symbol IDs, and golden checks for Run 02.

The [persistence layer](docs/persistence.md) documents PostgreSQL migrations, artifact storage, revision publishing, and local database setup for Run 03.

`apps/web` is the future Next.js workbench; `services/api` and `services/worker` are future Python services; `packages/pipeline` and `packages/evaluation` hold shared conversion and evidence code. `profiles`, `supabase/migrations`, and `infra/local` are reserved for their later bounded runs. No placeholder service currently listens on a port.

The [dataset contract](packages/evaluation/datasets/README.md), [labeling rules](packages/evaluation/datasets/LABELING_GUIDE.md), and [metric definitions](packages/evaluation/datasets/METRICS.md) guide future evaluation. Four tiny images in `packages/evaluation/fixtures/synthetic` are generated contract fixtures, never real-sketch accuracy evidence. The [data inventory](docs/DATA_INVENTORY.md) records two **unlabeled** real samples kept privately and out of Git. Do not commit `.private/`, source crops, secrets, or real drawings.
