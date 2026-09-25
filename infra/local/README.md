# Optional local PostgreSQL (legacy)

This Docker Compose stack is **not** used by `./scripts/check`, tests, or the default development flow. The project uses **Supabase Cloud** via `SUPABASE_DATABASE_URL` (see [docs/persistence.md](../../docs/persistence.md)).

If you still want a local Postgres instance for experiments:

```sh
docker compose -f infra/local/docker-compose.yml up -d
```

Do not point `SUPABASE_DATABASE_URL` at this container unless you intentionally replace cloud development with local Postgres.
