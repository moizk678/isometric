# Hand-Drawn Engineering Drawing to Clean Digital SVG System

For the implementation-ready service boundaries, data contracts, APIs, and
delivery phases, see [implementation_architecture.md](implementation_architecture.md).
The product interface follows [system-design/design.md](system-design/design.md)
and its component/foundation guidance in product mode.

## 1. Purpose

This document defines a complete system for converting **hand-drawn, hand-annotated engineering sketches** into **clean, sharp, editable digital SVG drawings**.

The target input is not a normal photograph or logo. It is a structured technical drawing that may contain:

- hand-drawn lines and pipe routes
- isometric or orthographic geometry
- handwritten dimensions
- handwritten labels and engineering notes
- colored line systems
- symbols such as valves, drops, elbows, arrows, connection points, blocks, and equipment markers
- graph or isometric paper in the background
- imperfections such as skew, camera distortion, shadows, faint strokes, inconsistent line weight, erasures, and annotations crossing geometry

The expected output is a **semantically reconstructed technical SVG**, not a literal pixel trace.

The generated SVG should contain:

- clean vector linework
- snapped geometry
- normalized line thickness
- standardized digital symbols
- typed digital text replacing handwriting
- editable dimensions and arrows
- grouped layers by engineering meaning
- preserved color coding where useful
- metadata and confidence information
- traceability back to the original image

---

# 2. Core Principle

A conventional image-to-SVG tracer is not sufficient for this use case.

A normal tracer performs something similar to:

```text
Image
  ↓
Edge detection
  ↓
Pixel contours
  ↓
Thousands of path points
  ↓
SVG
```

That approach produces an SVG that may look similar at first glance, but it does not understand the drawing.

For engineering sketches, the correct approach is:

```text
Hand-drawn image
       ↓
Image cleanup and normalization
       ↓
Drawing region detection
       ↓
Grid / paper removal
       ↓
Stroke and symbol segmentation
       ↓
Handwriting detection and transcription
       ↓
Optional LLM/Vision interpretation of ambiguous crops
       ↓
Geometry reconstruction
       ↓
Engineering symbol interpretation
       ↓
Topology reconstruction
       ↓
Dimension and annotation understanding
       ↓
Semantic scene graph
       ↓
SVG generation
       ↓
Render-and-compare validation
       ↓
Human review for uncertain items
       ↓
Final editable digital SVG
```

The system should therefore be treated as an **engineering sketch interpretation and reconstruction engine**, not simply an SVG converter.

---

# 3. Scope of the System

## 3.1 Primary Input Types

The system should support:

- JPG
- JPEG
- PNG
- scanned PDF pages
- camera-captured sketches
- screenshots of sketches
- exported images from note-taking applications

## 3.2 Primary Drawing Types

Initial supported drawings should include:

- piping isometric sketches
- simple process routing sketches
- mechanical line drawings
- plant layout sketches
- construction routing sketches
- electrical routing sketches
- equipment connection sketches
- hand-marked redlines
- handwritten field modifications

The strongest initial use case should be **piping isometric and engineering routing sketches**.

## 3.3 Output Types

Primary output:

```text
SVG
```

Optional later outputs:

```text
DXF
DWG-compatible export
PDF
PNG preview
JSON semantic model
```

---

# 4. Example Input Characteristics

A drawing such as the provided example contains multiple information classes at the same time.

### Geometry

- long pipe routes
- sloped or isometric segments
- vertical drops
- corners and elbows
- connection endpoints

### Color coding

Different pipe routes may be shown using:

- yellow
- cyan
- green
- black or gray

The system should preserve these colors unless the user requests normalization.

### Dimensions

Examples may include handwritten values such as:

```text
4'
3'
20'
25'
1'
```

These should become structured dimension objects rather than plain text when possible.

### Handwritten notes

Examples may include notes like:

```text
Drops x6 conn. to machines
Drops from mains
Clamp to strut on floor
Block + bleed ball valve
Leave thread conn. for maintenance
```

These should be transcribed and converted into clean typed SVG text.

### Symbols

The image may contain hand-drawn symbols representing:

- valves
- drops
- fittings
- connection points
- direction arrows
- machine connections
- maintenance points

The system must identify and redraw them using reusable digital symbols.

---

# 5. Overall System Architecture

A practical production architecture is:

```text
┌────────────────────────────────────────────┐
│                Frontend                    │
│             Next.js / React                │
│                                            │
│ Upload image                               │
│ Review original vs digital drawing         │
│ Correct OCR / symbols                      │
│ Edit colors / dimensions / labels          │
│ Export SVG                                 │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────┐
│             Processing API                 │
│               FastAPI                      │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────┐
│        Drawing Interpretation Engine       │
│                                            │
│ 1. Image normalization                     │
│ 2. Page / drawing detection                │
│ 3. Perspective correction                  │
│ 4. Grid removal                            │
│ 5. Stroke segmentation                     │
│ 6. Text detection                          │
│ 7. Handwriting recognition                 │
│ 8. Geometry extraction                     │
│ 9. Topology and symbol candidates          │
│10. Optional LLM/Vision interpretation      │
│11. Symbol/annotation association           │
│12. Semantic scene creation                 │
│13. SVG generation                          │
│14. Validation                              │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────┐
│           Data / Review Layer              │
│                                            │
│ Supabase Cloud PostgreSQL                  │
│ Object storage                             │
│ Processing metadata                        │
│ Confidence scores                          │
│ User corrections                          │
│ Version history                            │
└────────────────────────────────────────────┘
```

---

# 6. Processing Pipeline

# Stage 1 — Input Ingestion

The system first loads the source without modifying the original.

Store:

```json
{
  "document_id": "doc_123",
  "source_file": "drawing.jpg",
  "width": 1148,
  "height": 1279,
  "mime_type": "image/jpeg",
  "rotation": 0,
  "source_hash": "..."
}
```

The original must always remain available for audit and comparison.

---

# Stage 2 — Image Normalization

The purpose of normalization is to create a clean analysis image while preserving the source.

Operations may include:

1. EXIF orientation correction
2. white balance correction
3. local contrast enhancement
4. mild denoising
5. shadow correction
6. brightness normalization
7. sharpening if required
8. conversion to multiple color spaces

Useful representations:

```text
RGB
HSV
LAB
Grayscale
Binary ink mask
Edge map
```

Recommended libraries:

```text
OpenCV
Pillow
scikit-image
NumPy
```

---

# Stage 3 — Page and Drawing Boundary Detection

If the user captures the drawing using a phone camera, the sheet may be tilted.

The system should detect the paper boundary and perform a perspective transform.

Pipeline:

```text
Image
 ↓
Large rectangular contour detection
 ↓
Four corner estimation
 ↓
Perspective transformation
 ↓
Top-down normalized page
```

If no reliable page boundary is found, preserve the original orientation and proceed with a lower confidence score.

---

# Stage 4 — Grid and Paper Background Removal

This is especially important for isometric paper.

The grid is not engineering geometry and should not appear in the final SVG.

The engine should identify repetitive faint lines based on:

- low contrast
- regular spacing
- common orientation
- periodicity
- consistent thin width
- extension across most of the page

For isometric paper, typical orientations are around:

```text
0°
+30° / +60°
-30° / -60°
```

depending on the grid style.

Possible techniques:

- Hough line detection
- Fourier frequency analysis
- morphological line extraction
- color/lightness thresholding
- periodic-pattern detection

The result should be two representations:

```text
background/grid mask
drawing ink mask
```

The grid may optionally be retained as a display overlay in the UI, but it should normally not be exported.

---

# Stage 5 — Foreground Ink and Stroke Segmentation

The drawing contains different kinds of ink.

The system should separate:

```text
geometry strokes
text strokes
symbol strokes
dimension strokes
arrows
colored systems
```

Color should be used when available.

For example:

```text
yellow pipe system
cyan pipe system
green pipe system
black annotations
```

Use LAB or HSV color clustering instead of pure RGB thresholds.

Example:

```python
clusters = cluster_pixels_in_lab(image)
```

Each major colored line system can become its own vector layer.

---

# Stage 6 — Handwriting Region Detection

The engine must identify text regions before geometry reconstruction so that handwriting is not mistaken for pipe lines.

Detect text using:

- connected component geometry
- stroke density
- irregular baselines
- local OCR detection models
- text-region detectors

Each region should have:

```json
{
  "bbox": [x, y, width, height],
  "rotation": -11.2,
  "type": "handwritten_text",
  "confidence": 0.91
}
```

---

# Stage 7 — Handwriting Recognition

This stage converts handwriting to digital text.

This is more difficult than ordinary printed OCR.

Recommended strategy:

```text
Detected handwritten region
      ↓
Crop and deskew
      ↓
Handwriting recognition model
      ↓
Engineering vocabulary correction
      ↓
Contextual language correction
      ↓
Confidence scoring
```

Suitable model classes include:

- TrOCR-style handwriting models
- handwritten text recognition transformers
- domain-fine-tuned OCR models

An LLM/Vision API may inspect a cropped, ambiguous annotation and rank OCR
alternatives. It should not replace the primary OCR pass or silently invent
unreadable words. The service should be optional so that processing and manual
review still work when it is unavailable.

Do not allow the language model to silently invent unreadable words.

Each transcription should include alternatives.

Example:

```json
{
  "raw": "Block + Bleed ball valve",
  "normalized": "Block + Bleed Ball Valve",
  "confidence": 0.93,
  "alternatives": [
    "Block + Bleed Ball Valve",
    "Block + Bleed Valve"
  ]
}
```

Low confidence text must be marked for human review.

---

# Stage 8 — Engineering Vocabulary Normalization

A generic OCR model may misread technical terminology.

Create an engineering dictionary containing terms such as:

```text
ball valve
block and bleed
flange
threaded connection
NPT
mains
branch
machine
drop
elbow
tee
clamp
strut
floor
maintenance
connection
pipe
line
vent
drain
```

The correction system should rank candidates using:

```text
OCR confidence
engineering vocabulary
nearby geometry
nearby symbols
document-level vocabulary
```

For example:

```text
"ball value"
```

may be normalized to:

```text
"ball valve"
```

but only when confidence is sufficient.

---

# Stage 9 — Dimension Recognition

Dimensions should be treated as structured engineering objects.

Recognize:

```text
4'
3'
20'
25'
1'
```

and associate them with nearby dimension lines and arrowheads.

A dimension object might be:

```json
{
  "type": "linear_dimension",
  "value": 20,
  "unit": "ft",
  "start": [x1, y1],
  "end": [x2, y2],
  "text_position": [xt, yt],
  "confidence": 0.95
}
```

The final SVG should redraw the dimension using proper:

- extension lines
- arrowheads
- dimension line
- typed dimension text

---

# Stage 10 — Stroke Centerline Extraction

A hand-drawn pipe line is usually several pixels thick and irregular.

The goal is not to trace both edges.

The engine should infer the **centerline**.

Pipeline:

```text
stroke mask
   ↓
noise cleanup
   ↓
morphological thinning / skeletonization
   ↓
centerline graph
   ↓
line / curve fitting
```

Useful operations:

```text
skeletonization
medial axis
Douglas-Peucker simplification
Hough line fitting
least-squares line fitting
Bezier fitting
```

This converts a shaky hand stroke into a mathematically clean line.

---

# Stage 11 — Isometric Geometry Detection

For piping drawings, many segments are expected to follow isometric axes.

Instead of preserving small hand-drawing errors, the engine should identify intended orientation.

Example allowed directions:

```text
vertical
30° diagonal
150° diagonal
```

or whichever axes match the detected isometric grid.

For every line candidate, determine the nearest intended direction.

Example:

```text
Detected angle: 58.1°
Expected isometric axis: 60°
Difference: 1.9°
```

If below a configurable threshold, snap it to 60°.

This is a major difference between engineering reconstruction and generic vector tracing.

---

# Stage 12 — Line Segment Reconstruction

Each centerline is simplified into clean primitives:

```text
LineSegment
Polyline
BezierCurve
Arc
```

For a technical sketch, prefer straight lines and arcs whenever possible.

Example:

```json
{
  "type": "line",
  "start": [320, 612],
  "end": [721, 889],
  "orientation": "iso_axis_1",
  "stroke": "yellow",
  "stroke_width": 3
}
```

---

# Stage 13 — Junction and Topology Reconstruction

The system must determine what connects to what.

This is critical.

A drawing is not merely a set of lines. It is a graph.

Represent geometry as:

```text
Nodes = connection / elbow / tee / endpoint / valve
Edges = pipe segments
```

Example:

```text
Node A ─ Pipe 1 ─ Node B ─ Pipe 2 ─ Node C
                  │
                  └─ Drop 1
```

A topology model may look like:

```json
{
  "nodes": [
    {"id": "N1", "type": "elbow", "x": 320, "y": 640},
    {"id": "N2", "type": "valve", "x": 719, "y": 890}
  ],
  "edges": [
    {
      "id": "P1",
      "from": "N1",
      "to": "N2",
      "system": "yellow"
    }
  ]
}
```

Topology should be reconstructed before final SVG generation.

---

# Stage 14 — Symbol Detection

Engineering symbols should be detected independently of normal line geometry.

Initial symbol library may include:

```text
ball valve
block valve
bleed valve
tee
elbow
flange
threaded connection
end cap
connection point
flow arrow
drop
riser
machine connection
```

Detection can use a combination of:

```text
computer vision template matching
shape descriptors
small object detector
context from nearby text
context from connected pipes
```

For ambiguous symbols, an LLM/Vision API may rank a constrained list of
symbol candidates using a source crop, nearby OCR text, and the symbol
library. Its answer is evidence for review, not an instruction to change
pipe geometry or connectivity.

For example, a handwritten symbol next to the note:

```text
Block + Bleed Ball Valve
```

should substantially increase the probability that the nearby mark represents a valve assembly.

---

# Stage 15 — Symbol Standardization

Once recognized, the original shaky symbol should not simply be traced.

Replace it with a clean standard symbol.

Example semantic object:

```json
{
  "type": "ball_valve",
  "position": [805, 910],
  "rotation": 60,
  "connected_pipe": "P12",
  "source_confidence": 0.88
}
```

The renderer can then use a reusable SVG component:

```xml
<use href="#symbol-ball-valve" ... />
```

This makes the output consistent and editable.

---

# Stage 16 — Arrow Detection

Arrows appear in:

- dimensions
- notes
- flow directions
- callouts

The engine should identify:

```text
arrow shaft
arrowhead
arrow target
```

Callout arrows should be linked to their corresponding text.

Example:

```json
{
  "type": "callout",
  "text": "Clamp to strut on floor",
  "target": "pipe_segment_P4",
  "leader_path": [[420, 720], [501, 754]]
}
```

---

# Stage 17 — Text-to-Object Association

Recognizing the text alone is insufficient.

The system must understand what the note refers to.

Signals include:

- nearest object
- arrow endpoint
- leader line
- direction of text
- bounding-box proximity
- symbol context
- line color

This creates semantic relationships such as:

```text
"Clamp to strut on floor"
        ↓
associated with
        ↓
yellow pipe segment P7
```

---

# Stage 18 — Color and Layer Interpretation

Colors may carry engineering meaning.

Instead of simply storing RGB values, create named visual layers.

Example:

```json
{
  "layer": "pipe_system_1",
  "source_color": "#E8D54D",
  "normalized_color": "#E3C92E"
}
```

The user can later rename this layer:

```text
Compressed Air
Gas
Water
Process Line
```

The UI should permit recoloring without changing geometry.

---

# Stage 19 — Semantic Scene Graph

Before generating SVG, convert the entire drawing into a machine-readable intermediate representation.

Example:

```json
{
  "document": {
    "type": "piping_isometric",
    "units": "ft"
  },
  "layers": [
    {
      "id": "L1",
      "name": "yellow_pipe_system",
      "color": "#E3D140"
    }
  ],
  "objects": [
    {
      "id": "P1",
      "type": "pipe_segment",
      "geometry": {
        "start": [120, 300],
        "end": [430, 480]
      },
      "layer": "L1"
    },
    {
      "id": "V1",
      "type": "ball_valve",
      "position": [430, 480]
    },
    {
      "id": "T1",
      "type": "annotation",
      "text": "Block + Bleed Ball Valve",
      "target": "V1"
    }
  ]
}
```

This semantic model should be treated as the primary document representation.

SVG becomes one rendering of this model.

---

# 7. SVG Generation

The final SVG should be structured and editable.

Do not create one giant `<path>`.

A recommended hierarchy:

```xml
<svg>

  <defs>
    <marker id="arrowhead" />
    <symbol id="ball-valve" />
    <symbol id="tee" />
    <symbol id="connection" />
  </defs>

  <g id="pipe-systems">
    <g id="yellow-system">
      ...
    </g>
    <g id="cyan-system">
      ...
    </g>
    <g id="green-system">
      ...
    </g>
  </g>

  <g id="symbols">
      ...
  </g>

  <g id="dimensions">
      ...
  </g>

  <g id="annotations">
      <text>...</text>
  </g>

</svg>
```

---

# 8. Digital Text Rendering

Handwriting should be replaced by actual SVG text where possible.

Example:

```xml
<text
  x="680"
  y="220"
  font-family="Arial, Helvetica, sans-serif"
  font-size="18">
  Drops ×6 — Connect to Machines
</text>
```

Advantages:

- searchable
- selectable
- editable
- readable
- accessible
- exportable

Do not convert typed text back into vector outlines unless the user explicitly requests it.

---

# 9. Annotation Normalization Rules

The engine may improve capitalization and spacing without changing meaning.

Example:

```text
Source:
drops x6 conn. to machines

Normalized:
Drops ×6 — Connect to Machines
```

Another example:

```text
Source:
leave thread conn. for maintenance

Normalized:
Leave Threaded Connection for Maintenance
```

However, the system should preserve both values:

```json
{
  "recognized_text": "leave thread conn. for maintenance",
  "normalized_text": "Leave Threaded Connection for Maintenance"
}
```

The user should be able to switch between them.

---

# 10. Geometry Snapping Engine

The system should detect intended geometry rather than reproduce drawing imperfections.

Possible snapping targets:

```text
horizontal
vertical
isometric axis A
isometric axis B
parallel to nearby segment
perpendicular to nearby segment
shared junction
shared endpoint
same line
```

Example logic:

```python
if angle_difference(segment.angle, iso_axis) < 4.0:
    segment.angle = iso_axis
```

Snapping threshold should be configurable.

---

# 11. Coordinate Calibration

If dimensions are present, the system may estimate drawing scale.

Example:

If a line visually measures 400 pixels and is annotated as:

```text
20 ft
```

then:

```text
20 px ≈ 1 ft
```

This enables consistency checks across the drawing.

Important: because hand sketches are often not truly to scale, inferred scale must be treated as approximate unless multiple consistent dimensions confirm it.

---

# 12. Confidence Model

Every interpreted object should carry confidence.

Example:

```json
{
  "object_id": "V3",
  "type": "ball_valve",
  "confidence": 0.71
}
```

Suggested ranges:

```text
0.90 – 1.00   Very high confidence
0.75 – 0.89   High confidence
0.50 – 0.74   Review recommended
0.00 – 0.49   Human confirmation required
```

Confidence should be calculated separately for:

```text
text recognition
symbol recognition
geometry orientation
line connectivity
dimension association
annotation association
```

---

# 13. Human-in-the-Loop Review

For engineering drawings, fully automatic reconstruction should not be treated as perfect.

A review interface is highly recommended.

The interface should display:

```text
Original image            Generated SVG
────────────────          ─────────────
hand sketch               clean drawing
```

Clicking an object in either view should highlight its counterpart.

Review panel:

```text
Object type: Ball Valve
Confidence: 71%
Detected text: Block + Bleed Ball Valve
Connected pipe: Yellow System

[Confirm]
[Change Symbol]
[Edit Text]
[Delete]
```

This is especially important for ambiguous field sketches.

---

# 14. Render-and-Compare Validation

Once a candidate SVG is created, rasterize it and compare against the original drawing.

```text
Semantic Model
      ↓
Candidate SVG
      ↓
Rasterized candidate
      ↓
Comparison with source
```

Possible loss function:

```text
Ltotal =
    0.25 Lgeometry
  + 0.20 Ledge
  + 0.15 Lcolor
  + 0.15 Ltopology
  + 0.10 Ltext_location
  + 0.10 Lsymbol_location
  + 0.05 Lcomplexity
```

Unlike logo vectorization, pixel-perfect similarity should not dominate the score.

A technically correct cleaned drawing may deliberately differ from the hand-drawn source.

For this use case, higher priority should be given to:

```text
connectivity
geometry
meaning
annotations
symbols
```

rather than exact handwritten appearance.

---

# 15. Important Difference from General Image Vectorization

The previously defined general PNG/JPG-to-SVG pipeline remains useful, but this engineering use case requires additional semantic modules.

## General icon vectorization

```text
Image
→ regions
→ contours
→ primitive detection
→ gradients
→ SVG
```

## Engineering drawing vectorization

```text
Image
→ paper cleanup
→ grid removal
→ handwriting extraction
→ OCR
→ stroke centerlines
→ engineering geometry snapping
→ symbol recognition
→ topology graph
→ dimension extraction
→ annotation association
→ semantic model
→ standardized SVG
```

Therefore, the system should have different processing modes.

Recommended modes:

```text
Logo / Icon
Line Art
Engineering Sketch
Piping Isometric
General Diagram
```

The user can either choose the mode, or the system can classify it automatically.

---

# 16. Recommended Technology Stack

## Frontend

```text
Next.js
React
TypeScript
Tailwind CSS
SVG.js or native SVG DOM
Konva.js / Fabric.js optional for editor interactions
```

Use [system-design/design.md](system-design/design.md) as the UI design-system
entry point. The upload, review workbench, correction controls, and responsive
states should use its routed product-mode components and accessibility rules.
Engineering line colors remain drawing data and should not be replaced by UI
status colors.

## Processing Backend

```text
Python
FastAPI
```

## Computer Vision

```text
OpenCV
scikit-image
NumPy
SciPy
```

## OCR / Handwriting

Possible implementation layers:

```text
handwriting OCR model
vision-language model
engineering vocabulary correction model
```

## AI / ML

Potential components:

```text
object detection model
symbol classifier
vision-language model
handwriting recognizer
```

## SVG Generation

```text
svgwrite
lxml
custom SVG serializer
```

A custom serializer is preferred once the product matures.

## SVG Rendering / Validation

```text
resvg
CairoSVG
```

## Database

```text
Supabase Cloud hosted PostgreSQL
```

FastAPI and the worker access the database server-side. This choice does not
imply using Supabase for artifact storage, authentication, or the job queue.

## Storage

```text
S3-compatible object storage
```

---

# 17. AI and Classical Computer Vision Responsibilities

Do not give every task to one AI model.

A hybrid architecture is stronger.

## Classical computer vision is best suited for

```text
page boundaries
perspective correction
line detection
centerline extraction
color segmentation
junction detection
angle measurement
geometry snapping
contour analysis
```

## AI models are best suited for

```text
handwriting recognition
engineering text interpretation
symbol classification
ambiguous mark interpretation
document classification
annotation association
```

## LLM/Vision API interpretation lane

OpenCV, OCR, and the deterministic geometry engine should perform most of the
work. An LLM/Vision API is an optional escalation for messy annotations or
ambiguous drawing marks. Send only bounded source crops and relevant OCR,
symbol, and topology candidates. Require a structured response containing a
candidate ID, evidence, uncertainty, and an `unknown` option. Validate the
response against the candidate set before using it.

The API must not supply SVG paths, coordinates, dimensions, line endpoints,
junctions, or connectivity. It must not silently override legible OCR or a
reviewed user correction. Any interpretation that changes engineering meaning
must be flagged for review. Provider outages, timeouts, or invalid responses
fall back to the classical pipeline and human review.

Store the provider/model version, prompt version, crop reference, response,
and provenance with each suggestion. Minimize uploaded image data and allow an
organization to disable external vision calls.

## Deterministic geometry engine is best suited for

```text
line snapping
parallelism
isometric axes
junction reconstruction
dimensions
SVG construction
```

This separation improves reliability.

---

# 18. Core Data Model

A useful object model could be:

```typescript
interface DrawingDocument {
  id: string;
  drawingType: string;
  units?: string;
  sourceImage: SourceImage;
  layers: DrawingLayer[];
  objects: DrawingObject[];
  relationships: Relationship[];
  confidence: number;
}
```

Objects:

```typescript
type DrawingObject =
  | PipeSegment
  | Junction
  | Valve
  | Fitting
  | Dimension
  | Annotation
  | Callout
  | Arrow
  | EquipmentConnection
  | UnknownSymbol;
```

Example pipe segment:

```typescript
interface PipeSegment {
  id: string;
  type: "pipe_segment";
  start: Point;
  end: Point;
  layerId: string;
  originalAngle: number;
  snappedAngle: number;
  confidence: number;
}
```

---

# 19. Unknown Object Handling

The engine must never force every mark into a known class.

If it cannot confidently classify an object:

```json
{
  "type": "unknown_symbol",
  "bbox": [x, y, w, h],
  "confidence": 0.31,
  "source_crop": "..."
}
```

The UI should display:

```text
Unrecognized Symbol
Please choose:

[Valve]
[Connection]
[Drop]
[Elbow]
[Other]
```

User corrections should become training data.

---

# 20. Learning From User Corrections

Each correction should be logged.

Example:

```json
{
  "predicted": "tee",
  "corrected": "ball_valve",
  "source_crop_id": "crop_221",
  "drawing_type": "piping_isometric"
}
```

Over time this becomes a valuable domain-specific dataset.

It can be used to fine-tune:

- symbol recognition
- handwriting recognition
- annotation association
- drawing classification

---

# 21. Processing API

Implementation endpoint (multipart upload):

```http
POST /api/v1/documents
```

Form fields:

```text
file: uploaded image bytes
profile_id: piping_isometric
options: {remove_grid, normalize_text, snap_geometry, preserve_colors}
```

Initial response:

```json
{
  "document_id": "doc_123",
  "job_id": "job_123",
  "status": "queued"
}
```

Results:

```http
GET /api/v1/jobs/job_123
```

Response:

```json
{
  "status": "succeeded",
  "document_id": "doc_123",
  "revision_id": "rev_123",
  "revision_review_state": "review_required",
  "review_items": 4
}
```

The scene and generated artifacts are retrieved by document/revision endpoints
defined in the implementation architecture. The job response does not embed
large files or raw provider output.

---

# 22. Processing Stages Exposed to the UI

The frontend can display progress such as:

```text
✓ Image uploaded
✓ Correcting page perspective
✓ Removing grid
✓ Detecting pipe routes
✓ Reading handwritten notes
✓ Identifying symbols
✓ Reconstructing geometry
✓ Creating digital annotations
✓ Generating SVG
✓ Checking output
```

---

# 23. SVG Editing Experience

After conversion, the user should be able to edit the drawing.

Useful editing operations:

```text
move annotation
edit annotation text
change pipe color
change line thickness
change symbol
move symbol
connect / disconnect pipes
snap line
add pipe
remove pipe
edit dimension
add dimension
rotate symbol
```

Because the SVG was generated from semantic objects, editing should modify the underlying scene model and regenerate SVG rather than directly editing arbitrary path strings.

---

# 24. Quality Metrics

A good engineering vectorizer should not be evaluated by only one image similarity metric.

Measure:

## Geometry accuracy

```text
line endpoint error
angle error
junction accuracy
centerline deviation
```

## OCR accuracy

```text
Character Error Rate
Word Error Rate
engineering term accuracy
```

## Topology accuracy

```text
correct pipe connections
missed junctions
false connections
```

## Symbol accuracy

```text
symbol classification precision
symbol classification recall
position accuracy
```

## Dimension accuracy

```text
value accuracy
unit accuracy
correct geometry association
```

## SVG quality

```text
number of unnecessary nodes
file size
editability
rendering correctness
```

---

# 25. Acceptance Criteria

For an initial production-quality piping sketch system, suggested targets are:

```text
Major pipe centerlines detected:       > 95%
Major pipe connectivity accuracy:      > 95%
Dimension transcription accuracy:      > 95%
General handwriting transcription:     > 90%
Known symbol detection:                > 90%
Grid removal without geometry loss:    > 97%
```

These should be validated against a real domain dataset.

---

# 26. Edge Cases

The system must be designed for imperfect field documents.

Examples:

- faded pencil
- multiple pen colors
- notes crossing pipes
- arrows touching text
- overwritten measurements
- photographed pages with shadows
- folded paper
- grid lines darker than drawing lines
- inconsistent isometric angles
- missing dimensions
- partially erased symbols
- very small handwriting
- abbreviations
- unknown company-specific symbols

For uncertain cases, preserve the source crop and request user review rather than hallucinating.

---

# 27. Domain-Specific Symbol Library

A production implementation should include a configurable symbol library.

Suggested schema:

```json
{
  "id": "ball_valve",
  "name": "Ball Valve",
  "category": "valve",
  "aliases": [
    "ball valve",
    "BV"
  ],
  "svg_template": "...",
  "connection_points": [
    "left",
    "right"
  ]
}
```

Users or organizations should later be able to add their own symbol standards.

---

# 28. Document Modes

The system should support domain profiles.

Example:

```text
Profile: Piping Isometric

Allowed geometry:
- vertical
- iso axis A
- iso axis B

Known symbols:
- elbow
- tee
- valve
- flange
- drop
- threaded connection

OCR dictionary:
- NPT
- valve
- main
- drop
- clamp
- strut
```

Other profiles can later be introduced for electrical, construction, HVAC, etc.

---

# 29. Proposed Internal Pipeline in Pseudocode

```python
def convert_engineering_sketch(image):

    source = load_original(image)

    normalized = normalize_image(source)

    page = detect_and_rectify_page(normalized)

    drawing_type = classify_drawing(page)

    grid_model = detect_grid(page, drawing_type)
    clean_page = suppress_grid(page, grid_model)

    color_layers = segment_ink_colors(clean_page)

    text_regions = detect_handwriting(clean_page)
    symbol_regions = detect_symbol_candidates(clean_page)

    geometry_image = remove_regions(
        clean_page,
        text_regions + symbol_regions
    )

    text_objects = []
    for region in text_regions:
        transcription = recognize_handwriting(region)
        normalized_text = normalize_engineering_text(transcription)
        text_objects.append(
            build_annotation(region, transcription, normalized_text)
        )

    centerlines = extract_centerlines(geometry_image)

    lines = fit_geometric_primitives(centerlines)

    axes = infer_drawing_axes(lines, grid_model)

    snapped_lines = snap_to_engineering_axes(lines, axes)

    junctions = detect_junctions(snapped_lines)

    topology = build_connectivity_graph(snapped_lines, junctions)

    symbol_candidates = classify_symbol_candidates(
        symbol_regions, topology, text_objects
    )

    interpretation_suggestions = interpret_ambiguous_crops_with_vision(
        page=clean_page,
        text_objects=text_objects,
        symbol_candidates=symbol_candidates,
        topology_candidates=topology,
        allowed_labels=get_profile_symbol_labels(drawing_type),
    )  # Optional; returns evidence and candidate IDs, never geometry.

    symbols = resolve_symbol_candidates(
        symbol_candidates, interpretation_suggestions
    )

    dimensions = detect_dimensions(
        clean_page,
        text_objects,
        snapped_lines
    )

    associations = associate_annotations(
        text_objects,
        symbols,
        dimensions,
        snapped_lines,
        interpretation_suggestions
    )

    scene = build_semantic_scene(
        snapped_lines,
        topology,
        symbols,
        dimensions,
        text_objects,
        associations,
        color_layers
    )

    confidence = score_scene(scene)

    svg = render_scene_to_svg(scene)

    preview = rasterize_svg(svg)

    validation = compare_semantic_render(
        source,
        preview,
        scene
    )

    review_items = identify_low_confidence_items(scene)

    return {
        "scene": scene,
        "svg": svg,
        "confidence": confidence,
        "validation": validation,
        "review_items": review_items
    }
```

---

# 30. Recommended MVP

Do not attempt all possible engineering drawings in version one.

A strong MVP should focus on:

```text
Input:
Scanned or photographed piping isometric sketch

Output:
Clean editable SVG
```

MVP features:

1. PNG/JPG upload
2. perspective correction
3. grid removal
4. colored line extraction
5. line centerline detection
6. isometric snapping
7. handwritten note OCR
8. typed annotation replacement
9. basic dimension recognition
10. simple valve / connection symbols
11. SVG output
12. side-by-side review
13. manual corrections

This is sufficient to prove the main technical concept.

---

# 31. Phase 2

After MVP validation:

```text
advanced symbol recognition
custom organization symbol libraries
automatic topology verification
DXF export
PDF input
multi-page documents
redline comparison
version-to-version comparison
scale calibration
engineering rule validation
```

---

# 32. Phase 3

Longer-term capabilities may include:

```text
automatic generation of pipe schedules
BOM extraction
valve schedules
connection lists
machine drop lists
P&ID linking
CAD synchronization
as-built comparison
field drawing digitization workflows
```

At this stage the product is no longer simply an image-to-SVG tool. It becomes an **engineering drawing digitization platform**.

---

# 33. Key Product Differentiator

The main differentiator should be:

> The system reconstructs the intended engineering drawing rather than tracing the imperfections of the handwritten source.

For example, it should convert:

```text
shaky handwritten diagonal line
```

into:

```text
perfect isometric pipe segment
```

and:

```text
handwritten "Block + Bleed ball valve"
```

into:

```text
clean SVG text + standardized valve symbol
```

while maintaining the relationship between the note, symbol, and pipe.

---

# 34. Critical Design Rule

Never silently guess uncertain engineering information.

The system should follow:

```text
High confidence
→ automate

Medium confidence
→ automate + visually flag

Low confidence
→ request confirmation
```

This is especially important because a visually small interpretation mistake can materially change the meaning of an engineering drawing.

---

# 35. Final System Definition

The complete product can be summarized as:

```text
HAND-DRAWN ENGINEERING SKETCH
           │
           ▼
IMAGE NORMALIZATION
           │
           ▼
PAGE + GRID UNDERSTANDING
           │
           ▼
INK / COLOR SEGMENTATION
           │
           ├───────────────┐
           │               │
           ▼               ▼
   GEOMETRY ENGINE     HANDWRITING OCR
           │               │
           ▼               ▼
 ISOMETRIC SNAPPING     TEXT NORMALIZATION
           │               │
           └───────┬───────┘
                   ▼
       SYMBOL CANDIDATES + TOPOLOGY
                   │
                   ├───────────────┐
                   │               ▼
                   │     OPTIONAL LLM/VISION API
                   │     (interpretation only)
                   │               │
                   └───────┬───────┘
                           ▼
                ANNOTATION ASSOCIATION
                   │
                   ▼
          SEMANTIC SCENE GRAPH
                   │
                   ▼
              SVG RENDERER
                   │
                   ▼
             QUALITY CHECK
                   │
                   ▼
             HUMAN REVIEW
                   │
                   ▼
        CLEAN EDITABLE DIGITAL SVG
```

The architecture should be built around the **semantic scene graph**, with SVG treated as the rendering layer. This allows the system to later produce CAD formats, perform engineering checks, generate schedules, and support structured editing without redesigning the entire processing pipeline.
