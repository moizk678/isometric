# Visual principles and domain translation

**Read when:** Designing a new screen or adapting this aesthetic to another product.  
**Requires:** [Design tokens](../foundations/tokens.md), [Typography, geometry and rhythm](../foundations/typography-geometry.md)  
**Related (optional; do not automatically load):** [Responsive composition](../foundations/responsive.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

**[O]** A calm, tactile-looking operational workspace uses warm matte surfaces and soft geometry to make dense information approachable. Black anchors navigation and action; a deep-green financial summary supplies the largest visual emphasis; saturated circular signals make operational states easy to scan.

## Composition principles

- **The page is spacious at the macro level and compact inside records.** Large panels breathe; rows carry several aligned pieces of information.
- **Surface hierarchy replaces heavy borders.** A pale workspace contains white panels; panels contain warm inset tiles/rows. Separation comes from value differences and gutters.
- **Rounded geometry is systematic.** The outer frame, cards, inner cards, rows, button pills, logo pills, and circular icons form a coherent family.
- **Black means navigation/selection/action.** It is not an error state and does not require a colored brand CTA.
- **Color is concentrated.** The green feature panel is the only large saturated region. Other color is limited to status circles, miniature bars, change text, and one urgency badge.
- **Typography does the hierarchy work.** The hero number is dramatically larger than the supporting metrics; headings are modest; labels recede.
- **Numbers are intentionally light.** Do not convert all large metrics to bold. Weight is less important than scale, positioning, and whitespace.
- **Repeated shapes have repeated meaning.** Circular pale buttons are utilities, colored disks are state markers, black pills are active/primary, white pills are secondary or entity identity.
- **No visible gradients, glass blur, card drop shadows, illustrations, or ornamental backgrounds.** The photograph in the profile chip is the only photographic element.

## Content and interaction thesis [E]

The scan sequence should answer: **Where am I? → What matters now? → What needs action? → What changed?** Actions should stay beside their relevant information. Feedback should be immediate, spatially stable, and quiet. Use brief color/fill transitions, restrained overlay entry, and clear selection states; avoid staged dashboard entrances, counter roll-ups, floating cards, and scroll effects that slow work.

## Preserve roles; replace domain content

| Reference role | Invariant design behavior | Examples of appropriate substitutions |
|---|---|---|
| Revenue at risk feature | One dominant summary with current value, time context and small supporting facts | Inventory exposure, project workload, budget usage, service health; only if meaningful |
| Today metrics | Small comparable status summaries with consistent units and explicit trends | Tasks due, delivery rate, open issues, response time |
| Attention required | Actionable records with blockers/status, ownership, urgency and next step | Tickets, orders, approvals, deployments, invoices |
| Payer capsule | Secondary organization/entity identity in a white capsule | Customer, vendor, owner/team, integration |
| Approval odds | Exact metric plus compact visual supplement | Completion, confidence, capacity; omit when no honest equivalent exists |
| Review case | Specific secondary row action | Open ticket, inspect order, review request |
| Recent activity | Chronological changes in a shared inset feed | Audit events, comments, updates, sync activity |
| New Authorization | Single primary creation/next-step action | New project, add asset, create request |
| Sarah/avatar | User/account context | Real signed-in user or team identity |

Do not carry the reference's probability thresholds, risk definitions, counts, insurer marks or clinical categories into unrelated software. Keep the palette's role separation; a new brand may substitute the **paired feature greens and tiny highlight** after checking harmony/contrast, while retaining neutral surfaces and black actions. Changing every status hue and every control shape would create another design system rather than translating this one.

## Composition recipes

| Screen archetype | Composition recipe |
|---|---|
| Operational overview | Orientation + one primary action; optional feature; supporting metrics; work queue; secondary activity |
| List/search | Header + black creation action; search/filter row; neutral filter chips; one white table/list panel; clear results count and pagination |
| Record detail | Breadcrumb/back; entity title and status; primary action; wide detail content + optional 320–400px context pane; description lists, tabs and activity |
| Create/edit | Compact page title; single white form panel; semantic groups; neutral fields; specific black Save action; inline validation and retained draft |
| Settings | Page title;232px section navigation when space allows; white sections with clear labels; switches for immediate settings or explicit Save for grouped edits |
| Authentication | Pale page, small brand mark, white 32px-radius form max 440px wide/padding 32px; title 28px; standard 44px fields; black primary action; neutral provider buttons if needed |
| Wizard/onboarding | Stepper + focused form/card; concise progress text; stable Back/Next footer; no forced carousel or decorative illustration |
| Editor/workbench | Quiet top tools; flexible primary canvas; optional explorer and properties panes; neutral surfaces and black active tools; resizable panes with minimum widths |
| Reports/analytics | Filter scope made explicit; a few well-labeled chart panels; legends and data alternatives; exact values; restrained paired green/lime emphasis |
| Knowledge/article | White readable surface max 760px text column, body 16/26px; h1≈32px, h2≈24px, h3≈18px; black underlined links; neutral quotes/code; source/context metadata |

## Boundaries and unspecified themes

This is a **light** design system with a dark-green feature treatment. It does not define a full dark theme. If dark mode is later required, derive and verify a separate surface/contrast token set while preserving component geometry; do not invert the screenshot. Specialized domains such as medical imaging, geographic editing or a full code IDE need additional domain-specific interaction contracts beyond the common components covered here.
