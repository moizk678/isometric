# Choice, range and color controls

**Read when:** Checkbox, radio, switch, choice card, slider/range, rating or color picker.  
**Requires:** [Shared field contract](field-basics.md)  
**Related (optional; do not automatically load):** None.  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Checkbox, radio, and switch [E]

| Control | Visual contract | Behavior and content |
|---|---|---|
| Checkbox | 20px square, radius 6px, 1px `--stroke-control`; checked black fill with white 12px check; indeterminate black fill with centered white 10px dash. | Labeled row minimum 44px high; 10px gap to 14px label. Label activates input. Space toggles. Mixed state only for an actual partial group selection, never as a third arbitrary value. |
| Radio | 20px circle, 1px neutral border; selected black outer disc with a centered 8px white dot. | One selected value per named group; group has legend. Arrow navigation follows radio semantics; Space selects. Label is clickable. Do not use radios for immediate destructive actions. |
| Switch | 40px × 24px track, radius 12px; off neutral inset with 1px boundary and 18px white thumb; on black track with white thumb; inset 3px. | Enclose in a 44px minimum target. Label explains the setting, not current toggle action. Use for immediate on/off settings; communicate any save failure and restore the prior state. Keep label stable. Space toggles. |

All three retain visible focus; disabled controls remain recognizable and noninteractive. Use native inputs or equivalent semantics. Error associates with the group when no option is chosen; avoid outlining every radio as separately invalid. A description sits below the label with 4px gap and 12px/18px secondary type. Card-style choices use white or inset surface, 16px radius, 16px padding, 1px neutral border; selected card has a 1px black boundary plus its checked control, rather than a bright solid fill. Do not stretch the reference's green metric color into ordinary selected switches or checkboxes.

## Slider, range slider, and rating [E]

- Slider: 4px neutral track, selected segment black, 18px white thumb with 1px black boundary and subtle shadow. The thumb sits within a minimum 44px interactive target. Label and formatted current value share a row above with 8px bottom gap. Optional min/max labels below use 12px secondary text.
- Arrow keys increment one declared step; Page Up/Down adjust a larger declared step; Home/End select minimum/maximum. Expose current value and units. Always provide a number-input alternative where precise entry matters.
- Range slider has two separately named thumbs, e.g. `Minimum price`, `Maximum price`. Default prevents crossing; when values coincide, keyboard access must still reach both thumbs. Selected segment spans them; labels do not overlap. For narrow/mobile layouts place values in two fields above.
- Disabled track/thumb use neutral tokens, no fake hover. Invalid bounds create a group-level error. Tick marks are 2px × 6px, neutral; show only meaningful intervals.
- Rating uses five 20px outline stars or domain-appropriate icons within 44px targets, 4px visual gap; selected icons near-black, hover previews neutral/black. Expose a labeled discrete choice such as `4 of 5`, allow keyboard selection, and provide a clear option if rating is optional. Semantic warning yellow is not decorative default rating fill.

## Color picker [E]

Use a labeled 44px capsule with 20px circular swatch, 14px formatted color value, and trailing disclosure icon. White/light swatches retain a 1px neutral outline. The custom popup width is `min(304px, visualViewportWidth - 24px)`, with 24px radius, white surface, 16px padding, and the same 8px anchor gap/elevation as other form popups. Paint its 1px boundary inset, without consuming layout width. The editable color spectrum fills the inner width (272px at the desktop default), is 160px high and has 12px radius; a hue rail is 12px high within a 44px target; an optional alpha rail uses the same dimensions with a checkerboard background. A 16px selection indicator has contrasting inner/outer outlines so it remains visible over any chosen color.

Show labeled numerical entry fields for the selected format, with an explicit format selector for HEX/RGB/HSL; alpha is offered only if the destination supports it. Preset swatches are 24px circles within 44px targets; the selected swatch gains a contrasting ring and check. Presets use actual destination colors rather than reusing semantic status colors as arbitrary decoration. Text entry is the complete keyboard-operable alternative to dragging. Apply commits; Cancel/Escape restores the previous value. Invalid color syntax stays editable with a format example. If the chosen color will be used for text against a known background, present a measured readability indicator with the tested foreground/background pair; do not claim formal compliance from the hue alone.
