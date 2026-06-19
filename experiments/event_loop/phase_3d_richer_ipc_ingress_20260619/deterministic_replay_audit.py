"""Deterministic replay audit for Phase 3D richer IPC runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]

EXPECTED = {
    "accepted_task_message_labels": ["task-alpha", "task-beta"],
    "accepted_non_task_message_labels": [
        "cancel-beta",
        "correction-alpha",
        "evidence-alpha",
        "status-all",
    ],
    "corrected_message_labels": ["task-alpha"],
    "canceled_message_labels": ["task-beta"],
    "rejected_message_labels": ["cancel-ghost"],
    "completed_message_labels": ["task-alpha"],
    "research_status": "completed",
    "operations_status": "canceled",
    "evidence_cited_message_labels": ["correction-alpha", "task-alpha"],
}


def read_jsonl(path: Path) -> list[JsonDict]:
    records: list[JsonDict] = []
    if not path.exists():
        return records
    for line in path.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def enum_value(pending: JsonDict, field: str) -> Any:
    properties = (
        pending.get("terminal_surface", {})
        .get("input_schema", {})
        .get("properties", {})
    )
    schema = properties.get(field)
    if not isinstance(schema, dict):
        return None
    values = schema.get("enum")
    if isinstance(values, list) and len(values) == 1:
        return values[0]
    return None


def enum_values(pending: JsonDict, field: str) -> list[str]:
    properties = (
        pending.get("terminal_surface", {})
        .get("input_schema", {})
        .get("properties", {})
    )
    schema = properties.get(field)
    if not isinstance(schema, dict):
        return []
    item_schema = schema.get("items")
    if not isinstance(item_schema, dict):
        return []
    values = item_schema.get("enum")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def states_by_record_id(session_records: list[JsonDict]) -> dict[str, JsonDict]:
    states: dict[str, JsonDict] = {}
    for record in session_records:
        record_id = record.get("record_id")
        state = record.get("state")
        if record_id and isinstance(state, dict):
            states[str(record_id)] = state
    return states


def completed_events(event_records: list[JsonDict]) -> list[JsonDict]:
    return [
        record
        for record in event_records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]


def pending_by_event_id(event_records: list[JsonDict]) -> dict[str, JsonDict]:
    return {
        str(record.get("event_id")): record
        for record in event_records
        if record.get("record_type") == "event_status"
        and record.get("status") == "pending"
        and record.get("event_id")
    }


def build_substrate_ledger(event_records: list[JsonDict]) -> JsonDict:
    pending_records = pending_by_event_id(event_records)
    completed = completed_events(event_records)
    completed_event_ids = {str(record.get("event_id")) for record in completed}
    ledger: JsonDict = {
        "accepted_task_message_labels": [],
        "accepted_non_task_message_labels": [],
        "corrected_message_labels": [],
        "canceled_message_labels": [],
        "rejected_message_labels": [],
        "completed_message_labels": [],
        "workstream_by_message": {},
        "evidence_cited_message_labels": [],
        "evidence_citation_constraint_present": False,
    }
    for event_id, pending in pending_records.items():
        if event_id not in completed_event_ids:
            continue
        event_type = str(pending.get("event_type"))
        label = str(pending.get("label"))
        if label in {"category-summary", "claim-audit", "final-ipc-synthesis"}:
            continue
        workstream_id = enum_value(pending, "workstream_id")
        if workstream_id:
            ledger["workstream_by_message"][label] = workstream_id
        if event_type == "ipc_task":
            ledger["accepted_task_message_labels"].append(label)
        elif event_type == "ipc_correction":
            ledger["accepted_non_task_message_labels"].append(label)
            target = enum_value(pending, "target_message_label")
            if target:
                ledger["corrected_message_labels"].append(target)
        elif event_type == "ipc_cancellation":
            status = enum_value(pending, "cancellation_status")
            target = enum_value(pending, "target_message_label")
            if status == "accepted":
                ledger["accepted_non_task_message_labels"].append(label)
                if target:
                    ledger["canceled_message_labels"].append(target)
            elif status == "rejected":
                ledger["rejected_message_labels"].append(label)
        elif event_type == "self_scheduled_reflection":
            completed_label = enum_value(pending, "completed_message_label")
            if completed_label:
                ledger["completed_message_labels"].append(completed_label)
        elif event_type == "ipc_status_query":
            ledger["accepted_non_task_message_labels"].append(label)
            ledger["research_status"] = enum_value(pending, "research_status")
            ledger["operations_status"] = enum_value(pending, "operations_status")
        elif event_type == "ipc_external_evidence":
            ledger["accepted_non_task_message_labels"].append(label)
            citations = enum_values(pending, "cited_message_labels")
            ledger["evidence_cited_message_labels"] = sorted(citations)
            ledger["evidence_citation_constraint_present"] = bool(citations)
    for key, value in list(ledger.items()):
        if isinstance(value, list):
            ledger[key] = sorted(value)
    return ledger


def build_model_event_ledger(
    event_records: list[JsonDict],
    session_records: list[JsonDict],
) -> JsonDict:
    pending_records = pending_by_event_id(event_records)
    states = states_by_record_id(session_records)
    ledger: JsonDict = {
        "accepted_task_message_labels": [],
        "accepted_non_task_message_labels": [],
        "corrected_message_labels": [],
        "canceled_message_labels": [],
        "rejected_message_labels": [],
        "completed_message_labels": [],
        "evidence_cited_message_labels": [],
    }
    for completed in completed_events(event_records):
        pending = pending_records.get(str(completed.get("event_id")), {})
        label = str(pending.get("label"))
        event_type = str(pending.get("event_type"))
        if label in {"category-summary", "claim-audit", "final-ipc-synthesis"}:
            continue
        state = states.get(str(completed.get("result_record_id")), {})
        if event_type == "ipc_task" and state.get("message_status") == "accepted":
            ledger["accepted_task_message_labels"].append(label)
        elif event_type == "ipc_correction" and state.get("correction_status") == "applied":
            ledger["accepted_non_task_message_labels"].append(label)
            ledger["corrected_message_labels"].append(str(state.get("target_message_label")))
        elif event_type == "ipc_cancellation":
            if state.get("cancellation_status") == "accepted":
                ledger["accepted_non_task_message_labels"].append(label)
                ledger["canceled_message_labels"].append(str(state.get("target_message_label")))
            elif state.get("cancellation_status") == "rejected":
                ledger["rejected_message_labels"].append(label)
        elif event_type == "self_scheduled_reflection":
            completed_label = state.get("completed_message_label")
            if completed_label:
                ledger["completed_message_labels"].append(str(completed_label))
        elif event_type == "ipc_status_query":
            ledger["accepted_non_task_message_labels"].append(label)
            ledger["research_status"] = state.get("research_status")
            ledger["operations_status"] = state.get("operations_status")
        elif event_type == "ipc_external_evidence":
            ledger["accepted_non_task_message_labels"].append(label)
            citations = state.get("cited_message_labels") or []
            ledger["evidence_cited_message_labels"] = sorted(
                str(item) for item in citations
            )
    for key, value in list(ledger.items()):
        if isinstance(value, list):
            ledger[key] = sorted(item for item in value if item and item != "None")
    return ledger


def compare_ledger(ledger: JsonDict, *, include_evidence: bool) -> JsonDict:
    checks = {
        "accepted_task_labels": ledger.get("accepted_task_message_labels")
        == EXPECTED["accepted_task_message_labels"],
        "accepted_non_task_labels": ledger.get("accepted_non_task_message_labels")
        == EXPECTED["accepted_non_task_message_labels"],
        "corrected_labels": ledger.get("corrected_message_labels")
        == EXPECTED["corrected_message_labels"],
        "canceled_labels": ledger.get("canceled_message_labels")
        == EXPECTED["canceled_message_labels"],
        "rejected_labels": ledger.get("rejected_message_labels")
        == EXPECTED["rejected_message_labels"],
        "completed_labels": ledger.get("completed_message_labels")
        == EXPECTED["completed_message_labels"],
        "workstream_status": ledger.get("research_status") == EXPECTED["research_status"]
        and ledger.get("operations_status") == EXPECTED["operations_status"],
    }
    if include_evidence:
        checks["evidence_citations"] = ledger.get("evidence_cited_message_labels") == (
            EXPECTED["evidence_cited_message_labels"]
        )
    return {"passed": all(checks.values()), "checks": checks}


def audit_result_dir(result_dir: Path) -> JsonDict:
    event_records = read_jsonl(result_dir / "events.jsonl")
    session_records = read_jsonl(result_dir / "taste_open.jsonl")
    substrate_ledger = build_substrate_ledger(event_records)
    model_event_ledger = build_model_event_ledger(event_records, session_records)
    substrate_category_comparison = compare_ledger(
        substrate_ledger,
        include_evidence=False,
    )
    substrate_evidence_comparison = compare_ledger(
        substrate_ledger,
        include_evidence=True,
    )
    model_event_comparison = compare_ledger(
        model_event_ledger,
        include_evidence=True,
    )
    return {
        "result_dir": str(result_dir),
        "substrate_declared_ledger": substrate_ledger,
        "model_event_ledger": model_event_ledger,
        "substrate_category_comparison": substrate_category_comparison,
        "substrate_evidence_comparison": substrate_evidence_comparison,
        "model_event_comparison": model_event_comparison,
        "finding": {
            "substrate_category_truth_reconstructable": substrate_category_comparison[
                "passed"
            ],
            "substrate_evidence_truth_reconstructable": substrate_evidence_comparison[
                "passed"
            ],
            "model_event_category_truth_reconstructable": model_event_comparison[
                "passed"
            ],
            "evidence_citation_constrained_by_surface": bool(
                substrate_ledger.get("evidence_citation_constraint_present")
            ),
        },
    }


def write_markdown(output: Path, audits: list[JsonDict]) -> None:
    lines = [
        "# Phase 3D Deterministic Replay Audit",
        "",
        "Date: 2026-06-19",
        "",
        "## Question",
        "",
        "Can the Phase 3D category truth be reconstructed from recorded substrate",
        "events without asking a model to synthesize it?",
        "",
        "## Summary",
        "",
    ]
    for audit in audits:
        finding = audit["finding"]
        lines.extend(
            [
                f"- `{audit['result_dir']}`:",
                "  - substrate category truth reconstructable: "
                f"`{finding['substrate_category_truth_reconstructable']}`",
                "  - substrate evidence citation truth reconstructable: "
                f"`{finding['substrate_evidence_truth_reconstructable']}`",
                "  - model event category truth reconstructable: "
                f"`{finding['model_event_category_truth_reconstructable']}`",
                "  - evidence citation constrained by terminal surface: "
                f"`{finding['evidence_citation_constrained_by_surface']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The deterministic replay can reconstruct the IPC category ledger from",
            "scheduler-authored event surfaces and event completion records. This means",
            "the substrate did not lose the accepted/rejected/canceled/completed facts.",
            "",
            "Where model event outputs diverge, the divergence is visible as model-owned",
            "state drift rather than substrate ambiguity. The split-final run also shows",
            "that tighter evidence citation constraints can repair evidence routing, but",
            "final category synthesis still fails without an explicit durable category",
            "ledger.",
            "",
            "## Decision",
            "",
            "The failure is mitigable in architecture: maintain a substrate-owned or",
            "event-loop-owned category ledger instead of asking final synthesis to",
            "reconstruct category truth from accumulated context.",
            "",
        ]
    )
    output.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dirs", nargs="+", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args(argv)
    audits = [audit_result_dir(path) for path in args.result_dirs]
    payload = {
        "schema_version": "hamutay.phase_3d_deterministic_replay_audit.v1",
        "audits": audits,
        "overall": {
            "all_substrate_ledgers_reconstructable": all(
                audit["finding"]["substrate_category_truth_reconstructable"]
                for audit in audits
            ),
            "all_substrate_evidence_reconstructable": all(
                audit["finding"]["substrate_evidence_truth_reconstructable"]
                for audit in audits
            ),
            "all_model_event_ledgers_reconstructable": all(
                audit["finding"]["model_event_category_truth_reconstructable"]
                for audit in audits
            ),
        },
    }
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_markdown(args.output_md, audits)
    print(json.dumps(payload["overall"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
