"""Review item carry-forward and revision readiness policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ReviewState = Literal["review_required", "ready"]

_BLOCKING_SEVERITIES = frozenset({"critical", "high"})
_BLOCKING_STATES = frozenset({"open", "acknowledged_unknown"})


@dataclass(frozen=True)
class ReviewItemRow:
    issue_key: str
    object_id: str | None
    relationship_id: str | None
    issue_type: str
    severity: str
    crop_uri: str | None
    proposed_options: list[Any]
    state: str


def row_from_db(row: dict[str, Any]) -> ReviewItemRow:
    options = row.get("proposed_options")
    if options is None:
        options = []
    return ReviewItemRow(
        issue_key=row["issue_key"],
        object_id=row.get("object_id"),
        relationship_id=row.get("relationship_id"),
        issue_type=row["issue_type"],
        severity=row["severity"],
        crop_uri=row.get("crop_uri"),
        proposed_options=list(options),
        state=row["state"],
    )


def derive_review_state(items: list[ReviewItemRow]) -> ReviewState:
    """Ready only when no blocking open or acknowledged_unknown items remain."""
    for item in items:
        if item.state not in _BLOCKING_STATES:
            continue
        if item.severity in _BLOCKING_SEVERITIES:
            return "review_required"
    return "ready"


def items_after_edit(
    parent_items: list[ReviewItemRow],
    *,
    affected_object_ids: set[str],
) -> list[ReviewItemRow]:
    """Carry unresolved items; reopen items tied to edited objects."""
    carried: list[ReviewItemRow] = []
    for item in parent_items:
        if item.state in ("confirmed", "corrected"):
            carried.append(item)
            continue
        if item.state not in ("open", "acknowledged_unknown"):
            continue
        if item.object_id is not None and item.object_id in affected_object_ids:
            carried.append(
                ReviewItemRow(
                    issue_key=item.issue_key,
                    object_id=item.object_id,
                    relationship_id=item.relationship_id,
                    issue_type=item.issue_type,
                    severity=item.severity,
                    crop_uri=item.crop_uri,
                    proposed_options=item.proposed_options,
                    state="open",
                )
            )
        else:
            carried.append(item)
    return carried


def items_after_resolution(
    parent_items: list[ReviewItemRow],
    *,
    issue_key: str,
    new_state: str,
) -> list[ReviewItemRow]:
    """Copy unresolved items and record the resolved item state on the new revision."""
    carried: list[ReviewItemRow] = []
    resolved_template: ReviewItemRow | None = None
    for item in parent_items:
        if item.issue_key == issue_key:
            resolved_template = item
            continue
        carried.append(item)
    if resolved_template is None:
        raise ValueError(f"review item {issue_key} not found on parent revision")
    carried.append(
        ReviewItemRow(
            issue_key=resolved_template.issue_key,
            object_id=resolved_template.object_id,
            relationship_id=resolved_template.relationship_id,
            issue_type=resolved_template.issue_type,
            severity=resolved_template.severity,
            crop_uri=resolved_template.crop_uri,
            proposed_options=resolved_template.proposed_options,
            state=new_state,
        )
    )
    return carried


def reopen_affected_items(
    items: list[ReviewItemRow],
    *,
    affected_object_ids: set[str],
    except_issue_key: str | None = None,
) -> list[ReviewItemRow]:
    """Reopen unresolved items on objects touched by a correction."""
    if not affected_object_ids:
        return items
    reopened: list[ReviewItemRow] = []
    for item in items:
        if item.issue_key == except_issue_key:
            reopened.append(item)
            continue
        if (
            item.object_id is not None
            and item.object_id in affected_object_ids
            and item.state in ("open", "acknowledged_unknown")
        ):
            reopened.append(
                ReviewItemRow(
                    issue_key=item.issue_key,
                    object_id=item.object_id,
                    relationship_id=item.relationship_id,
                    issue_type=item.issue_type,
                    severity=item.severity,
                    crop_uri=item.crop_uri,
                    proposed_options=item.proposed_options,
                    state="open",
                )
            )
        else:
            reopened.append(item)
    return reopened
