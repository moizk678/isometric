"""Validate text candidate artifacts."""

from __future__ import annotations

from isometric_pipeline.ocr.artifact import TextCandidatesMetadata


def validate_text_candidates(
    metadata: TextCandidatesMetadata,
    *,
    region_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for candidate in metadata.candidates:
        if candidate.id in seen:
            errors.append(f"duplicate text candidate id: {candidate.id}")
        seen.add(candidate.id)
        if candidate.region_id not in region_ids:
            errors.append(f"unknown region id: {candidate.region_id}")
        if candidate.status != "unreadable" and not (candidate.raw_text or "").strip():
            errors.append(f"empty rawText for readable candidate {candidate.id}")
        if not candidate.crop_uri:
            errors.append(f"missing cropUri for {candidate.id}")
    for item in metadata.review_items:
        if item.text_candidate_id:
            if item.text_candidate_id not in seen:
                errors.append(
                    f"review item references missing candidate {item.text_candidate_id}"
                )
    return errors
