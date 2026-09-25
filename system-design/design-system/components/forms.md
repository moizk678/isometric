# Form layout and validation

**Read when:** Field grouping, validation, submission, dirty drafts, autosave and form footers.  
**Requires:** [Shared field contract](field-basics.md)  
**Related (optional; do not automatically load):** [Dialogs, drawers and sheets](dialogs.md)  
**Load only for this variant:** Discard confirmation or modal form shell → [Dialogs, drawers and sheets](dialogs.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Form organization, validation, and completion [E]

**Groups and layout.** Default form panel is white, radius 32px, padding 24px. Title is 20px/26px medium; description 13px/20px secondary with 6px gap. Group headings 15px/22px medium; supporting description 12px/18px; 16px gap before fields. Single-column reading order is preferred for narrative/long inputs. Use two equal columns only for strongly related short fields at container width ≥640px, gap 16px; collapse to one below that. A composite address/date group has a programmatic group label and field-specific names. Repeated groups use 20px gaps and named `Remove [item]` actions; Add is a neutral outlined pill. Never render an unbounded form as one unbroken gray inset block.

**Validation policy.** Validate after first blur or an attempted submit, then revalidate the touched field as the user corrects it. Do not show invalid state on first render for empty required fields. Run expensive/server checks after a debounce or explicit action and avoid stale responses. Preserve all entered values on failed submission. When several fields fail, show a compact summary near the form heading and focus it or the first invalid field according to form length; summary entries link to the fields. Error messages name the field/problem/repair, e.g. `End date must be on or after the start date.` Keep helpers that remain relevant and replace only conflicting feedback. Requiredness, format, min/max and cross-field constraints must agree between UI and data validation.

**Footer.** Actions align right on desktop: tertiary/outlined Cancel followed by black primary Save, 12px gap, both 44px high; destructive actions are spatially separated. On narrow screens the primary action can span the width with the secondary beneath or alongside only if labels fit. Sticky footers have white fill, a 1px top boundary, 16px padding, safe-area support, and enough content bottom padding to avoid hiding the final field. During submission, primary button preserves width, shows spinner plus `Saving…`, and prevents duplicate submission; nonconflicting fields may remain readable. On success, communicate the saved state and navigate only as expected. A save failure retains the form and provides retry without duplicating already-created records.

**Dirty state.** Indicate unsaved changes only when useful. If navigation would irreversibly discard meaningful work, use a confirmation dialog with `Keep editing` and an explicit discard action. Autosave shows understated `Saving…`, `Saved`, or `Couldn't save · Retry`; autosave failure must not masquerade as successful completion. A reset action is labeled distinctly from cancel and restores defined initial values.
