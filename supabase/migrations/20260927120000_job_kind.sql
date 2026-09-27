-- Drawing reading jobs run beside pipeline jobs.

ALTER TABLE drawing.jobs
  ADD COLUMN kind text NOT NULL DEFAULT 'pipeline';

CREATE INDEX jobs_document_id_kind_created_at_idx
  ON drawing.jobs (document_id, kind, created_at DESC);
