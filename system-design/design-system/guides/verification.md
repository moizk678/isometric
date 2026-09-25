# Implementation and verification

**Read when:** Planning implementation order or checking a completed component, screen or reconstruction.  
**Requires:** None beyond the entry point.  
**Related (optional; do not automatically load):** [Accessibility, contrast and internationalization](../foundations/accessibility.md), [Source, evidence and measurement conventions](../reference/evidence.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Build order for a future implementing agent

1. Read [design.md](../../design.md) and identify whether the request is reference reconstruction or domain translation. Follow its task routing and load only the chosen modules plus their required dependencies; do not read the whole collection. Produce a short list of applicable components; do not build the reference product automatically.
2. Load the source image if visual matching or source verification is relevant. Establish tokens, font candidate and glyph match, icons, and approved assets. Record missing source assets as substitutions.
3. Implement surface and layout primitives first: workspace, panel, inset, stack/grid, text, icon and state disk. Check their relationships before building all screens.
4. Implement controls and state contracts, including select/date/calendar, with accessible behavior. Reuse proven semantic behavior where available; fully replace visual defaults with these tokens.
5. Build the requested workflows from the recipes. Wire real content/data requirements; do not manufacture measures or original-image business rules.
6. Verify visual fidelity and product behavior separately. A screenshot comparison cannot prove keyboard behavior; a passing interaction test cannot prove aesthetic fidelity.
7. Record only deliberate deviations: product-specific adaptation, missing asset/font substitution, responsive reflow, or contrast improvement. Do not describe arbitrary framework defaults as faithful interpretation.

## Extension acceptance checklist for an implementing agent [E]

- [ ] Component is identified as observed or extended; invented interactions are not described as visible evidence.
- [ ] Geometry, typography, surface, state, and interaction rules come from this collection or an explicitly documented product-specific exception.
- [ ] Normal, hover, focus-visible, pressed/selected, disabled, loading, empty, error, overflow, and long-content cases are accounted for where relevant.
- [ ] The component works with keyboard, pointer, and touch; icon-only controls have names; hover-only actions have an equivalent visible path.
- [ ] Primary action/selection remains black; semantic colors carry consistent meanings; overall surface composition remains predominantly neutral.
- [ ] Text and controls do not clip at narrow widths, long localization, 200% zoom, or when the on-screen keyboard opens.
- [ ] Overlay positioning, focus restoration, click-away, Escape, and unsaved-change behavior are explicit.
- [ ] Data presentation preserves values, units, sorting/filtering scope, and unknown/error states; chart decoration does not distort interpretation.
- [ ] Custom appearance uses semantic native controls where possible and fully implemented accessible patterns where native controls cannot express the design.
- [ ] This remains a reusable visual/interaction specification; domain copy, branded logos, healthcare entities, and business rules are not hardwired into unrelated software.

## Reference fidelity checklist

- [ ] Taupe exterior and pale workspace are different colors; source proportions/margins are matched at the comparison size.
- [ ] Top and bottom grids use different split ratios; all major panels share the correct row edges.
- [ ] Logo/navigation/search/utility/profile shapes and spacing are represented; the header has flexible whitespace.
- [ ] Active Dashboard and Today are black nested pills; New Authorization is a separate black CTA.
- [ ] Greeting, overline and support line have correct relative scale, weight, color, line breaks and punctuation.
- [ ] Financial panel has two green surfaces, a white label pill, a white arrow circle, enormous regular value and a three-cell outlined strip.
- [ ] Six miniature bars have the right order, relative heights, rounded bottoms, historical hatch and single solid lime latest bar.
- [ ] Four Today tiles use one shared white parent, warm inset fills, aligned values, top labels and colored icon circles.
- [ ] All KPI units, trend directions, change values and comparison copy match; double-check and motion stopwatch icons remain distinct.
- [ ] Table has five separated rounded rows; no invented visible checkbox/sort/footer; exact column alignment and action widths are preserved.
- [ ] Probability uses ten vertical ticks and exact numerical labels; payer pills vary with artwork width.
- [ ] Activity uses one inset well, six entries, five dividers, right-aligned timestamps and only the evidenced subtitle truncation.
- [ ] Large numbers are regular, not bold; UI text remains sans serif while logo artwork retains its original lettering.
- [ ] Status symbols are dark on colored disks, not automatically white.
- [ ] No new resting-card shadows, gradients, bright default link colors or ornamental texture were introduced.
- [ ] Any unknown font/logo/photo substitution is documented honestly.

## Product component verification

| Area | Required verification |
|---|---|
| Controls | Keyboard/pointer/touch, all relevant states, non-overlapping targets, labels and form semantics |
| Select/combobox | Single/multiple, no results, slow and failed requests, long options, disabled options, active versus committed selection, clear/reopen |
| Date/time | Leap day, month/year transitions, locale week start, bounds, unavailable dates, same-day/range order, draft cancel/apply, manual entry, time zone/clock changes |
| Forms | Empty required submit, correction, cross-field error, server error, saved draft, password manager/paste, long help, focus after failed submit |
| Tables/lists | Empty/error/loading, long title, large values, many records, sorting/filtering, bulk selection scope, narrow comparison view, detail/back preservation |
| Overlays | Viewport edges, nested dialog-owned picker, Escape order, outside click, focus return, scroll locking, on-screen keyboard, dirty form |
| Charts | Missing versus zero, units, true values/scales, readable legend, keyboard/text alternative, semantic color consistency |
| Layout | 1790px comparison plus 1440, 1280, 1024, 768, 390 and 320px product widths; long labels, RTL when supported,200%/400% zoom |
| Accessibility | Actual color pairs, focus visibility, screen-reader names/relationships, forced colors, reduced motion, no hover-only essential action |

Visual review order: **macro layout → surface colors → typography → component proportions → spacing → icons/assets → tiny optical details**. Compare rendered screenshots at the same size as the reference plane; avoid claiming pixel perfection when fonts or artwork differ. For geometry, use approximate±2px tolerance at the reference plane where measurement confidence permits; prioritize matching line breaks, baselines and relative proportions over antialiasing noise.
