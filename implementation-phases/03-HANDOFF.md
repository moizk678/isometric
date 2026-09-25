# Run handoff — 03 Supabase persistence

**Run file:** `implementation-phases/03-supabase-persistence.md`
**Status:** complete locally; cloud migration applied to Supabase project `isometric` (`bhezwfoifroyidfwdvcy`).
**Next run:** `04-upload-and-jobs.md`

## Delivered

- **Migrations:** [`supabase/migrations/20260925203821_drawing_schema.sql`](../supabase/migrations/20260925203821_drawing_schema.sql) — `drawing` schema tables, indexes, RLS, Supabase role revokes.
- **Persistence package:** [`packages/persistence/isometric_persistence/`](../packages/persistence/isometric_persistence/) — pool config, `FilesystemArtifactStore`, `RevisionPublisher`, job/outbox repository, reconciler, migration replay helper.
- **Scripts:** `./scripts/migrate-replay`, `./scripts/test-persistence`, `./scripts/seed-persistence`.
- **Local infra:** [`infra/local/docker-compose.yml`](../infra/local/docker-compose.yml) (Postgres 17).
- **Docs:** [`docs/persistence.md`](../docs/persistence.md).

## Contract changes

- **Supabase dev project:** `isometric` in Enubix's Org, region `ap-southeast-1`, ref `bhezwfoifroyidfwdvcy` ($0/month). Do not reuse `Enubix-ATSProject`.
- **Env:** `SUPABASE_DEVELOPMENT_DATABASE_URL` added to `.env.example` (direct URL, server-side only).
- **CI:** GitHub Actions `Check` job runs Postgres 17 service and requires `LOCAL_DATABASE_URL`.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/migrate-replay` | Pass | Clean apply + no-op second pass via `public.schema_migrations` checksums. |
| `./scripts/test-persistence` | Pass | 10 Run 03 exit-check tests. |
| `./scripts/check` | Pass | Ruff, scene schema, render goldens, API/pipeline/web/persistence. |
| Supabase Cloud migration | Pass | `drawing_schema` applied via MCP to project `bhezwfoifroyidfwdvcy`. |
| Hosted CI (`Check`) | Pass | Run [`36189876699`](https://github.com/moizk678/isometric/actions/runs/36189876699) on `1ed76af`, pushed together with Run 03 commit `fe4a055`; Postgres 17 service, full `./scripts/check`. |

## Data used

- Synthetic scene fixture `packages/scene-schema/fixtures/valid/annotation.json` for seed and tests only.

## Remaining work and risks

- **S3 artifact adapter:** interface stub only; production needs `ARTIFACT_*` and implementation (Run 19).
- **Cloud integration tests:** require `SUPABASE_DEVELOPMENT_DATABASE_URL` in a private `.env`; not run in CI.
- **Run 04:** upload routes, queue dispatcher, and worker still out of scope.

## Next-run starting point

- Read [`docs/persistence.md`](../docs/persistence.md).
- **Repositories:** `JobRepository.create_with_outbox`, `RevisionPublisher.publish`, `DocumentRepository`.
- **Migrations:** `./scripts/migrate-replay` with `LOCAL_DATABASE_URL`.
- **Artifacts:** `FilesystemArtifactStore` under `ARTIFACT_ROOT`.

## Commands

```sh
export LOCAL_DATABASE_URL=postgresql://isometric:isometric@localhost:5432/isometric
docker compose -f infra/local/docker-compose.yml up -d
./scripts/migrate-replay
./scripts/test-persistence
./scripts/check
```
