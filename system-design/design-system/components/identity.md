# Badges, status and avatars

**Read when:** Badges, chips, counts, signal disks, avatars/groups, presence or organization capsules.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** None.  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Badges, status indicators, chips, avatars, and identity [E]

| Element | Specification |
|---|---|
| Neutral badge | 24 px high; 8 px horizontal padding; 12 px radius; white or inset-neutral background; 12 px / 16 px label |
| Signal badge | 28 px high; 12 px horizontal padding; pill shape; small black/dark glyph or 6 px dot; 6 px label gap; colored fill from a semantic signal token; dark label |
| Outline badge | 24 px high; white; 1 px control stroke; primary ink; use only when neutral fill does not separate from its parent |
| Count badge | Minimum 20 × 20 px; 10 px radius; 11 px medium tabular number; allow width to grow with 6 px horizontal padding; show a deliberate cap such as `99+` only when the underlying count remains available |
| Filter chip | 32 px visible height; 12 px horizontal padding; 16 px radius; white; 1 px stroke; 12–13 px label; optional close affordance with 8 px gap; expand hit height to 44 px on touch |
| Selected filter chip | Black background; white label; white close glyph; focus ring independent of selection |
| Status disc | 36 × 36 px for feed rows; 28 × 28 px for dense table cells; 16–18 px dark icon; no shadow |
| Small status marker | 8 × 8 px dot plus text; never use a dot as the sole data label |
| Avatar | Circular; 40 px default, 32 px compact, 48 px profile, 64 px detail header; `object-fit: cover`; neutral fallback with 14 px initials |

- A noninteractive badge is not focusable. A chip that changes a filter is a button or checkbox-like control with a clear selected state. A chip that navigates is a link. A removable chip has a named remove action, not an unlabelled `×` target.
- Use black text and icons on vivid signal fills if measured contrast supports it. A positive value displayed as colored text needs a darker, contrast-checked semantic text token; do not assume the signal fill token is also a valid small-text color.
- Mapping: green = successful/approved/completed; yellow = pending/in progress; orange = warning/attention/at risk; coral = failure/denied/destructive; lavender = informational, automated, or assisted result when an explicit legend defines it. These are semantic roles, not a requirement to keep the original domain.
- Tag color does not encode arbitrary categories by default. Use neutral labels unless category differentiation is a real task requirement. Include text when many similar tags must be distinguished.
- Avatar groups overlap by **8 px**, with a **2 px** parent-surface outline around each circle. Show at most **4 avatars** before a neutral `+N` circle. The group has a readable collective label; each avatar's name is exposed when individually interactive.
- Presence indicators are **8 px** circles with a **2 px** parent-surface outline at the lower logical end of a 32–40 px avatar. Presence is secondary and must not compete with record status.
- A user-menu trigger combines a 36–40 px avatar, 14 px name, and 12 px chevron in a 44 px white pill with 8 px content gaps. On narrow screens, remove the displayed name before shrinking the avatar or hit target.
- Company or organization logos sit inside a white capsule, approximately **80–116 px wide × 32–36 px high**, with **8 px** horizontal and **6 px** vertical breathing room. Preserve the logo's aspect ratio. Logos are image content, not text rendered in an approximate font.
