# Feedback, loading and progress

**Read when:** Toasts, notices, empty/error states, skeletons, spinners, progress or optimistic updates.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** None.  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Notices, feedback, empty states, errors, and loading [E]

**Toast.** White floating panel, **24 px radius**, **16 px padding**, preferred width **320–400 px**, capped at `min(400px, visualViewportWidth - 32px)` so it can narrow below 320px on small screens; 36 px signal disc, 12 px icon/content gap, 14 px title, 12 px optional description, and a 44 px close/action target. Place at the lower logical end on desktop, **24 px** from safe edges; use 16 px side margins on mobile. Show at most **3** stacked toasts with 8 px gaps. Noncritical success toasts may auto-dismiss after **5 seconds**; pause on hover/focus. Actionable, error, or long messages persist until dismissed or resolved. Use polite live announcements for ordinary updates and urgent announcements only for genuinely urgent failures. Do not repeatedly announce the same event.

**Inline banner.** Full available width within its owning section; neutral inset surface, **20–24 px radius**, 16 px padding; 28–36 px signal disc, 12 px gap, 14 px message. A small action sits at the logical end or wraps beneath the text on narrow screens. Signal color concentrates in the disc/marker, while the text surface stays light and calm. Place the banner next to the affected area; global notices are reserved for global conditions.

**Inline field/section error.** 12 px / 16 px text with an explicit error icon and **4–8 px** gap beneath the affected control/group. Errors explain a correction, not just `Invalid`. A submission summary at the top links to each invalid field, and focus moves to that summary or first invalid field according to the task. The [shared field contract](field-basics.md) defines border/ring details.

**Empty state.** Use the existing panel shape with **32–48 px vertical padding**. Center a **48 px neutral circle** containing a 24 px outline icon, then 16 px title gap, 16–18 px heading, 8 px description gap, max **360 px** description width, and 24 px gap to one primary action. For compact table emptiness, use 24 px padding and left-aligned copy instead of a large illustration. Distinguish: first use (`Create your first…`), search mismatch (`No results match…`, clear filters), permission limitation (explain access), and failure (retry). Do not reuse the same generic blank state for all four.

**Error state.** Preserve successfully loaded surrounding UI. Replace only the failed region with a neutral inset block, coral warning disc, plain explanation, and a secondary retry button. Show an error identifier only if it helps support. Keep raw stack traces and implementation jargon out of normal product flows.

**Skeleton.** Match the eventual layout exactly: text bars 12–16 px high, control placeholders 36–44 px high, circular avatar placeholders at real avatar sizes, and row placeholders at the final row height. Neutral gray fill is **approximately 6% primary ink over the surface** with 8 px bar radius. An optional low-contrast pulse is **1.5 s**; disable under reduced motion. Skeletons are decorative to assistive technology; their region exposes one loading state. Do not render fake readable text or show both a full skeleton and a redundant giant spinner.

**Spinner.** 16 px inline, 20 px in a control, or 28 px for a small isolated region; **2 px** track with an emphasized arc; primary ink for neutral loading. Delay a blocking loading indicator approximately **150–250 ms** to avoid flashing for fast operations. For known long operations, show text explaining what is running.

**Linear progress.** Track height **6 px** for compact status or **8 px** for explicit task progress; neutral track; pill ends; black fill for generic progress, semantic fill only when the progress has a meaningful status. A 12 px label/value sits 8 px above. Indeterminate progress has a moving segment only while progress is unknown. A value of 100% does not imply success until the actual operation confirms completion.

**Segmented micro-meter.** Approximate a compact probability/readiness indicator with **10 rounded vertical ticks by default** (a 12-part variant requires a meaningful 12-part domain scale), **3–4 px** wide, **14–16 px** high, and **2 px** gaps; inactive ticks are low-contrast neutral. Place the exact percentage immediately beside it. Use a documented domain-specific mapping of color to bands, or one neutral fill; do not invent thresholds from the screenshot's five examples.

**Optimistic updates.** A reversible action may update immediately if the application supports reliable rollback. Keep a pending cue near the changed content, announce failures, restore prior state on failure, and offer retry/undo. Do not remove the user's input or show a final green success state before confirmation when failure would be materially confusing.
