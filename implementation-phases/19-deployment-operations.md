# Run 19 — Staging deployment, observability, and recovery

**Agent brief:** Deploy the tested system to staging with Supabase Cloud PostgreSQL and prove that jobs, migrations, telemetry, and recovery work in the real topology.

**Depends on:** [Runs 03–04 and 14–18](18-security-privacy.md). Deployment host, artifact bucket, queue, and Supabase staging credentials must be available.

## Build

1. Provision/configure staging API, worker, queue, private artifact bucket, and a dedicated Supabase Cloud PostgreSQL project. Verify network connection mode (direct where supported; session pooler when needed), TLS, bounded pools, and secret storage.
2. Apply `supabase/migrations` through controlled CI after local replay. Exercise a fresh staging database and document a production migration procedure with forward-fix/rollback decision rules.
3. Add structured logs and traces joining API request, job, stage run, scene revision, and provider call IDs. Export metrics for queue depth, stage duration/failure, unresolved items, export failures, provider cost/latency, and connection pool pressure.
4. Configure alerts for stalled jobs, repeated failures, outbox backlog, queue backlog, database connectivity, orphan artifacts, and invalid exports. Create a runbook for retry/dead-letter, outbox replay, artifact reconciliation, worker restart, migration failure, and provider outage.
5. Test backup/restore or recovery procedure appropriate to the selected Supabase plan and artifact store. Run a staging upload→review→export and worker-crash/retry exercise.

## Deliverables

- Staging deployment configuration, CI migration job, dashboards/alerts, runbooks, and recovery evidence.

## Exit checks

- A real staging upload reaches a reviewable scene and export without manual database intervention.
- Worker crash and provider outage do not lose the original or overwrite a reviewed revision.
- A crash between job transaction and queue send is recovered through the outbox; orphan artifact cleanup cannot delete referenced revisions.
- Migrations, secrets, signed artifacts, metrics, alerts, and recovery procedure are verified in staging.
- A second deployment with no schema changes is safe and repeatable.
- Missing cloud credentials or hosting choices leave the run open; local mocks are not staging proof.

## Out of scope and handoff

Do not announce release readiness merely because staging is live. Hand off deployment IDs, migration version, dashboards, recovery results, and open operational risks to [Run 20](20-release-verification.md).
