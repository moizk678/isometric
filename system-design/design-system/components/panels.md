# Panels, lists and detail layouts

**Read when:** Cards, metric tiles, rows, key-value blocks, master-detail, split panes, accordion or dividers.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** [Responsive composition](../foundations/responsive.md)  
**Load only for this variant:** Master-detail presented in a modal drawer → [Dialogs, drawers and sheets](dialogs.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Cards, list rows, and master–detail compositions [E]

- **Standard panel:** white, 32 px radius, 24 px content padding; header uses an 18–20 px title, optional 12–14 px supporting line, and 44 px icon actions at the far end. Header-to-body gap: **16–24 px**. Related inset content is warm neutral with 24 px radius, not white cards floating over white cards with repeated shadows.
- **Compact panel:** same visual language with 24 px outer radius and 16 px padding when the parent grid is dense. Do not use a compact radius solely to make one card look different.
- **Inset metric tile:** warm neutral, 24 px radius, 16 px padding; short label at the top, optional status disc at the opposite corner, flexible empty middle, prominent numeric value toward the bottom, and a secondary delta line beneath. Align neighboring tile values and delta baselines even when labels wrap.
- **List row:** **72 px minimum height**, 16 px padding, 12 px internal gaps, 24 px radius when separated by 8 px gaps. Use a 40 px icon/avatar disc, a flexible title/subtitle column, and one trailing value or action. A title is 14 px / 20 px; subtitle 12 px / 16 px. Dense feeds may use 64 px rows inside a single shared inset panel with 1 px neutral separators and no radius per row.
- **Selectable row:** the shared neutral hover surface; selected row uses a 1 px primary-ink inset outline and a light neutral surface. A selected record row does not become entirely black when that would reduce data readability. Include a checkbox or explicit selected marker when multiselection exists.
- **Clickable card:** only the dominant destination spans the card. Secondary buttons remain independent targets; never nest one interactive control inside another interactive wrapper. Add a hover surface change or border emphasis, plus a complete visible focus treatment.
- **Description list / key-value block:** 12 px muted term, 14 px primary value, 4 px vertical gap, 16 px between pairs. A row format uses a **120–160 px** term column and flexible value; stack labels above values below 480 px content width. Use semantic terms and descriptions rather than a decorative table for one record.
- **Master–detail:** use a **320–400 px** list pane and a flexible detail pane, with a **16–24 px** gap. Each pane gets one coherent surface, not nested cards around every field. Selected item uses the selectable-row treatment. Below **900 px available component width**, show list and detail as separate views or open the detail in a drawer; provide a persistent back control and retain scroll position.
- **Split pane:** divider hit area 8 px, visual line 1 px; on hover show a centered 24 px tall rounded grab mark. Minimum pane width 280 px. Support keyboard resize from the separator, with 16 px steps and meaningful accessible value. Offer a reset layout action when user resizing is persisted.
- **Accordion:** 52 px minimum header, 16 px horizontal inset, 14 px medium title, trailing 16 px chevron. Shared white panel with 24 px radius; 1 px separators between headers. Expanded body uses 16 px padding and 14 px text, with an optional neutral inset group. Enter/Space toggles, trigger exposes expanded state, and collapsed content leaves the tab order. Single-open and multi-open variants are explicit configuration options.

**Divider and section label:** use 1px `--stroke-subtle`, normally 16–24px surrounding space. A small label may interrupt a divider only for a meaningful separation such as alternative authentication methods; avoid decorative rules around every heading.
