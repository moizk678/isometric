# Uploads, attachments and file views

**Read when:** Dropzones, file selection, attachment state, upload progress, image upload or file list/grid.  
**Requires:** [Shared field contract](field-basics.md)  
**Related (optional; do not automatically load):** [Image and video viewers](media.md)  
**Load only for this variant:** Full image/video inspection or lightbox → [Image and video viewers](media.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## File upload, attachment list, and image selection [E]

- Upload zone: minimum height 144px, radius 24px, 1px dashed neutral border, inset-neutral fill, padding 24px, centered 24px upload icon inside a 44px white circle, 14px primary instruction, 12px format/size helper. A black 36px or 44px `Choose files` button remains available; drag-and-drop is supplementary.
- Drag-over: boundary becomes black, surface remains neutral, concise `Drop files to upload` instruction. Do not flash a green-filled zone. Reject unsupported types/oversize files individually with actionable text.
- Attachment row: 56px minimum height, 16px radius, white/inset contrast against its container, 12px padding, 32px file-type icon tile, primary filename 13px, metadata 11px, named trailing remove/retry buttons. File extension remains visible when the middle of a long name truncates.
- Uploading: 6px neutral track with black progress fill and textual percentage if known; indeterminate progress when unknown. Success uses a small positive icon; failure uses danger icon and `Retry`; canceled files do not appear as saved. Parallel uploads report per-file status plus aggregate progress when useful.
- Image upload preview uses a square 56px thumbnail, radius 12px, cover fit; its attachment row grows to at least 80px to contain the thumbnail and padding; the larger inspection view preserves the full image. Replacing an image should preserve the previous saved version until the replacement succeeds. Cropping is an explicit optional step, never a hidden destructive transformation.
- File picker supports keyboard operation; status changes are announced. Remove has an accessible name including filename. Whether removal is immediate or requires confirmation follows reversibility and data importance; avoid blanket confirmation for a reversible unsaved selection.

**File list/grid.** Reuse list/card geometry: 56–72 px rows or 180–240 px grid cards, white surface, 20–24 px radius, 16 px padding, 40 px file-type icon disc, 14 px filename, 12 px size/date. File status uses a small semantic marker. Show extensions when relevant, preserve complete filenames through detail/tooltip, and distinguish file selection from opening. Grid/list view toggles are 36/44 px icon buttons with a black selected state.

**Upload/progress area.** Use the single canonical upload, attachment and image-selection specification in [Uploads, attachments and file views](uploads-files.md). It owns the dropzone, browse action, per-file progress, validation, cancellation and retry states.
