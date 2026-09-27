# Review editor (Run 15)

Human reviewers apply **semantic edits** through the API. The server validates the scene, regenerates SVG/preview exports, and publishes a new revision with optimistic concurrency.

## Concurrency

All mutation endpoints require an **`If-Match`** header set to the parent revision UUID. A stale parent returns HTTP **409** (`revision_conflict`). Edits and resolves must target the document **current** revision.

## Edit commands

`POST /api/v1/documents/{id}/revisions/{rid}/edits`

```json
{
  "commands": [
    { "type": "update_annotation_text", "objectId": "…", "normalizedText": "6 in" },
    { "type": "disconnect_pipe_endpoint", "pipeId": "…", "endpoint": "end" }
  ]
}
```

Supported `type` values: `update_annotation_text`, `move_annotation`, `set_symbol_type`, `set_symbol_rotation`, `move_junction`, `connect_pipe_endpoint`, `connect_symbol_port`, `disconnect_pipe_endpoint`, `disconnect_symbol_port`, `set_layer_color`, `set_dimension_text`.

Implementation: [`packages/pipeline/isometric_pipeline/scene/edits/`](../packages/pipeline/isometric_pipeline/scene/edits/).

## Review resolution

`POST /api/v1/documents/{id}/revisions/{rid}/review-items/{item_id}/resolve`

Body: `{ "action": "confirm" | "correct" | "acknowledge_unknown", "correction": { "commands": […] } }` (correction required for `correct`).

Resolution writes `review_events` and carries forward unrelated open items under stable `issue_key` values.

## Adopt reprocess candidate

`POST /api/v1/documents/{id}/revisions/{rid}/adopt` with `{ "candidate_revision_id": "…" }` promotes a machine candidate to `current_revision_id`. The response lists **lost confirmed edits** if the candidate diverges from the reviewed scene.

## Reprocess and confirmed pins

When reprocess does not advance the current pointer, assembly overlays objects with `interpretation.state == confirmed` from the reviewed current scene onto the new candidate ([`overlay_confirmed_objects`](../packages/pipeline/isometric_pipeline/review/overlay.py)).

## Export labeling

`review_state` on the revision is `ready` only when no blocking open/acknowledged items remain (critical/high severity). The workbench labels SVG download as **draft** until `ready`.

## Undo

There is no separate undo stack: open an earlier revision and publish a new child revision from it (same CAS rules).
