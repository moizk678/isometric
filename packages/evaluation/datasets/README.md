# Dataset registry

`manifest.schema.json` is the versioned contract. `manifest.template.json` illustrates a complete synthetic entry. Real drawings and their manifests remain under `.private/drawings/`, outside Git. A null `annotation_uri` means the item is unlabeled; `unassigned` split prevents accidental use in calibration or held-out evaluation.

Checksums cover immutable image bytes. Dataset IDs and annotation versions must remain stable when labels change. `LABELING_GUIDE.md` and `METRICS.md` define the evidence and measurement conventions.
