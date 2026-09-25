# Migrations

Versioned SQL for Supabase Cloud and local PostgreSQL. Apply with `./scripts/migrate-replay` locally or controlled CI after a clean replay.

Staging applies before production. Prefer forward-fix migrations over rollback unless a migration is explicitly backward compatible.
