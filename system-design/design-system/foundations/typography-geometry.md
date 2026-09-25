# Typography, geometry and rhythm

**Read when:** Choosing fonts or matching type hierarchy, nested radii, panel dimensions or spacing.  
**Requires:** [Design tokens](tokens.md)  
**Related (optional; do not automatically load):** None.  
**Evidence:** Raster estimates [M] and product defaults [E]; exact font unknown [U].  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Typography [M/E]

**[U] Exact family:** a modern sans serif with a high x-height, clean double-storey `a`, open spacing in body copy, and relatively geometric round letters. The greeting has a single-storey `g` and double-storey `a`; check these glyphs when choosing a font. UI typography is sans serif; embedded organization logos retain their own lettering, including serif lettering in the United Healthcare mark. **[E] Recommended reproduction starting point:** Inter; use the existing equivalent project font if it matches better. Load the actual font file before visual comparison. An unprovided font must not silently fall back during an acceptance screenshot.

| Role | Reference target size / line-height | Weight / tracking | Use |
|---|---|---|---|
| Hero value | `108 / 116px` | 400, around `-0.035em` | `$184,500`; tune fit to ≈478px-wide ink bounds |
| Greeting | `44 / 52px` | 400–450, around `-0.045em` | `Good morning, Sarah` |
| KPI value | `52 / 58px` | 400, around `-0.035em` | 42, 87.4, 8, 3.2 |
| Panel heading | `22 / 28px` | 550–600, around `-0.025em` | Today / Attention required / Recent activity |
| Probability percentage | `26 / 32px` | 400, around `-0.02em` | 78%, 61%, etc. |
| Primary row title | `16 / 21px` | 450–500, normal | Procedure/entity title |
| Nav / primary action | `16 / 20px` | 450–500, normal | Desktop header, New Authorization |
| Body / intro support | `16 / 22px` | 400, normal | Activity counts, sorting explanation |
| Metric label | `15 / 21px` | 400, normal | Pending authorizations; other labels |
| Secondary control | `14 / 20px` | 450–500, normal | Review case; segmented control |
| Metadata / table headings | `14 / 19px` | 400, normal | ID, due date, issue, timestamp |
| Small chart / trend | `13 / 18px` | 400–500, normal | Months, delta support, hero strip labels |
| KPI unit | `14 / 19px` | 400, muted | %, cases, days; baseline aligned to number |

These are **starting metrics**, not a claim about the original font's CSS. Match line breaks, ink width, baseline, and perceived weight before fine-tuning 1px differences. In product mode, new form labels/body use 14–16px with a 20–24px line-height; never shrink text merely to preserve desktop geometry.

Use `font-variant-numeric: tabular-nums` for live metrics, dates, progress values, and aligned numeric columns. Preserve a proportional font for prose. Use regular weight for large figures; medium for actionable row names; muted metadata should remain legible. Avoid uppercase micro-labels and wide tracking: neither is part of this reference.

## Shape, stroke, depth and rhythm

| Element | Reference [M] | Extension default [E] |
|---|---|---|
| Workspace frame | 36px radius | 36px desktop; 0–24px when edge constrained |
| White/green outer panel | 34–36px radius | 32px |
| Dark hero inset | 28px radius, ≈9px frame inset | 24px inset with 8px parent gap |
| Metric tile | ≈28px radius | 24px |
| Activity inset | ≈28px radius | 24px |
| Table row | ≈32px radius; 70–72px high | 24px for standard product rows; 16px compact variant |
| Small support strip | ≈18px radius, thin border | 16px |
| Pill | Half of control height | `999px` |
| Circle | Equal width/height | `50%` |
| Flat icon stroke | ≈1.5–1.8px at 20px | 1.5px; 1.75 if needed at 24px |
| Borders | ≈1px only in select places | 1px; 2px visible focus ring |
| Major gutters | 17–18px | 16/24px |
| Inner row/metric gutters | ≈9–12px | 8/12px |
| Panel text padding | ≈22–24px | 24px |

Nested radii should normally satisfy `outer radius ≈ inner radius + inset`; exact source shapes can deviate slightly. Do not apply the same large radius blindly to every nested rectangle. Static panels remain shadowless. Only floating overlays/dialogs receive the new elevation tokens. The screenshot's faint edge antialiasing is not evidence of a glow or drop shadow.
