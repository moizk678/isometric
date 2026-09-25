# Local infrastructure

Run 03 adds PostgreSQL 17 for persistence tests:

```sh
docker compose -f infra/local/docker-compose.yml up -d
export LOCAL_DATABASE_URL=postgresql://isometric:isometric@localhost:5432/isometric
./scripts/migrate-replay
```

Artifact bytes default to `.private/artifacts` via `ARTIFACT_ROOT`. Queue adapters remain for later runs.
