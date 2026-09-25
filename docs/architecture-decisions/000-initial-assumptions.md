# ADR 000 — Initial assumptions and missing inputs

**Status:** baseline record for Run 00, 2026-09-25.

- **Development:** Native Python 3.12.12, Node 26.0.0, pnpm 10.23.0. Run 00 needs no Docker or live services. Git is local; no remote CI execution is verified.
- **Real samples:** Two user-supplied PNGs are locally available, approved by the user for project use, deliberately untracked, and unlabeled. Original provenance and rights-holder details remain to be verified. The project owner owns deletion. A consented, reviewed, representative dataset and engineering reviewer are still needed for Run 17.
- **Symbol convention:** No organization-specific piping symbol standard has been supplied. Do not infer one from two images.
- **OCR and optional vision:** No model or provider selected; credentials and external-call policy are not supplied. Keep the optional vision lane disabled.
- **Persistence and jobs:** Supabase staging/production URLs, private artifact bucket, durable queue host, and credentials are not supplied. Later runs may use local adapters without claiming cloud verification.
- **Hosts and auth:** API/worker deployment targets and authentication provider are undecided. No browser-to-database access is assumed.

These are unresolved inputs, not reasons to fabricate data or block the scene-contract work in Run 01.
