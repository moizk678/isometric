-- Run 05 W1A: persist upload filename and profile on documents.

ALTER TABLE drawing.documents
  ADD COLUMN original_filename text,
  ADD COLUMN profile_id text;
