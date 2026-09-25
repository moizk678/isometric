# Run 03 — Supabase PostgreSQL persistence and artifact contract

**Agent brief:** Implement the database and immutable artifact layer used by jobs and revisions. Supabase Cloud hosts deployed PostgreSQL; this run does not deploy the application.

**Depends on:** [Runs 01–02](01-scene-contract.md). Read architecture section 6 and its Supabase deployment subsection.

## Build

1. Write versioned SQL migrations in `supabase/migrations` for documents, jobs, outbox events, stage runs, scene revisions, review items/events, exports, and interpretation-call metadata. Give review items a stable issue key across revision snapshots. Add foreign keys, unique job-result and upload-idempotency keys, indexes for job polling and document lists, and timestamp columns.
2. Implement server-side repositories with bounded SQL connections and transactions. Write and validate immutable scene/export artifacts before inserting the revision and compare-and-swap publishing `documents.current_revision_id` in one database transaction. A stale expected revision fails without moving the pointer; unreferenced artifacts are cleaned by a reconciler.
3. Define an `ArtifactStore` interface and local filesystem adapter. Add a production S3-compatible adapter only if a bucket/provider is configured; otherwise keep a tested interface and explicit deployment blocker. Use immutable keys from architecture section 6 and SHA-256 checksums.
4. Keep database credentials on API/worker hosts. Add connection configuration for direct PostgreSQL and session pooler without coupling application code to Supabase Data API. Do not expose privileged keys to the browser.
5. Add a migration replay script and seeded test data using synthetic scene fixtures. Document staging-to-production migration order and rollback/forward-fix policy. Add an outbox repository so job creation and enqueue intent commit together. Add a dry-run artifact reconciler that reports unreferenced keys and a grace-period cleanup path that excludes in-progress publications.

## Deliverables

- Tested migrations, repository interfaces/implementations, artifact store, and connection configuration.
- A small local integration environment for PostgreSQL. Cloud verification uses a Supabase project only when credentials are available.

## Exit checks

- Migrations apply cleanly to an empty local database and rerun without drift.
- Creating a revision writes artifacts before moving the current pointer; injected storage failure leaves the prior revision current, while injected database failure leaves only a reclaimable orphan artifact.
- Concurrent edits with the same expected parent result in one success and one conflict.
- Artifact checksum mismatch is detected; original and prior revision keys are never overwritten.
- Job row and outbox event are committed together, with a unique event key.
- Reconciler identifies an injected orphan while leaving referenced originals/revisions untouched.
- Review-item snapshots retain the same issue key across a new revision.
- State whether a real Supabase Cloud connection was tested. Lack of credentials does not count as a passing cloud test.

## Out of scope and handoff

Do not implement upload routes or jobs. Hand off repository APIs, migration commands, required environment variables, and cloud-test status to [Run 04](04-upload-and-jobs.md).
