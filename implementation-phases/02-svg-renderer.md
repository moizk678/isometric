# Run 02 — Deterministic SVG renderer

**Agent brief:** Render a validated semantic scene into safe, editable SVG and a preview. The renderer must never infer missing topology.

**Depends on:** [Run 01](01-scene-contract.md). Read architecture sections 5 and 8.

## Build

1. Create a pure `render_svg(scene, symbol_library_version, style_profile_version)` function in `packages/pipeline/render`. Sort layers/objects by stable IDs and normalize numeric formatting so the same inputs produce identical bytes.
2. Add a minimal versioned piping symbol library with connection ports for a ball valve, an explicitly identified tee/elbow fitting, endpoint, and unknown placeholder. Structural tee/elbow junctions render once as geometry; a separate fitting symbol appears only when explicitly represented in the scene. Symbols use renderer-owned SVG definitions; no external URLs or scripts.
3. Render named groups for pipe layers, symbols, dimensions, callouts, and annotations. Preserve typed `<text>`, document colors, object IDs, and `viewBox` in rectified page coordinates. Escape all user text and metadata.
4. Add a preview rasterizer adapter with a pinned renderer version. Keep review overlays and original-paper overlays out of the exported SVG.
5. Validate generated XML, element/attribute allowlist, bounds, and absence of script/external references. Report a structured error rather than publishing invalid SVG.

## Deliverables

- Renderer and preview adapter, symbol definitions, SVG safety validator, and golden fixtures.
- Documented function signatures and export version metadata.

## Exit checks

- All Run 01 fixtures render, parse, and rasterize; a disconnected crossing still looks disconnected or is explicitly marked unresolved.
- Two renders of the same inputs have identical checksums.
- Text containing XML metacharacters cannot inject markup.
- Each object is separately addressable in SVG; output is not one giant traced path.
- A tee/elbow junction without an explicit fitting object does not render a duplicate symbol.
- `make test-pipeline` and relevant golden-image checks pass.

## Out of scope and handoff

Do not perform image recognition or write an editor. Hand off rendering entry points, supported symbol IDs, preview command, and known font substitutions to [Run 03](03-supabase-persistence.md).
