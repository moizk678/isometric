# Critical review of architecture and implementation runs

**Scope:** [implementation_architecture.md](../implementation_architecture.md) and all numbered files in this directory. The `system-design` files were excluded from review and not modified. This is a documentation/contract review; no application code exists yet, so no runtime behavior was claimed or tested.

## Issues found and corrected

| Severity | Issue | Correction |
|---|---|---|
| High | Job completion, drawing review readiness, and export state were mixed together. | Separate job (`queued/running/succeeded/failed/canceled`), revision (`review_required/ready`), and immutable export records in the architecture and Runs 04–05/14. |
| High | Pipe connectivity could be represented twice, by endpoint IDs and generic `connects` relationships. | Shared endpoint node IDs and named symbol ports are now the only connectivity source. Crossings remain distinct until confirmed; Runs 01/10/15 use that rule. |
| High | PostgreSQL plus object storage was described as an atomic publish. | Artifacts are written first; a conditional PostgreSQL transaction publishes references. Orphan reconciliation and failure tests are assigned to Runs 03/14/19. |
| High | A database commit could succeed while queue send failed, leaving a job stranded. | Add a transactional outbox and idempotent worker claim; Runs 03–04/19 verify crash recovery. |
| High | An edit could create a new revision without carrying unresolved review items, falsely marking it ready. | Stable issue keys and revision snapshots preserve or reevaluate review items; Run 15 tests this and critical unknowns do not unlock final export. |
| High | Reprocessing behavior did not define how reviewed edits survive. | Reprocess creates a separate machine candidate. Explicit adoption shows lost confirmed edits and requires fresh review; no automatic merge in the first release. |
| Medium | LLM/Vision example allowed an ambiguous object ID and did not constrain choice to a supplied candidate. | Provider output selects only supplied candidate IDs; geometry and free-form IDs are rejected in Run 16. |
| Medium | Raw source coordinates and browser EXIF orientation could misalign evidence overlays. | Define raw pre-EXIF source, orientation-normalized display, and rectified page spaces with invertible transforms; Runs 01/05/06 test the mapping. |
| Medium | Arc fitting was in an early run while the v1 scene/renderer supported only lines. | Initial piping profile fits straight-line routes. Curved marks remain unresolved until an arc schema and renderer are explicitly added. |
| Medium | Structural tees/elbows and explicit fitting symbols could render twice. | Structural junctions render once; separate fitting symbols require explicit evidence. |
| Medium | The API omitted document listing, private source retrieval, revision history, candidate adoption, and cancellation needed by the planned UI. | Added endpoints and corresponding Runs 04/15 checks. |
| Medium | A system could appear safe by flagging every item for review, with no useful automation. | Acceptance thresholds and review-burden limits must be approved before held-out evaluation; Runs 17/20 report both. |
| Medium | Real drawing evaluation preceded the full security run. | Runs 00/17 require consented, private, offline, access-controlled data until Run 18 protections are complete; Run 16 live tests use approved synthetic crops. |
| Low | The implementation index named the wrong real-data gate and the spec's job example used revision status. | Corrected the index and the companion spec API example. |

## Remaining external decisions and evidence

- Obtain consented, labeled piping sketches and an engineering reviewer to approve ground truth, acceptance thresholds, and review burden. Until then, Runs 17 and 20 cannot pass real-image gates.
- Choose the organization symbol convention and verify OCR on actual handwriting; synthetic tests establish only contract correctness.
- Supply Supabase staging/production, artifact store, queue, deployment-host, authentication, and optional LLM/Vision configuration when the relevant run begins. Runs can implement/test adapters locally but must leave cloud/live gates open without access.
- Decide whether the vision feature must be active at first release. Its adapter is part of the pipeline; it stays disabled if live verification or policy approval is incomplete, and the release record must say so.

## Review checks performed

- Read the architecture, implementation index/progress/handoff, and all numbered run files for dependency, data, API, revision, and acceptance consistency.
- Checked consecutive run numbering, Markdown code fences, local file links, stale contract terms, and absence of development timeline estimates.
