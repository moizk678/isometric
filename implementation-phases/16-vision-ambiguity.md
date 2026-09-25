# Run 16 — Optional LLM/Vision ambiguity lane

**Agent brief:** Add a constrained interpretation adapter for ambiguous crops. The provider must not generate geometry, dimensions, topology, or SVG.

**Depends on:** [Runs 11–15](15-review-editor.md), especially candidate schemas, review items, and user-correction precedence. Read architecture section 4.

## Build

1. Define a strict request/response schema for text alternatives, symbol label ranking, or annotation-target ranking. Requests contain bounded crop references, enumerated candidate IDs/labels, nearby OCR text, and profile context. Responses contain only a selected supplied candidate ID, evidence, uncertainty, supplied alternative IDs, or `unknown`—no coordinate/path fields. Annotation-target ranking uses supplied target IDs in its own request kind.
2. Add a provider-neutral adapter and one configured LLM/Vision API implementation. Validate returned JSON locally with extra fields forbidden. Reject unknown labels/IDs, invalid JSON, geometry-like fields, or claims unsupported by the submitted candidate list.
3. Invoke only for thresholded ambiguity after OCR, topology, and local symbol candidates exist. Add per-job crop budget, timeout, bounded retry/backoff, concurrency cap, policy opt-out, and provider version/prompt version metadata.
4. Send minimum cropped image content, strip unrelated filenames/context, and keep credentials and raw payloads out of logs. Persist private request/response references and cost/latency metadata according to retention policy.
5. Treat suggestions as candidate evidence. Do not overwrite a confirmed review decision, auto-connect a crossing, or change a coordinate. On provider failure, keep the deterministic scene and review item usable. Use only synthetic or explicitly approved crops for live-provider testing before Run 18 privacy controls are complete.

## Deliverables

- Provider adapter and configured implementation, strict schemas, invocation policy, privacy settings, and fake-provider tests.

## Exit checks

- Malicious/invalid provider output with SVG, points, dimensions, free-form object IDs, or candidate IDs absent from the request is rejected.
- Disabling the provider yields the same geometry and usable review workflow as before this run.
- A timeout or quota error produces a recorded fallback, not a failed whole job.
- A user-confirmed correction stays authoritative on reprocess.
- A bounded live invocation with an approved synthetic crop is verified before claiming the vision feature active. If credentials or policy are missing, record the live-integration gate as open; later deterministic work may proceed with the feature disabled.

## Out of scope and handoff

Do not use provider self-confidence as calibrated truth or send whole pages by default. Hand off provider configuration, prompt version, call budget, fallbacks, and open live verification to [Run 17](17-evaluation-calibration.md).
