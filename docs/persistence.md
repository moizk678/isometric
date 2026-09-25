# Persistence and artifacts (Run 03)

PostgreSQL holds jobs, revisions, review metadata, and outbox events. Immutable scene and export bytes live in an `ArtifactStore`. The API and worker connect with server-side URLs only; the browser never receives database credentials.

## Schema

Versioned SQL lives in [`supabase/migrations/`](../supabase/migrations/). Application tables are in the `drawing` schema with row-level security enabled and Supabase Data API roles revoked when present.

## Environment

| Variable | Purpose |
|---|---|
| `SUPABASE_DATABASE_URL` | Direct Postgres URL for the Supabase Cloud project (development, tests, CI) |
| `SUPABASE_DEVELOPMENT_DATABASE_URL` | Optional alias when `SUPABASE_DATABASE_URL` is unset |
| `ARTIFACT_ROOT` | Filesystem root for `FilesystemArtifactStore` (default `.private/artifacts`) |
| `ARTIFACT_*` | S3-compatible production storage (adapter not implemented in Run 03) |

Use the **direct** connection string from the Supabase dashboard (Session mode or direct host), not the Data API URL. Keep it in an untracked `.env`; see [`.env.example`](../.env.example).

## Commands

```sh
./scripts/setup-env   # prompts for DB password; writes .env and apps/web/.env.local
# or: SUPABASE_DB_PASSWORD='…' ./scripts/setup-env

./scripts/migrate-replay
./scripts/bootstrap-migrations   # once if schema was applied outside migrate-replay
./scripts/test-persistence
./scripts/seed-persistence
```

`./scripts/check` runs migration replay and persistence tests when `SUPABASE_DATABASE_URL` (or the development alias) is set.

Optional local Postgres via Docker (`infra/local/`) is not used by default; all scripts and tests target Supabase Cloud.

## Publishing contract

1. Register a short-lived `publication_intents` row listing artifact keys.
2. Write and checksum scene/export artifacts (immutable keys).
3. In one transaction: insert revision and export rows, carry review items if requested, compare-and-swap `documents.current_revision_id`, delete the intent.

Stale parent revision IDs return `revision_conflict` (HTTP 409 in Run 04). Failed database commits leave reclaimable orphan artifacts; the reconciler dry-run lists keys not referenced by the database after publication intents expire.

## Migrations and deployment

Apply migrations with `./scripts/migrate-replay` against the development Supabase project, then staging, then production through CI. Prefer forward-fix migrations over rollback unless a migration is explicitly backward compatible.

## Production blockers

- S3-compatible `ArtifactStore` requires `ARTIFACT_ENDPOINT` and `ARTIFACT_BUCKET`; the interface is tested with the filesystem adapter only until Run 19.

## CI

GitHub Actions `Check` expects repository secret `SUPABASE_DATABASE_URL` pointing at the same development project (or a dedicated CI database).
