# Image and video viewers

**Read when:** Media frames, playback, lightbox, captions, fitting and loading behavior; not uploads.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** [Uploads, attachments and file views](uploads-files.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

**Image/video viewer.** Media frame has 24 px radius, clips media only, and uses `object-fit: contain` when full content matters; use `cover` only for deliberate previews. Preserve intrinsic aspect ratio and layout space while loading. Viewer controls are 44 px circles/pills; captions use 12–14 px secondary ink outside the image. Full-screen lightbox uses a dark backdrop with white controls, an explicit close button, keyboard arrows for a real sequence, and Escape to close. Do not autostart audio/video. Playback controls have labels, visible focus, captions support, and keyboard access.
