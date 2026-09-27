-- Append-only processing log lines for live job progress in the UI.

CREATE TABLE drawing.job_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid NOT NULL REFERENCES drawing.jobs (id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  level text NOT NULL,
  stage text,
  message text NOT NULL,
  detail jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT job_logs_level_check CHECK (level IN ('info', 'warning', 'error'))
);

CREATE INDEX job_logs_job_id_created_at_id_idx
  ON drawing.job_logs (job_id, created_at, id);

ALTER TABLE drawing.job_logs ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE drawing.job_logs FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON TABLE drawing.job_logs FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON TABLE drawing.job_logs FROM authenticated;
  END IF;
END
$$;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
    EXECUTE 'GRANT ALL ON TABLE drawing.job_logs TO postgres';
  END IF;
END
$$;
