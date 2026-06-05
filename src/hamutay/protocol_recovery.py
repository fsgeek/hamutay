"""Deterministic protocol-recovery builders for taste_open sessions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


SECTION_INVALIDATED_ASSUMPTIONS = "Invalidated Assumptions"
SECTION_NEW_CONSTRAINTS = "New Constraints"
SECTION_UPDATED_GOALS = "Updated Goals"
SECTION_NEXT_ACTIONS = "Next Actions"

_COST_WARNING_RE = re.compile(
    r"expected cost|contingency|hardware|cellular plans|\$\s?\d",
    re.I,
)


def _normalize_heading(line: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", line.lower()).strip()


def _section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    target = _normalize_heading(heading)
    start = None
    for index, line in enumerate(lines):
        if target in _normalize_heading(line):
            start = index + 1
            break
    if start is None:
        return []
    collected = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped == "---" and collected:
            break
        if stripped.startswith("###") and collected:
            break
        collected.append(line)
    return collected


def _clean_markup(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    return " ".join(text.split()).strip()


def _extract_numbered_items(lines: list[str]) -> list[dict]:
    items = []
    current: dict | None = None
    for line in lines:
        stripped = line.strip()
        match = re.match(r"^\d+\.\s+(.*)", stripped)
        if match:
            if current is not None:
                items.append(current)
            current = {"text": _clean_markup(match.group(1)), "support": ""}
            continue
        if current is None:
            continue
        evidence = re.match(r"^-\s+Evidence\s*:\s*(.*)", _clean_markup(stripped), re.I)
        if evidence:
            current["support"] = evidence.group(1).strip()
        elif stripped.startswith("-"):
            detail = _clean_markup(stripped.lstrip("- "))
            current["support"] = (
                f"{current['support']} {detail}".strip()
                if current["support"]
                else detail
            )
    if current is not None:
        items.append(current)
    return items


def _extract_bullet_items(lines: list[str]) -> list[dict]:
    items = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        text = _clean_markup(stripped.lstrip("- "))
        if text:
            items.append({"text": text, "support": ""})
    return items


@dataclass(frozen=True)
class RecoverySource:
    source_cycle: int
    source_record_id: str
    source_field: str


def _candidate_row(*, kind: str, item: dict, source: RecoverySource) -> dict:
    return {
        "row_type": kind,
        "status": "candidate",
        "text": item["text"],
        "support": item.get("support") or "",
        "source_cycle": source.source_cycle,
        "source_record_id": source.source_record_id,
        "source_field": source.source_field,
        "accepted": False,
    }


def _contamination_warnings(
    text: str,
    *,
    source_cycle: int,
    source_record_id: str,
) -> list[dict]:
    warnings = []
    for line in text.splitlines():
        stripped = _clean_markup(line.strip().lstrip("- "))
        if not stripped or not _COST_WARNING_RE.search(stripped):
            continue
        if "$18k" in stripped.lower() or "$18,000" in stripped:
            continue
        warnings.append(
            {
                "row_type": "contamination_warning",
                "status": "candidate",
                "text": stripped,
                "warning_type": "unsupported_budget_or_cost_detail",
                "source_cycle": source_cycle,
                "source_record_id": source_record_id,
                "source_field": "response_text",
                "accepted": False,
            }
        )
    return warnings


@dataclass
class DeterministicProtocolRecoveryBuilder:
    """Build candidate repair artifacts from failed merge responses.

    This builder is intentionally conservative: it never returns accepted state
    and never claims extracted rows are true. It only preserves candidates for
    later adjudication.
    """

    live_policy: str = "strict_reject"

    def recover(
        self,
        *,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
        prior_state: dict | None,
        raw_output: dict,
        response_text: str,
        failure_classification: dict,
    ) -> dict:
        del timestamp, prior_state
        source_record_id = str(record_id)
        candidate_rows: list[dict] = []
        candidate_rows.extend(
            _candidate_row(
                kind="invalidated_assumption",
                item=item,
                source=RecoverySource(
                    source_cycle=cycle,
                    source_record_id=source_record_id,
                    source_field="response_text.Invalidated Assumptions",
                ),
            )
            for item in _extract_numbered_items(
                _section_lines(response_text, SECTION_INVALIDATED_ASSUMPTIONS)
            )
        )
        candidate_rows.extend(
            _candidate_row(
                kind="constraint",
                item=item,
                source=RecoverySource(
                    source_cycle=cycle,
                    source_record_id=source_record_id,
                    source_field="response_text.New Constraints",
                ),
            )
            for item in _extract_bullet_items(
                _section_lines(response_text, SECTION_NEW_CONSTRAINTS)
            )
        )
        candidate_rows.extend(
            _candidate_row(
                kind="goal",
                item=item,
                source=RecoverySource(
                    source_cycle=cycle,
                    source_record_id=source_record_id,
                    source_field="response_text.Updated Goals",
                ),
            )
            for item in _extract_bullet_items(
                _section_lines(response_text, SECTION_UPDATED_GOALS)
            )
        )
        candidate_rows.extend(
            _candidate_row(
                kind="next_action",
                item=item,
                source=RecoverySource(
                    source_cycle=cycle,
                    source_record_id=source_record_id,
                    source_field="response_text.Next Actions",
                ),
            )
            for item in _extract_numbered_items(
                _section_lines(response_text, SECTION_NEXT_ACTIONS)
            )
        )
        overlap_keys = failure_classification.get("overlap_keys", [])
        return {
            "recovery_type": "merge_failure_candidate_extraction",
            "status": "candidate",
            "accepted_state": None,
            "live_policy": self.live_policy,
            "source_cycle": cycle,
            "source_record_id": source_record_id,
            "failure_classification": json.loads(
                json.dumps(failure_classification, default=str)
            ),
            "overlap_keys": overlap_keys,
            "candidate_rows": candidate_rows,
            "contamination_warnings": _contamination_warnings(
                response_text,
                source_cycle=cycle,
                source_record_id=source_record_id,
            ),
            "raw_update_excerpt": {
                "deleted_regions": raw_output.get("deleted_regions"),
                "overlap_values": {
                    key: raw_output.get(key)
                    for key in overlap_keys
                    if isinstance(key, str)
                },
            },
        }


__all__ = ["DeterministicProtocolRecoveryBuilder"]
