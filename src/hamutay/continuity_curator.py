"""Continuity curator adapters for taste_open sessions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from hamutay.taste_open import ExchangeResult, TasteBackend


_CURATOR_SYSTEM_PROMPT = """\
You are a continuity curator for a Hamut'ay taste_open session.

Your job is to produce a compact continuity artifact for the next cycle. You
are not the session's identity object author, and you must not write new state
for the main instance. Preserve what is useful for continuity, distinguish
supported facts from uncertainty, and explicitly mark invalidated assumptions.

Return a structured object. Put the compact carry-forward text in `summary`.
The required `response` field should repeat that compact summary; it is an
internal curator artifact, not a user-facing chat response.
"""

_CLAIM_TABLE_CURATOR_SYSTEM_PROMPT = """\
You are a continuity curator for a Hamut'ay taste_open session.

Your job is to produce bounded evidence-status claim rows for the next cycle.
You are not the session's identity object author, and you must not write new
state for the main instance.

Return a structured object with a `claims` array. Each claim row must include:
- claim: concise text, no invented details;
- status: one of supported, invalidated, uncertain, open;
- source_cycle: the cycle number that supports the row when available;
- support: concise source/evidence text.

Do not produce narrative continuity prose as the primary artifact. The harness
will render your accepted rows deterministically for the next cycle.
"""

_ALLOWED_CLAIM_STATUSES = {
    "supported",
    "invalidated",
    "uncertain",
    "open",
}

_CLAIM_STATUS_PRIORITY = {
    "invalidated": 0,
    "supported": 1,
    "uncertain": 2,
    "open": 3,
}

_GUARDRAIL_HARD_CONSTRAINTS = [
    (
        "hard_constraint_no_local_document_storage",
        "blocked:local_document_storage",
        ("local", "document", "stor"),
    ),
    (
        "hard_constraint_west_shelter_replaces_east_clinic",
        "site_replaced:east_clinic->west_shelter",
        ("east clinic", "west shelter"),
    ),
    (
        "hard_constraint_no_social_security_numbers",
        "constraint:no_ssn",
        ("social security",),
    ),
    (
        "hard_constraint_budget_18000",
        "constraint:budget<=18000",
        ("budget", "18"),
    ),
]


def _jsonable(value):
    return json.loads(json.dumps(value, default=str))


def _truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars < 1:
        raise ValueError("max_summary_chars must be positive")
    if len(text) <= max_chars:
        return text, False
    marker = "\n[truncated]"
    if max_chars <= len(marker):
        return text[:max_chars], True
    return text[: max_chars - len(marker)].rstrip() + marker, True


def _clean_cell(value, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _coerce_source_cycle(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _normalize_claim_rows(
    raw_rows,
    *,
    max_claims: int,
    max_claim_chars: int,
    max_support_chars: int,
) -> tuple[list[dict], list[dict]]:
    accepted: list[dict] = []
    rejected: list[dict] = []
    if not isinstance(raw_rows, list):
        return accepted, [{"reason": "claims_not_list", "value_type": type(raw_rows).__name__}]

    for index, row in enumerate(raw_rows):
        if len(accepted) >= max_claims:
            rejected.append({"index": index, "reason": "row_cap_exceeded"})
            continue
        if not isinstance(row, dict):
            rejected.append({"index": index, "reason": "row_not_object"})
            continue
        claim = _clean_cell(row.get("claim"), max_claim_chars)
        support = _clean_cell(row.get("support"), max_support_chars)
        status = str(row.get("status") or "").strip().lower().replace(" ", "_")
        if status not in _ALLOWED_CLAIM_STATUSES:
            rejected.append({
                "index": index,
                "reason": "invalid_status",
                "status": row.get("status"),
            })
            continue
        if not claim:
            rejected.append({"index": index, "reason": "empty_claim"})
            continue
        accepted.append(
            {
                "claim": claim,
                "status": status,
                "source_cycle": _coerce_source_cycle(row.get("source_cycle")),
                "support": support,
            }
        )
    return accepted, rejected


def _claim_rows_from_response(raw: dict) -> tuple[object, dict | None]:
    response = raw.get("response")
    if isinstance(response, dict) and "claims" in response:
        rows = response.get("claims")
        count = len(rows) if isinstance(rows, list) else 0
        return rows, {
            "source": "response_object_claims",
            "recovered_claim_rows": count,
        }
    if isinstance(response, str):
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            return None, None
        if isinstance(parsed, dict) and "claims" in parsed:
            rows = parsed.get("claims")
            count = len(rows) if isinstance(rows, list) else 0
            return rows, {
                "source": "response_stringified_json_claims",
                "recovered_claim_rows": count,
            }
    return None, None


def _render_claim_table(rows: list[dict], max_chars: int) -> tuple[str, bool]:
    if not rows:
        return "(no valid curator claim rows)", False
    lines = [
        "Continuity claim table. Bounded curator artifact; verify against prompt facts.",
    ]
    for row in rows:
        cycle = row.get("source_cycle")
        cycle_text = f"c{cycle}" if cycle is not None else "c?"
        support = row.get("support") or "support not specified"
        lines.append(
            f"- [{row['status']} {cycle_text}] {row['claim']} | support: {support}"
        )
    return _truncate_text("\n".join(lines), max_chars)


def _claim_signature(row: dict) -> tuple[str, str]:
    return (
        str(row.get("status") or "").lower(),
        " ".join(str(row.get("claim") or "").lower().split()),
    )


def _select_delta_rows(
    rows: list[dict],
    prior_claim_rows: list[dict],
    max_rows: int,
) -> tuple[list[dict], list[dict]]:
    prior_signatures = {_claim_signature(row) for row in prior_claim_rows}
    selected: list[dict] = []
    omitted: list[dict] = []

    def add(row: dict, reason: str) -> None:
        item = {**row, "render_reason": reason}
        if len(selected) < max_rows:
            selected.append(item)
        else:
            omitted.append({**item, "omit_reason": "delta_row_cap_exceeded"})

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            _CLAIM_STATUS_PRIORITY.get(str(row.get("status")), 99),
            -(row.get("source_cycle") or 0),
            str(row.get("claim") or ""),
        ),
    )
    for row in sorted_rows:
        if (
            _claim_signature(row) not in prior_signatures
            and str(row.get("status")) in {"invalidated", "supported"}
        ):
            add(row, "new_or_changed")
    for row in sorted_rows:
        if str(row.get("status")) in {"invalidated", "supported"}:
            sig = _claim_signature(row)
            if any(_claim_signature(selected_row) == sig for selected_row in selected):
                continue
            reason = "stable_invalidated" if row.get("status") == "invalidated" else "stable_supported"
            add(row, reason)
    for row in sorted_rows:
        if _claim_signature(row) not in prior_signatures:
            sig = _claim_signature(row)
            if any(_claim_signature(selected_row) == sig for selected_row in selected):
                continue
            add(row, "new_or_changed")

    selected_sigs = {_claim_signature(row) for row in selected}
    for row in rows:
        if _claim_signature(row) not in selected_sigs:
            omitted.append({**row, "omit_reason": "not_selected"})
    return selected, omitted


def _guardrail_reason(row: dict) -> str | None:
    text = " ".join(
        [
            str(row.get("claim") or ""),
            str(row.get("support") or ""),
        ]
    ).lower()
    for reason, _token, needles in _GUARDRAIL_HARD_CONSTRAINTS:
        if all(needle in text for needle in needles):
            return reason
    return None


def _guardrail_token(row: dict) -> str | None:
    text = " ".join(
        [
            str(row.get("claim") or ""),
            str(row.get("support") or ""),
        ]
    ).lower()
    for _reason, token, needles in _GUARDRAIL_HARD_CONSTRAINTS:
        if all(needle in text for needle in needles):
            return token
    return None


def _select_guardrail_delta_rows(
    rows: list[dict],
    prior_claim_rows: list[dict],
    max_rows: int,
    stable_invalidated_cap: int,
) -> tuple[list[dict], list[dict]]:
    prior_signatures = {_claim_signature(row) for row in prior_claim_rows}
    selected: list[dict] = []
    omitted: list[dict] = []
    selected_sigs: set[tuple[str, str]] = set()

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            _CLAIM_STATUS_PRIORITY.get(str(row.get("status")), 99),
            -(row.get("source_cycle") or 0),
            str(row.get("claim") or ""),
        ),
    )

    def add(row: dict, reason: str) -> bool:
        sig = _claim_signature(row)
        if sig in selected_sigs:
            return False
        item = {**row, "render_reason": reason}
        if len(selected) < max_rows:
            selected.append(item)
            selected_sigs.add(sig)
            return True
        omitted.append({**item, "omit_reason": "delta_row_cap_exceeded"})
        return False

    for row in sorted_rows:
        if (
            row.get("status") == "invalidated"
            and _claim_signature(row) not in prior_signatures
        ):
            add(row, "new_or_changed_invalidated_guardrail")

    for row in sorted_rows:
        reason = _guardrail_reason(row)
        if reason is not None:
            add(row, reason)

    stable_invalidated = 0
    for row in sorted_rows:
        if row.get("status") != "invalidated":
            continue
        if _claim_signature(row) not in prior_signatures:
            continue
        if stable_invalidated >= stable_invalidated_cap:
            continue
        if add(row, "stable_invalidated_guardrail"):
            stable_invalidated += 1

    for row in sorted_rows:
        if (
            row.get("status") == "supported"
            and _claim_signature(row) not in prior_signatures
        ):
            add(row, "new_or_changed_supported")

    for status in ("uncertain", "open"):
        for row in sorted_rows:
            if (
                row.get("status") == status
                and _claim_signature(row) not in prior_signatures
            ):
                if add(row, f"new_or_changed_{status}"):
                    break
        else:
            continue
        break

    for row in rows:
        if _claim_signature(row) not in selected_sigs:
            omitted.append({**row, "omit_reason": "not_selected"})
    return selected, omitted


def _render_delta_claim_table(
    rows: list[dict],
    prior_claim_rows: list[dict],
    *,
    max_chars: int,
    max_rows: int,
) -> tuple[str, bool, list[dict], list[dict]]:
    selected, omitted = _select_delta_rows(rows, prior_claim_rows, max_rows)
    if not selected:
        return "(no new or prioritized curator claim rows)", False, selected, omitted
    lines = [
        "Continuity claim delta. Bounded curator artifact; verify against prompt facts.",
    ]
    for row in selected:
        cycle = row.get("source_cycle")
        cycle_text = f"c{cycle}" if cycle is not None else "c?"
        lines.append(
            f"- [{row['status']} {cycle_text} {row['render_reason']}] "
            f"{row['claim']}"
        )
    summary, truncated = _truncate_text("\n".join(lines), max_chars)
    return summary, truncated, selected, omitted


def _render_guardrail_delta_claim_table(
    rows: list[dict],
    prior_claim_rows: list[dict],
    *,
    max_chars: int,
    max_rows: int,
    stable_invalidated_cap: int,
) -> tuple[str, bool, list[dict], list[dict]]:
    selected, omitted = _select_guardrail_delta_rows(
        rows,
        prior_claim_rows,
        max_rows,
        stable_invalidated_cap,
    )
    if not selected:
        return "(no guardrail-prioritized curator claim rows)", False, selected, omitted
    lines = [
        "Continuity guardrail delta. Bounded curator artifact; verify against prompt facts.",
    ]
    for row in selected:
        cycle = row.get("source_cycle")
        cycle_text = f"c{cycle}" if cycle is not None else "c?"
        lines.append(
            f"- [{row['status']} {cycle_text} {row['render_reason']}] "
            f"{row['claim']}"
        )
    summary, truncated = _truncate_text("\n".join(lines), max_chars)
    return summary, truncated, selected, omitted


def _with_typed_tokens(rows: list[dict]) -> list[dict]:
    typed_rows = []
    for row in rows:
        token = _guardrail_token(row)
        if token is None:
            typed_rows.append(row)
        else:
            typed_rows.append({**row, "typed_token": token})
    return typed_rows


def _render_typed_guardrail_delta_claim_table(
    rows: list[dict],
    prior_claim_rows: list[dict],
    *,
    max_chars: int,
    max_rows: int,
    stable_invalidated_cap: int,
) -> tuple[str, bool, list[dict], list[dict]]:
    selected, omitted = _select_guardrail_delta_rows(
        rows,
        prior_claim_rows,
        max_rows,
        stable_invalidated_cap,
    )
    selected = _with_typed_tokens(selected)
    omitted = _with_typed_tokens(omitted)
    if not selected:
        return "(no typed guardrail-prioritized curator claim rows)", False, selected, omitted
    lines = [
        "Continuity typed guardrail delta. Verify against prompt facts.",
    ]
    for row in selected:
        cycle = row.get("source_cycle")
        cycle_text = f"c{cycle}" if cycle is not None else "c?"
        prefix = f"[{row['status']} {cycle_text} {row['render_reason']}]"
        token = row.get("typed_token")
        if token:
            lines.append(f"- {token} {prefix}")
        else:
            lines.append(f"- {prefix} {row['claim']}")
    summary, truncated = _truncate_text("\n".join(lines), max_chars)
    return summary, truncated, selected, omitted


@dataclass
class ModelContinuityCurator:
    """Model-backed continuity curator for the first-class scaffold hook."""

    backend: TasteBackend
    model: str
    experiment_label: str = "taste_open_continuity_curator"
    max_summary_chars: int = 2400

    def curate(
        self,
        *,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
        prior_state: dict | None,
        raw_output: dict,
        response_text: str,
        state: dict,
    ) -> dict:
        payload = {
            "source_cycle": cycle,
            "source_record_id": str(record_id),
            "source_timestamp": timestamp.isoformat(),
            "prior_state": prior_state,
            "main_raw_output": raw_output,
            "main_visible_response": response_text,
            "merged_state": state,
        }
        messages = [
            {
                "role": "user",
                "content": (
                    "Curate the following completed cycle for continuity. "
                    "Do not add unsupported facts. Return `summary`, "
                    "`supported_facts`, `uncertain_claims`, "
                    "`invalidated_assumptions`, and any brief "
                    "`curator_notes` that matter.\n\n"
                    + json.dumps(payload, indent=2, default=str)
                ),
            }
        ]

        result = self.backend.call(
            model=self.model,
            system=_CURATOR_SYSTEM_PROMPT,
            messages=messages,
            experiment_label=self.experiment_label,
        )
        raw = _jsonable(result.raw_output)
        summary_source = "summary"
        summary = str(raw.get("summary") or "").strip()
        if not summary:
            summary_source = "carry_forward_summary"
            summary = str(raw.get("carry_forward_summary") or "").strip()
        if not summary:
            summary_source = "response"
            summary = str(raw.get("response") or "").strip()
        summary, summary_truncated = _truncate_text(
            summary,
            self.max_summary_chars,
        )

        return {
            "curator_type": "model",
            "model": self.model,
            "summary": summary,
            "summary_source": summary_source,
            "summary_chars": len(summary),
            "summary_truncated": summary_truncated,
            "supported_facts": raw.get("supported_facts", []),
            "uncertain_claims": raw.get("uncertain_claims", []),
            "invalidated_assumptions": raw.get("invalidated_assumptions", []),
            "curator_notes": raw.get("curator_notes", []),
            "usage": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_read_input_tokens": result.cache_read_tokens,
                "cache_creation_input_tokens": result.cache_creation_tokens,
                "stop_reason": result.stop_reason,
            },
            "raw_output": raw,
        }


@dataclass
class ClaimTableContinuityCurator:
    """Model-backed curator that injects deterministic claim-table rendering."""

    backend: TasteBackend
    model: str
    experiment_label: str = "taste_open_claim_table_curator"
    max_summary_chars: int = 1200
    max_claims: int = 8
    max_claim_chars: int = 180
    max_support_chars: int = 120
    recover_response_claims: bool = False
    renderer: str = "full"
    delta_max_rows: int = 5
    guardrail_stable_invalidated_cap: int = 2
    _prior_claim_rows: list[dict] | None = None

    def curate(
        self,
        *,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
        prior_state: dict | None,
        raw_output: dict,
        response_text: str,
        state: dict,
    ) -> dict:
        payload = {
            "source_cycle": cycle,
            "source_record_id": str(record_id),
            "source_timestamp": timestamp.isoformat(),
            "prior_state": prior_state,
            "main_raw_output": raw_output,
            "main_visible_response": response_text,
            "merged_state": state,
        }
        messages = [
            {
                "role": "user",
                "content": (
                    "Curate the following completed cycle as bounded claim "
                    "rows. Preserve only continuity-critical facts, invalidated "
                    "assumptions, uncertainties, and open questions. Do not "
                    "invent dates, policies, vendors, budgets, hardware, or "
                    "implementation details not present in the payload.\n\n"
                    + json.dumps(payload, indent=2, default=str)
                ),
            }
        ]

        result = self.backend.call(
            model=self.model,
            system=_CLAIM_TABLE_CURATOR_SYSTEM_PROMPT,
            messages=messages,
            experiment_label=self.experiment_label,
        )
        raw = _jsonable(result.raw_output)
        raw_rows = raw.get("claims")
        protocol_recovery = None
        if not isinstance(raw_rows, list) and self.recover_response_claims:
            recovered_rows, protocol_recovery = _claim_rows_from_response(raw)
            if protocol_recovery is not None:
                raw_rows = recovered_rows
        rows, rejected = _normalize_claim_rows(
            raw_rows,
            max_claims=self.max_claims,
            max_claim_chars=self.max_claim_chars,
            max_support_chars=self.max_support_chars,
        )
        selected_delta_rows: list[dict] = []
        omitted_delta_rows: list[dict] = []
        if self.renderer == "full":
            summary, summary_truncated = _render_claim_table(
                rows,
                self.max_summary_chars,
            )
            rendered_rows = rows
        elif self.renderer == "delta":
            summary, summary_truncated, selected_delta_rows, omitted_delta_rows = (
                _render_delta_claim_table(
                    rows,
                    self._prior_claim_rows or [],
                    max_chars=self.max_summary_chars,
                    max_rows=self.delta_max_rows,
                )
            )
            rendered_rows = selected_delta_rows
        elif self.renderer == "guardrail_delta":
            summary, summary_truncated, selected_delta_rows, omitted_delta_rows = (
                _render_guardrail_delta_claim_table(
                    rows,
                    self._prior_claim_rows or [],
                    max_chars=self.max_summary_chars,
                    max_rows=self.delta_max_rows,
                    stable_invalidated_cap=self.guardrail_stable_invalidated_cap,
                )
            )
            rendered_rows = selected_delta_rows
        elif self.renderer == "typed_guardrail_delta":
            summary, summary_truncated, selected_delta_rows, omitted_delta_rows = (
                _render_typed_guardrail_delta_claim_table(
                    rows,
                    self._prior_claim_rows or [],
                    max_chars=self.max_summary_chars,
                    max_rows=self.delta_max_rows,
                    stable_invalidated_cap=self.guardrail_stable_invalidated_cap,
                )
            )
            rendered_rows = selected_delta_rows
        else:
            raise ValueError(f"unknown claim-table renderer: {self.renderer}")
        self._prior_claim_rows = list(rows)

        return {
            "curator_type": "claim_table_model",
            "model": self.model,
            "summary": summary,
            "summary_source": f"deterministic_claim_table_{self.renderer}",
            "summary_chars": len(summary),
            "summary_truncated": summary_truncated,
            "renderer": self.renderer,
            "claim_rows": rows,
            "rendered_claim_rows": rendered_rows,
            "selected_delta_rows": selected_delta_rows,
            "omitted_delta_rows": omitted_delta_rows,
            "selected_delta_row_count": len(selected_delta_rows),
            "omitted_delta_row_count": len(omitted_delta_rows),
            "accepted_claim_rows": len(rows),
            "rejected_claim_rows": len(rejected),
            "rejected_claim_row_examples": rejected[:8],
            "protocol_recovery": protocol_recovery,
            "protocol_recovery_used": protocol_recovery is not None,
            "protocol_recovery_source": (
                protocol_recovery.get("source") if protocol_recovery else None
            ),
            "recovered_claim_rows": (
                int(protocol_recovery.get("recovered_claim_rows") or 0)
                if protocol_recovery
                else 0
            ),
            "usage": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_read_input_tokens": result.cache_read_tokens,
                "cache_creation_input_tokens": result.cache_creation_tokens,
                "stop_reason": result.stop_reason,
            },
            "raw_output": raw,
        }


__all__ = ["ClaimTableContinuityCurator", "ModelContinuityCurator"]
