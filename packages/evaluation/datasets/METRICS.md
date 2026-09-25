# Evaluation definitions v1

All geometric distances use rectified-page pixels. Match predictions to reference objects one-to-one, report unmatched counts, and pin any matching tolerance in the evaluation run configuration before inspecting held-out results. Report synthetic and real results separately.

| Measure | Definition |
|---|---|
| Route centerline recall | Reference centerline length within the pinned pixel distance of a matched predicted route, divided by total reference route length. Also report precision using predicted length. |
| Endpoint error | Euclidean pixel distance for matched route endpoints; report median, p95, and page-diagonal-normalized values. Unmatched endpoints are counted separately. |
| Angle error | Smallest absolute angle difference modulo 180 degrees for matched straight segments. |
| Topology precision/recall | One-to-one matched nodes and edges, with connectivity determined by shared node IDs and symbol ports. Report false confirmed connections and missed junctions separately. |
| OCR CER/WER | Character/word Levenshtein distance divided by reference character/word count. Report empty-reference cases separately. Engineering term accuracy uses an explicitly versioned normalization dictionary. |
| Symbols | Per-class precision and recall after spatial matching; report center-position error in pixels. Unknown classes stay in the denominator. |
| Dimensions | Exact parsed value and unit accuracy, plus associated geometry ID accuracy, reported both separately and as a tuple. Unparsed values are misses. |
| Review burden | Wall-clock reviewer minutes and count of semantic corrections per page, including unresolved items at stop time. |
| Critical errors | Individually list false confirmed pipe connections, wrong confirmed valve types, and wrong confirmed dimension values with scene IDs and source evidence. |

Aggregate by page and report page-bootstrap confidence intervals when enough real labeled pages exist. Choose numeric tolerances, release thresholds, and an acceptable review burden before Run 17 opens the frozen test split. The two current real samples are unlabeled and provide no accuracy evidence.
