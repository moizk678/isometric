"""Merge confirmed interpretations from a reviewed revision into a machine candidate."""

from __future__ import annotations

from ..scene.models import DrawingObject, DrawingScene


def overlay_confirmed_objects(
    candidate: DrawingScene,
    reviewed: DrawingScene,
) -> DrawingScene:
    """Replace candidate objects with reviewed snapshots when interpretation is confirmed."""
    reviewed_by_id: dict[str, DrawingObject] = {
        obj.id: obj
        for obj in reviewed.objects
        if obj.interpretation.state == "confirmed"
    }
    if not reviewed_by_id:
        return candidate
    objects: list[DrawingObject] = []
    for obj in candidate.objects:
        pinned = reviewed_by_id.get(obj.id)
        objects.append(pinned if pinned is not None else obj)
    return candidate.model_copy(update={"objects": objects})


def confirmed_object_ids(scene: DrawingScene) -> frozenset[str]:
    return frozenset(
        obj.id for obj in scene.objects if obj.interpretation.state == "confirmed"
    )


def lost_confirmed_edits(
    current: DrawingScene,
    candidate: DrawingScene,
) -> list[dict[str, str]]:
    """Summarize confirmed objects on current that differ or are absent on candidate."""
    candidate_ids = {obj.id for obj in candidate.objects}
    lost: list[dict[str, str]] = []
    for obj in current.objects:
        if obj.interpretation.state != "confirmed":
            continue
        if obj.id not in candidate_ids:
            lost.append({"object_id": obj.id, "reason": "missing_on_candidate"})
            continue
        other = next(c for c in candidate.objects if c.id == obj.id)
        if other.model_dump(mode="json") != obj.model_dump(mode="json"):
            lost.append({"object_id": obj.id, "reason": "differs_on_candidate"})
    return lost
