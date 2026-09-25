# Run 18 — Authentication, authorization, and data privacy

**Agent brief:** Secure the existing workflow without changing recognition behavior. This run requires an explicit product auth/retention decision if those choices remain open.

**Depends on:** [Runs 03–05 and 15–17](17-evaluation-calibration.md). Read architecture sections 6–7 and 10.

## Build

1. Implement the selected authentication provider and map identities to document ownership/organization membership. FastAPI authorizes every document, job, scene, review item, crop, and export operation; worker credentials remain separate.
2. Keep browser access through FastAPI only. Use least-privilege database roles/connections for the deployed Supabase PostgreSQL project; do not expose privileged database URLs or keys in frontend bundles. Disable unused database Data API access or secure any intentionally exposed schema with explicit grants and policies.
3. Implement private artifact access with short-lived signed URLs or authenticated streaming. Verify IDs and paths cannot cross tenant boundaries. Add upload signature/size/decode limits and safe SVG export checks at the API boundary.
4. Implement a documented retention and deletion workflow for originals, stage artifacts, crops, interpretation calls, revisions, and exports. Preserve audit records only as the approved policy requires.
5. Add security tests for cross-user access, guessed object IDs, stale signed URLs, malformed upload, SVG injection text, secret leakage, and provider crop minimization.

## Deliverables

- Auth/authorization middleware and tests, data-access policy, deletion/retention jobs, secret boundary review, and privacy decision record.

## Exit checks

- All document-scoped endpoints deny another user's data; worker-only actions are inaccessible to browsers.
- Private artifacts cannot be fetched with guessed IDs or expired links.
- No database/provider secret appears in frontend output or routine logs.
- Deletion and retention behavior is tested against a fixture document, including dependent artifacts.
- If auth provider or retention policy is undecided, keep the run open with the specific decision recorded.

## Out of scope and handoff

Do not deploy to production in this run. Hand off auth setup, secrets inventory, data lifecycle, and security test results to [Run 19](19-deployment-operations.md).
