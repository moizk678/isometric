# Design tokens

**Read when:** Implementing or changing colors, fonts, spacing, radii, control sizes, focus, elevation or motion tokens.  
**Requires:** None beyond the entry point.  
**Related (optional; do not automatically load):** None.  
**Evidence:** Measured palette [M] plus explicit product extensions [E].  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Palette and role mapping

**Never use a color because it is available. Assign it a role.** Fills sampled from solid interiors are [M]; text colors, thin strokes, and derived interactive colors are approximate or [E].

| Token | Value | Evidence | Role |
|---|---|---|---|
| `--surface-canvas` | `#D1CCC6` | [M] high | Taupe outside the workspace; presentation only |
| `--surface-page` | `#EAEBE6` | [M] high | Pale gray-green workspace background |
| `--surface-panel` | `#FFFFFF` | [M] high | Outer panels, nav rail, secondary pills, search |
| `--surface-inset` | `#F2F1ED` | [M] high | Metric tiles, rows, activity well, utility circles |
| `--surface-hover` | `#E9E8E2` | [E] | Hover on neutral interactive surfaces |
| `--surface-pressed` | `#DFE0D8` | [E] | Pressed neutral controls |
| `--surface-selected` | `#E4EADF` | [E] | Subtle multi-row selection background |
| `--ink-primary` | `#0B0B0B` | [M] high on fills | Main text, primary controls, selected pills |
| `--ink-secondary` | `#50514D` | [M] approximate | Secondary sentences, field labels, metadata with normal emphasis |
| `--ink-muted-reference` | `#8B8B85` | [M] approximate | Screenshot's overline, timestamps, muted labels |
| `--ink-muted` | `#686963` | [E] | Production muted text; deliberately darker |
| `--ink-on-dark` | `#FFFFFF` | [M] | Text on black/green surfaces |
| `--ink-on-feature` | `#C8E8D4` | [M] approximate | Hero support sentence |
| `--ink-feature-muted-reference` | `#B4D8C4` | [M] approximate | Hero strip labels |
| `--stroke-subtle` | `#E0DFDB` | [M] approximate | Activity separators, quiet internal rules |
| `--stroke-control` | `#D2D2D2` | [M] approximate | Secondary button border / optional field boundary |
| `--stroke-control-strong` | `#777970` | [E] | Boundaries where a low-contrast fill alone is insufficient |
| `--feature-outer` | `#4A9169` | [M] high | Mid-green hero wrapper |
| `--feature-inner` | `#2F6A4A` | [M] high | Deep-green hero well |
| `--feature-history` | `#4A906B` | [M] approximate | Historical bars, distinct from hero outer only slightly |
| `--feature-hatch` | `#397B58` | [M] approximate | Thin darker diagonal strokes on past bars |
| `--feature-axis-reference` | `#809080` | [M] approximate | Muted month labels in reference |
| `--feature-highlight` | `#D7EE3C` | [M] high | Current month lime bar; sparse emphasis only |
| `--state-positive` | `#1FB25A` | [M] approximate | Success icon disk / favorable probability segments |
| `--state-pending` | `#FCCC0A` | [M] approximate | Waiting disk / intermediate probability segments |
| `--state-warning` | `#F8A01A` | [M] approximate | Risk disk, urgency badge, warning segments |
| `--state-danger` | `#F0563A` | [M] approximate | Denied/error disk |
| `--state-info` | `#C4B4FB` | [M] approximate | Automated/review or time metric disk; not generic hyperlink blue |
| `--ink-positive` | `#167342` | [E], close to image | Favorable small change text |
| `--ink-warning` | `#8A5000` | [E] | Warning text on light surfaces |
| `--ink-danger` | `#B33624` | [E] | Adverse change, error text, destructive text |
| `--ink-info` | `#57418A` | [E] | Supporting informational text |
| `--focus-ring` | `#0B0B0B` | [E] | Keyboard focus on light surfaces |
| `--focus-ring-inverse` | `#D7EE3C` | [E] | Keyboard focus on black/deep green |

**Semantic distinction:** green hero fill is a brand/emphasis treatment even though the data is “at risk.” Orange, iconography, and labels carry risk semantics elsewhere. Do not infer that all green regions mean success. Pending yellow and warning orange are different states. Lavender is used both for turnaround and AI review, so it does not establish one universal business meaning.

## Copy-ready canonical tokens [E unless noted]

```css
:root {
  color-scheme: light;
  --surface-canvas: #d1ccc6;
  --surface-page: #eaebe6;
  --surface-panel: #ffffff;
  --surface-inset: #f2f1ed;
  --surface-hover: #e9e8e2;
  --surface-pressed: #dfe0d8;
  --surface-selected: #e4eadf;
  --ink-primary: #0b0b0b;
  --ink-secondary: #50514d;
  --ink-muted-reference: #8b8b85;
  --ink-muted: #686963;
  --ink-on-dark: #ffffff;
  --ink-on-feature: #c8e8d4;
  --ink-feature-muted-reference: #b4d8c4;
  --stroke-subtle: #e0dfdb;
  --stroke-control: #d2d2d2;
  --stroke-control-strong: #777970;
  --feature-outer: #4a9169;
  --feature-inner: #2f6a4a;
  --feature-history: #4a906b;
  --feature-hatch: #397b58;
  --feature-axis-reference: #809080;
  --feature-highlight: #d7ee3c;
  --state-positive: #1fb25a;
  --state-pending: #fccc0a;
  --state-warning: #f8a01a;
  --state-danger: #f0563a;
  --state-info: #c4b4fb;
  --ink-positive: #167342;
  --ink-warning: #8a5000;
  --ink-danger: #b33624;
  --ink-info: #57418a;
  --focus-ring: #0b0b0b;
  --focus-ring-inverse: #d7ee3c;
  --font-ui: "Inter", "Helvetica Neue", Arial, sans-serif;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  --radius-control: 22px;
  --radius-field-multiline: 16px;
  --radius-overlay: 24px;
  --radius-inset: 24px;
  --radius-panel: 32px;
  --radius-frame: 36px;
  --radius-pill: 999px;
  --control-compact: 36px;
  --control-default: 44px;
  --control-large: 52px;
  --icon-small: 16px;
  --icon-default: 20px;
  --icon-large: 24px;
  --icon-stroke: 1.5;
  --shadow-panel: none;
  --shadow-overlay: 0 4px 12px rgb(11 11 11 / 0.04),
                    0 16px 40px rgb(11 11 11 / 0.10);
  --shadow-dialog: 0 24px 80px rgb(11 11 11 / 0.16);
  --overlay-scrim: rgb(11 11 11 / 0.32);
  --duration-quick: 120ms;
  --duration-standard: 180ms;
  --duration-panel: 240ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
  --z-base: 0;
  --z-sticky: 10;
  --z-popover: 30;
  --z-dialog: 50;
  --z-toast: 70;
}
[data-design-mode="reference"] {
  --ink-muted: var(--ink-muted-reference);
  --radius-panel: 36px;
  --radius-inset: 28px;
}
```

Token values are a controlled vocabulary. Component-specific source measurements may override a general token in reference mode; product extensions should use the standard values. Do not globally change panel radii because one small component needs a different radius.
