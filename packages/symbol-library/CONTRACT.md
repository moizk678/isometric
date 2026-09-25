# Symbol library contract

This file freezes the shape of a symbol library file and the symbol IDs and ports that scenes may reference. The loader is `load_symbol_library(version)` in `packages/pipeline/isometric_pipeline/render/symbols.py`. It returns a `SymbolLibrary`, which implements the `SymbolCatalog` protocol used by `validate_scene`.

Changing a symbol ID, a port name, a port position, or whether a port is required is a contract change. It needs a new library version.

## Files

| Version | File |
| --- | --- |
| `piping-symbols@1.0.0` | `piping-symbols-1.0.0.json` |
| `piping-symbols@1.1.0` | `piping-symbols-1.1.0.json` |

The bundled preview font is `fonts/LiberationSans-Regular.ttf`, with its license in `fonts/LICENSE`.

## JSON shape

```json
{
  "version": "piping-symbols@1.0.0",
  "units": "px",
  "symbols": [
    {
      "id": "ball_valve",
      "label": "Ball valve",
      "ports": [
        { "name": "inlet", "x": -20, "y": 0, "required": true },
        { "name": "outlet", "x": 20, "y": 0, "required": true }
      ],
      "primitives": [
        {
          "kind": "polygon",
          "points": [[-20, -10], [-20, 10], [20, -10], [20, 10]],
          "fill": false
        },
        { "kind": "circle", "points": [[0, 0]], "r": 4, "fill": true }
      ]
    }
  ]
}
```

Rules:

- The top-level keys are exactly `version`, `units`, and `symbols`. `version` must equal the version the file is loaded as. `units` is always `"px"`.
- `symbols` is sorted by `id`. For `piping-symbols@1.0.0`, each symbol has exactly the keys `id`, `label`, `ports`, and `primitives`.
- For `piping-symbols@1.1.0`, each symbol may also include `aliases` (string array), `anchor` (`x`/`y` in symbol-local px), and `allowedAttachments` (`nodeKinds`, optional `minIncidentEdges` / `maxIncidentEdges`) for classification port binding. The renderer ignores those optional keys.
- A symbol `id` matches `^[a-z][a-z0-9_]*$`. Port names within a symbol are unique.
- A port has exactly the keys `name`, `x`, `y`, and `required`.
- A primitive has `kind`, `points`, and `fill`. A circle also has `r`, and no other kind may have it.
  - `line`: exactly 2 points.
  - `polygon`: at least 3 points. It is closed automatically.
  - `circle`: exactly 1 point, the center, and `r > 0`.
- Only `line`, `circle`, and `polygon` exist. There are no paths, raw SVG, text, URLs, colors, or style values.
- Every number is finite. Every coordinate, including each circle's full extent, lies inside the box from -24 to 24 on both axes.
- Each port lies on the symbol's drawn outline, so pipes visibly meet the symbol.
- The loader rejects unknown keys.

Colors and stroke widths are not in the library. The renderer strokes each symbol with its layer's `renderColor` and the style profile's `symbol_stroke_width`. `"fill": true` fills the shape with that same color, and `"fill": false` leaves it unfilled.

## Coordinates and placement

Geometry and ports use symbol-local pixels. The origin is the symbol's `anchor`. Y points down, as it does on the page.

A symbol object is placed with `transform="translate(ax ay) rotate(r) scale(s)"`, where `(ax, ay)` is `anchor`, `r` is `rotationDegrees`, and `s` is the style profile's `symbol_scale`. For `piping-default@1.0.0`, `s` is 1. A port at local `(px, py)` lands on the page at:

```text
x = ax + s * (px * cos(r) - py * sin(r))
y = ay + s * (px * sin(r) + py * cos(r))
```

Positive `r` turns clockwise on screen. The renderer uses this formula to draw the unresolved ring for a port whose node ID is `null`.

In `valve-inline`, the `ball_valve` anchor is `(100, 100)` with rotation 0. So `inlet` lands on the junction at `(80, 100)` and `outlet` on the junction at `(120, 100)`.

## Frozen symbols for `piping-symbols@1.0.0`

| Symbol ID | Port | Local x | Local y | Required |
| --- | --- | --- | --- | --- |
| `ball_valve` | `inlet` | -20 | 0 | yes |
| `ball_valve` | `outlet` | 20 | 0 | yes |
| `elbow_fitting` | `a` | -20 | 0 | yes |
| `elbow_fitting` | `b` | 0 | -20 | yes |
| `endpoint` | `pipe` | 0 | 0 | yes |
| `tee_fitting` | `run_a` | -20 | 0 | yes |
| `tee_fitting` | `run_b` | 20 | 0 | yes |
| `tee_fitting` | `branch` | 0 | -20 | yes |
| `unknown` | `port_1` | -20 | 0 | no |
| `unknown` | `port_2` | 0 | -20 | no |
| `unknown` | `port_3` | 20 | 0 | no |
| `unknown` | `port_4` | 0 | 20 | no |

What each symbol is for:

- **`ball_valve`:** an inline valve between two junctions 40 px apart.
- **`tee_fitting`:** a tee that the scene represents explicitly. A structural tee junction with no symbol object does not get this symbol.
- **`elbow_fitting`:** an elbow that the scene represents explicitly. A structural elbow is drawn only as the corner its pipes form.
- **`endpoint`:** a cap at a pipe end. Its anchor sits on the end junction.
- **`unknown`:** a placeholder for a symbol that was detected but not identified. Any of its ports may be connected or left out.

## Rendering in SVG

Only symbols that a scene uses are written into `<defs>`, each as `<symbol id="sym-{id}" overflow="visible">`. The `overflow` attribute is required: without it, resvg clips geometry at negative local coordinates. Each symbol object is a `<use href="#sym-{id}">` in the `symbols` group.
