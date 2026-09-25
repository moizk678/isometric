# Implementation progress

Update this file after a run's exit criteria pass. `planned` is not `complete`; record blocked gates explicitly.

| Run | Status | Handoff | Key blocker or note |
|---|---|---|---|
| 00 | complete | [handoff](00-HANDOFF.md) | Local and hosted CI verified (`eaf84d8`, run `36176905064`); two real samples are untracked and unlabeled. |
| 01 | complete | [handoff](01-HANDOFF.md) | Scene contract v1.0 in CI; review events and profile tolerances deferred. |
| 02 | complete | [handoff](02-HANDOFF.md) | SVG renderer and goldens verified locally and on hosted CI (`c08ea37`, run `36183166119`). |
| 03 | complete | [handoff](03-HANDOFF.md) | Migrations, repositories, and artifact store verified locally; cloud migration on project `bhezwfoifroyidfwdvcy`. |
| 04 | complete | [handoff](04-HANDOFF.md) | Upload/jobs API exit checks: lease recovery, idempotent revision per job, error classes, progress/review_state; `./scripts/test-api` passes. |
| 05 | complete | [handoff](05-HANDOFF.md) | Upload, job, and review UI verified by `./scripts/check` with 26 Playwright tests (keyboard, touch, 1440/390/320/200% zoom, upload retry, axe); `/display` is an EXIF stand-in until Run 06. |
| 06 | complete | [handoff](06-HANDOFF.md) | `normalize_page` stage, document display/page artifacts, `/display` cache + EXIF fallback; fixture scene publish unchanged. |
| 07 | complete | [handoff](07-HANDOFF.md) | `separate_masks` + `detect_regions`, mask/region artifacts; fixture scene publish unchanged. |
| 08 | complete | [handoff](08-HANDOFF.md) | `extract_centerlines` + `fit_primitives`, `centerlines.json` / `primitives.json`; fixture scene publish unchanged. |
| 09 | complete | [handoff](09-HANDOFF.md) | `snap_primitives`, `axes.json` / `snapped-primitives.json`; fixture scene publish unchanged. |
| 10 | complete | [handoff](10-HANDOFF.md) | `infer_topology`, `topology.json`; fixture scene publish unchanged. |
| 11 | complete | [handoff](11-HANDOFF.md) | `transcribe_regions`, `text-candidates.json`; TrOCR + FakeOCR in CI; accuracy unmeasured on real handwriting. |
| 12 | complete | [handoff](12-HANDOFF.md) | `classify_symbol_regions`, `symbol-candidates.json`; template + Fake classifier in CI; per-class accuracy unmeasured on real drawings. |
| 13 | complete | [handoff](13-HANDOFF.md) | `associate_markup`, `association-candidates.json`; synthetic fixtures in CI; real-drawing association accuracy unmeasured. |
| 14 | planned | — | |
| 15 | planned | — | |
| 16 | planned | — | Provider credentials/policy required for live invocation. |
| 17 | planned | — | Held-out real dataset required for accuracy claims. |
| 18 | planned | — | Auth provider and retention policy must be chosen. |
| 19 | planned | — | Deployment target and credentials required for cloud checks. |
| 20 | planned | — | Release requires real-drawing evidence and staging verification. |
