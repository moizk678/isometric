-- Run 03: drawing persistence schema (server-only access).

CREATE SCHEMA IF NOT EXISTS drawing;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION drawing.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TABLE drawing.documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id text NOT NULL,
  source_hash text NOT NULL,
  source_uri text NOT NULL,
  source_mime text NOT NULL,
  source_width_px integer,
  source_height_px integer,
  upload_idempotency_key text,
  current_revision_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT documents_upload_idempotency_key_unique UNIQUE (upload_idempotency_key)
);

CREATE TABLE drawing.scene_revisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES drawing.documents (id) ON DELETE CASCADE,
  parent_revision_id uuid REFERENCES drawing.scene_revisions (id) ON DELETE RESTRICT,
  schema_version text NOT NULL,
  scene_uri text NOT NULL,
  scene_checksum_sha256 text NOT NULL,
  author_type text NOT NULL,
  review_state text NOT NULL,
  validation_status text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE drawing.documents
  ADD CONSTRAINT documents_current_revision_id_fkey
  FOREIGN KEY (current_revision_id) REFERENCES drawing.scene_revisions (id)
  ON DELETE RESTRICT;

CREATE INDEX scene_revisions_document_id_created_at_idx
  ON drawing.scene_revisions (document_id, created_at DESC);

CREATE TABLE drawing.jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES drawing.documents (id) ON DELETE CASCADE,
  state text NOT NULL,
  stage text,
  attempt integer NOT NULL DEFAULT 0,
  input_hash text NOT NULL,
  options_hash text NOT NULL,
  pipeline_version text NOT NULL,
  profile_version text NOT NULL,
  result_revision_id uuid REFERENCES drawing.scene_revisions (id) ON DELETE RESTRICT,
  error_code text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT jobs_result_revision_id_unique UNIQUE (result_revision_id)
);

CREATE INDEX jobs_state_created_at_idx ON drawing.jobs (state, created_at);

CREATE TABLE drawing.outbox_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type text NOT NULL,
  aggregate_id uuid NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  publish_state text NOT NULL DEFAULT 'pending',
  attempt_count integer NOT NULL DEFAULT 0,
  event_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz,
  CONSTRAINT outbox_events_event_key_unique UNIQUE (event_key)
);

CREATE INDEX outbox_events_publish_state_created_at_idx
  ON drawing.outbox_events (publish_state, created_at);

CREATE TABLE drawing.stage_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid NOT NULL REFERENCES drawing.jobs (id) ON DELETE CASCADE,
  stage text NOT NULL,
  status text NOT NULL,
  input_hash text NOT NULL,
  producer_version text NOT NULL,
  artifact_uri text,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX stage_runs_job_id_stage_idx ON drawing.stage_runs (job_id, stage);

CREATE TABLE drawing.review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_key text NOT NULL,
  revision_id uuid NOT NULL REFERENCES drawing.scene_revisions (id) ON DELETE CASCADE,
  object_id text,
  relationship_id text,
  issue_type text NOT NULL,
  severity text NOT NULL,
  crop_uri text,
  proposed_options jsonb NOT NULL DEFAULT '[]'::jsonb,
  state text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX review_items_revision_id_idx ON drawing.review_items (revision_id);
CREATE INDEX review_items_issue_key_idx ON drawing.review_items (issue_key);

CREATE TABLE drawing.review_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_key text NOT NULL,
  source_revision_id uuid NOT NULL REFERENCES drawing.scene_revisions (id) ON DELETE RESTRICT,
  result_revision_id uuid NOT NULL REFERENCES drawing.scene_revisions (id) ON DELETE RESTRICT,
  old_value jsonb,
  new_value jsonb,
  actor_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE drawing.exports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  revision_id uuid NOT NULL REFERENCES drawing.scene_revisions (id) ON DELETE CASCADE,
  kind text NOT NULL,
  uri text NOT NULL,
  checksum_sha256 text NOT NULL,
  renderer_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT exports_revision_kind_unique UNIQUE (revision_id, kind)
);

CREATE TABLE drawing.interpretation_calls (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid NOT NULL REFERENCES drawing.jobs (id) ON DELETE CASCADE,
  crop_id text NOT NULL,
  provider text NOT NULL,
  model text NOT NULL,
  prompt_version text NOT NULL,
  request_uri text NOT NULL,
  response_uri text,
  outcome text NOT NULL,
  latency_ms integer,
  token_usage jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE drawing.publication_intents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES drawing.documents (id) ON DELETE CASCADE,
  expected_parent_revision_id uuid REFERENCES drawing.scene_revisions (id) ON DELETE RESTRICT,
  artifact_keys text[] NOT NULL DEFAULT '{}',
  grace_until timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX publication_intents_grace_until_idx
  ON drawing.publication_intents (grace_until);

CREATE INDEX documents_owner_id_created_at_idx
  ON drawing.documents (owner_id, created_at DESC);

CREATE TRIGGER documents_set_updated_at
  BEFORE UPDATE ON drawing.documents
  FOR EACH ROW
  EXECUTE FUNCTION drawing.set_updated_at();

CREATE TRIGGER jobs_set_updated_at
  BEFORE UPDATE ON drawing.jobs
  FOR EACH ROW
  EXECUTE FUNCTION drawing.set_updated_at();

ALTER TABLE drawing.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE drawing.scene_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE drawing.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE drawing.outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE drawing.stage_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE drawing.review_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE drawing.review_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE drawing.exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE drawing.interpretation_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE drawing.publication_intents ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON SCHEMA drawing FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA drawing FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON ALL TABLES IN SCHEMA drawing FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON ALL TABLES IN SCHEMA drawing FROM authenticated;
  END IF;
END
$$;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
    EXECUTE 'GRANT USAGE ON SCHEMA drawing TO postgres';
    EXECUTE 'GRANT ALL ON ALL TABLES IN SCHEMA drawing TO postgres';
    EXECUTE 'GRANT ALL ON ALL SEQUENCES IN SCHEMA drawing TO postgres';
  END IF;
END
$$;
