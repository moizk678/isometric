-- Run 04: job leases, cancellation, and per-owner upload idempotency.

ALTER TABLE drawing.documents
  ADD COLUMN upload_options_hash text;

ALTER TABLE drawing.jobs
  ADD COLUMN cancel_requested boolean NOT NULL DEFAULT false,
  ADD COLUMN lease_token uuid,
  ADD COLUMN lease_expires_at timestamptz;

ALTER TABLE drawing.documents
  DROP CONSTRAINT IF EXISTS documents_upload_idempotency_key_unique;

CREATE UNIQUE INDEX documents_owner_upload_idempotency_key_idx
  ON drawing.documents (owner_id, upload_idempotency_key)
  WHERE upload_idempotency_key IS NOT NULL;

CREATE INDEX jobs_document_id_created_at_idx
  ON drawing.jobs (document_id, created_at DESC);
