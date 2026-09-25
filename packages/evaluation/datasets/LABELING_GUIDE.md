# Labeling guide v1

Use rectified-page pixel coordinates for geometry. Preserve raw input coordinates and the source-to-page transform when evidence is traced to a crop. Keep source images immutable and identify each annotation version separately from the image checksum.

- **Route centerlines:** Trace the center of each visible pipe stroke as an ordered polyline. End at visible endpoints, fittings, and junctions; do not infer hidden continuations. Keep color/layer if visible. Mark uncertain spans as unknown.
- **Crossing versus junction:** A pixel intersection alone is not connectivity. Give a junction a shared node only when a connection mark, continuous branch evidence, or reviewer decision supports it. Otherwise use distinct route IDs and record a crossing candidate.
- **Symbols:** Bound the visible mark, classify only against the approved profile vocabulary, and record orientation and named ports separately from appearance. Use `unknown` when the class or connectivity is unclear.
- **Text:** Transcribe what is visible, preserving case, punctuation, abbreviations, and uncertainty. Store normalized engineering vocabulary separately; do not silently repair handwriting.
- **Dimensions:** Record the literal text, parsed value and unit when unambiguous, the dimension line or arrows, and the associated geometry ID only with evidence. Never convert a dimension into image scale by default.
- **Unknown marks:** Keep a source region, candidate types, reason for uncertainty, and reviewer status. Do not omit a visible mark just because it is hard to interpret.

Two reviewers should adjudicate critical connectivity, valve type, and dimension-value disagreements before an annotation is marked `reviewed`. Never place draft labels in a frozen test set.
