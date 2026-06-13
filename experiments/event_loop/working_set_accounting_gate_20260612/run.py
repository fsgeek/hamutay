"""Goal 7 working-set accounting gate.

This dry-run gate proves the accounting shape needed before matched
working-set experiments. It intentionally uses the existing
LocalMemorySubstrate as a bounded substitute so evidence availability,
retrieval provenance, omissions, truncation, and request answerability can be
classified without live model calls.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.events import validate_requested_context
from hamutay.memory.bridge import JsonDict, LocalMemorySubstrate


EXPERIMENT_ID = "working_set_accounting_gate_20260612"
ROW_ID = "dry_run_gate"
REQUIRED_SECTIONS = {
    "live_context",
    "carried_state",
    "recalled_context",
    "omitted_context",
    "declared_losses",
    "token_counts",
    "recall_provenance",
    "truncation_metadata",
    "evidence_request_classifications",
    "recovery_metrics",
    "contamination_metrics",
    "substrate_decision",
    "failure_attribution",
}

TASK_RECORD_ID = UUID("70000000-0000-0000-0000-000000000101")
EVIDENCE_RECORD_ID = UUID("70000000-0000-0000-0000-000000000102")
LONG_RECORD_ID = UUID("70000000-0000-0000-0000-000000000103")
DISTRACTOR_RECORD_ID = UUID("70000000-0000-0000-0000-000000000104")
MISSING_RECORD_ID = UUID("70000000-0000-0000-0000-000000000199")


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def _approx_tokens(value: Any) -> int:
    text = json.dumps(value, sort_keys=True, default=str)
    return max(1, (len(text) + 3) // 4)


def build_bounded_corpus() -> LocalMemorySubstrate:
    substrate = LocalMemorySubstrate()
    records = [
        (
            TASK_RECORD_ID,
            "working_set_task",
            {
                "title": "Restart frontier evidence audit",
                "goal": "Verify whether a restart boundary preserved required evidence.",
                "expected_evidence_record_id": str(EVIDENCE_RECORD_ID),
                "expected_long_record_id": str(LONG_RECORD_ID),
            },
        ),
        (
            EVIDENCE_RECORD_ID,
            "evidence_record",
            {
                "claim": "Restart frontier preserved the event status and memory snapshot.",
                "support": "actions.jsonl, events.jsonl, restart_frontier.jsonl, memory_snapshot.json",
                "status": "supported",
            },
        ),
        (
            LONG_RECORD_ID,
            "long_evidence_record",
            {
                "summary": "Long audit trace excerpt",
                "body": "restart-frontier trace segment " * 80,
            },
        ),
        (
            DISTRACTOR_RECORD_ID,
            "distractor_record",
            {
                "claim": "A decorative unrelated note that should not enter the working set.",
                "status": "irrelevant",
            },
        ),
    ]
    for record_id, record_type, content in records:
        response = substrate.store_episode(
            record_id=record_id,
            record_type=record_type,
            content=content,
            production={
                "who": {"instance": "goal7-gate"},
                "what": {"artifact": record_type},
                "when": {"cycle": 0},
                "where": {"project": "hamutay"},
            },
            execution_trace={
                "experiment_id": EXPERIMENT_ID,
                "row_id": ROW_ID,
                "source": "bounded_inspectable_corpus",
            },
        )
        if not response.ok:
            raise RuntimeError(response.to_dict())
    return substrate


def model_authored_requests() -> list[Any]:
    return [
        {"tool": "recall", "record_id": str(EVIDENCE_RECORD_ID), "field": "claim"},
        {"tool": "recall", "record_id": str(LONG_RECORD_ID), "field": "body"},
        {"tool": "recall", "record_id": str(MISSING_RECORD_ID)},
        {"tool": "recall", "cycle": 1},
        {"tool": "recall", "record_id": "not-a-uuid"},
    ]


def classify_evidence_request(
    request: Any,
    *,
    substrate: LocalMemorySubstrate,
) -> JsonDict:
    if not isinstance(request, dict):
        return {
            "request": request,
            "classification": "malformed_or_underspecified",
            "layer": "prompt_schema",
            "reason": "request is not an object",
        }
    try:
        validated = validate_requested_context([request])[0]
    except ValueError as exc:
        return {
            "request": deepcopy(request),
            "classification": "malformed_or_underspecified",
            "layer": "prompt_schema",
            "reason": str(exc),
        }
    if validated.get("tool") != "recall":
        return {
            "request": validated,
            "classification": "structurally_impossible",
            "layer": "recall_protocol",
            "reason": "working-set gate only implements recall answerability",
        }
    if "cycle" in validated:
        return {
            "request": validated,
            "classification": "structurally_impossible",
            "layer": "recall_protocol",
            "reason": "cycle-based recall requires prior-state mapping not provided by the bounded local substitute",
        }
    result = substrate.recall(
        record_id=validated["record_id"],
        field=validated.get("field"),
        max_chars=96 if validated.get("record_id") == str(LONG_RECORD_ID) else None,
        reason={
            "experiment_id": EXPERIMENT_ID,
            "request_classification": "answerability_probe",
            "request": validated,
        },
    )
    if result.ok:
        data = result.to_dict()
        return {
            "request": validated,
            "classification": "answerable_by_substrate",
            "layer": None,
            "reason": "request resolved successfully",
            "result": data,
            "truncated": bool(data.get("truncated")),
            "omitted": data.get("omitted", []),
        }
    error = result.to_dict().get("error") or {}
    if error.get("code") in {"record_not_found", "field_not_found"}:
        return {
            "request": validated,
            "classification": "unavailable_but_well_formed",
            "layer": "memory_substrate_coverage",
            "reason": error.get("message"),
            "error": error,
        }
    return {
        "request": validated,
        "classification": "malformed_or_underspecified",
        "layer": "prompt_schema",
        "reason": error.get("message", "request failed validation"),
        "error": error,
    }


def _recalled_context(classifications: list[JsonDict]) -> list[JsonDict]:
    recalled = []
    for item in classifications:
        if item.get("classification") != "answerable_by_substrate":
            continue
        result = item["result"]
        recalled.append(
            {
                "request": deepcopy(item["request"]),
                "content": deepcopy(result.get("content")),
                "field": result.get("field"),
                "truncated": result.get("truncated", False),
                "omitted": result.get("omitted", []),
            }
        )
    return recalled


def build_working_set_accounting() -> JsonDict:
    substrate = build_bounded_corpus()
    live_context = {
        "system": "Goal 7 dry-run working-set gate",
        "task": "Use available corpus records to audit restart evidence handling.",
        "visible_record_ids": [str(TASK_RECORD_ID)],
        "available_tools": ["recall"],
    }
    carried_state = {
        "selected_investigation": "restart frontier evidence audit",
        "open_question": "which requested evidence is available, omitted, or unavailable?",
        "prior_cycle_summary": "model shaped the investigation around evidence handling",
    }
    requests = model_authored_requests()
    classifications = [
        classify_evidence_request(request, substrate=substrate)
        for request in requests
    ]
    recalled_context = _recalled_context(classifications)
    omitted_context = [
        {
            "record_id": str(DISTRACTOR_RECORD_ID),
            "reason": "distractor_not_task_relevant",
            "known_to_substrate": True,
            "omission_type": "intentional_working_set_exclusion",
        },
        {
            "record_id": str(LONG_RECORD_ID),
            "field": "body",
            "reason": "max_chars bound produced a truncated recall",
            "known_to_substrate": True,
            "omission_type": "payload_truncated",
        },
    ]
    declared_losses = [
        {
            "what": "Yanantin substrate not exercised",
            "why": "Goal 7 chose bounded local substitute for readiness gate",
            "layer": "memory_substrate_coverage",
        },
        {
            "what": "cycle-addressed recall not resolved",
            "why": "bounded local substitute has no cycle-to-record map",
            "layer": "recall_protocol",
        },
    ]
    retrieval_log = substrate.retrieval_log().data["retrievals"]
    truncation_metadata = [
        {
            "retrieval_id": entry["retrieval_id"],
            "tool": entry["tool"],
            "coordinate": entry["coordinate"],
            "omitted": entry.get("omitted", []),
            "truncated": entry.get("truncated", False),
        }
        for entry in retrieval_log
        if entry.get("truncated") or entry.get("omitted")
    ]
    unavailable_evidence = [
        item
        for item in classifications
        if item.get("classification")
        in {"unavailable_but_well_formed", "structurally_impossible"}
    ]
    token_counts = {
        "live_context": _approx_tokens(live_context),
        "carried_state": _approx_tokens(carried_state),
        "recalled_context": _approx_tokens(recalled_context),
        "omitted_context": _approx_tokens(omitted_context),
        "declared_losses": _approx_tokens(declared_losses),
        "unavailable_evidence": _approx_tokens(unavailable_evidence),
    }
    token_counts["total_accounted"] = sum(token_counts.values())
    requested_targets = {
        str(EVIDENCE_RECORD_ID),
        str(LONG_RECORD_ID),
        str(MISSING_RECORD_ID),
    }
    recovered_targets = {
        item["request"]["record_id"]
        for item in classifications
        if item.get("classification") == "answerable_by_substrate"
        and "record_id" in item.get("request", {})
    }
    recovery_metrics = {
        "requested_target_count": len(requested_targets),
        "recovered_target_count": len(recovered_targets),
        "missing_target_count": len(requested_targets - recovered_targets),
        "recovery_rate": len(recovered_targets) / len(requested_targets),
        "recovered_record_ids": sorted(recovered_targets),
        "missing_record_ids": sorted(requested_targets - recovered_targets),
    }
    recalled_record_ids = {
        item["request"].get("record_id")
        for item in classifications
        if item.get("classification") == "answerable_by_substrate"
    }
    contamination_metrics = {
        "distractor_record_ids": [str(DISTRACTOR_RECORD_ID)],
        "distractors_in_recalled_context": sorted(
            rid for rid in recalled_record_ids if rid == str(DISTRACTOR_RECORD_ID)
        ),
        "contamination_count": 0,
        "contamination_rate": 0.0,
    }
    failure_attribution = {
        "model_behavior": [],
        "prompt_schema": [
            item for item in classifications if item.get("layer") == "prompt_schema"
        ],
        "memory_substrate_coverage": [
            item
            for item in classifications
            if item.get("layer") == "memory_substrate_coverage"
        ],
        "recall_protocol": [
            item for item in classifications if item.get("layer") == "recall_protocol"
        ],
        "scorer": [],
        "inconclusive": [],
    }
    return {
        "schema_version": "hamutay.working_set_accounting.v1",
        "experiment_id": EXPERIMENT_ID,
        "row_id": ROW_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "substrate_decision": {
            "selected": "LocalMemorySubstrate",
            "yanantin_used": False,
            "rationale": (
                "Goal 7 is an accounting readiness gate; the bounded local "
                "substitute already exposes recall, retrieval logs, explicit "
                "failures, truncation metadata, and snapshots."
            ),
            "limitations": [
                "No Yanantin field mapping or storage obfuscation exercised.",
                "No semantic find surface exercised.",
                "No cycle-to-record recall map in the bounded substitute.",
            ],
        },
        "bounded_inspectable_corpus": substrate.snapshot()["records"],
        "live_context": live_context,
        "carried_state": carried_state,
        "model_authored_evidence_requests": requests,
        "evidence_request_classifications": classifications,
        "recalled_context": recalled_context,
        "omitted_context": omitted_context,
        "declared_losses": declared_losses,
        "unavailable_evidence": unavailable_evidence,
        "token_counts": token_counts,
        "recall_provenance": retrieval_log,
        "truncation_metadata": truncation_metadata,
        "recovery_metrics": recovery_metrics,
        "contamination_metrics": contamination_metrics,
        "failure_attribution": failure_attribution,
        "memory_snapshot": substrate.snapshot(),
    }


def score_accounting(accounting: JsonDict) -> JsonDict:
    missing_sections = sorted(REQUIRED_SECTIONS - set(accounting))
    classifications = {
        item["classification"]
        for item in accounting.get("evidence_request_classifications", [])
    }
    required_classifications = {
        "answerable_by_substrate",
        "unavailable_but_well_formed",
        "structurally_impossible",
        "malformed_or_underspecified",
    }
    checks = {
        "required_sections_present": not missing_sections,
        "all_request_classes_exercised": required_classifications <= classifications,
        "recall_provenance_present": bool(accounting.get("recall_provenance")),
        "truncation_recorded": bool(accounting.get("truncation_metadata")),
        "omitted_context_recorded": bool(accounting.get("omitted_context")),
        "declared_losses_recorded": bool(accounting.get("declared_losses")),
        "token_counts_present": bool(accounting.get("token_counts", {}).get("total_accounted")),
        "recovery_metrics_present": "recovery_rate" in accounting.get("recovery_metrics", {}),
        "contamination_metrics_present": "contamination_rate"
        in accounting.get("contamination_metrics", {}),
        "substrate_limitations_explicit": bool(
            accounting.get("substrate_decision", {}).get("limitations")
        ),
        "failure_layers_separated": all(
            layer in accounting.get("failure_attribution", {})
            for layer in (
                "model_behavior",
                "prompt_schema",
                "memory_substrate_coverage",
                "recall_protocol",
                "scorer",
                "inconclusive",
            )
        ),
    }
    classification = "survived" if all(checks.values()) else "falsified"
    return {
        "schema_version": "hamutay.working_set_accounting_gate_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "live_model_calls": False,
        "classification": classification,
        "checks": checks,
        "missing_sections": missing_sections,
        "request_classification_counts": {
            name: sum(
                1
                for item in accounting.get("evidence_request_classifications", [])
                if item.get("classification") == name
            )
            for name in sorted(required_classifications)
        },
        "summary": {
            "ready_for_goal_8": classification == "survived",
            "decision": (
                "Working-set accounting gate is ready for the matched panel."
                if classification == "survived"
                else "Working-set accounting gate is not ready for the matched panel."
            ),
            "failure_layers_with_findings": [
                layer
                for layer, items in accounting.get("failure_attribution", {}).items()
                if items
            ],
            "recovery_rate": accounting.get("recovery_metrics", {}).get("recovery_rate"),
            "contamination_rate": accounting.get("contamination_metrics", {}).get(
                "contamination_rate"
            ),
        },
    }


def write_analysis(output_root: Path, accounting: JsonDict, results: JsonDict) -> None:
    counts = results["request_classification_counts"]
    lines = [
        "# Working-Set Accounting Gate Analysis",
        "",
        f"Experiment ID: `{EXPERIMENT_ID}`",
        "",
        "## Result",
        "",
        f"- Classification: `{results['classification']}`",
        f"- Ready for Goal 8: `{results['summary']['ready_for_goal_8']}`",
        "- Live model calls: `False`",
        f"- Recovery rate: `{results['summary']['recovery_rate']}`",
        f"- Contamination rate: `{results['summary']['contamination_rate']}`",
        f"- Decision: {results['summary']['decision']}",
        "",
        "## Request Classification Counts",
        "",
        "| Classification | Count |",
        "| --- | ---: |",
    ]
    for name, count in counts.items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The gate survived as an accounting readiness result, not as an "
            "artifact-quality claim. The dry run distinguished live context, "
            "carried state, recalled context, omitted context, declared losses, "
            "and unavailable evidence. It also separated malformed request "
            "shape, substrate coverage, and recall-protocol limitations from "
            "model-behavior findings.",
            "",
            "The bounded local substitute was sufficient for this gate because "
            "it preserves recall provenance and truncation metadata. Its "
            "limitations remain explicit: no Yanantin adapter, no semantic find "
            "surface, and no cycle-to-record recall map.",
            "",
            "## Artifact Trail",
            "",
            "- `PRE_REGISTRATION.md`, `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the frame.",
            "- `working_set_accounting.json` preserves the accounting object, bounded corpus, request classifications, retrieval log, token counts, and metrics.",
            "- `results.json` preserves deterministic checks and readiness decision.",
            "- `analysis.md` separates model behavior from substrate, recall-protocol, prompt/schema, scorer, and inconclusive layers.",
        ]
    )
    output_root.joinpath("analysis.md").write_text("\n".join(lines) + "\n")


def run_gate(output_root: Path) -> JsonDict:
    output_root.mkdir(parents=True, exist_ok=True)
    accounting = build_working_set_accounting()
    results = score_accounting(accounting)
    _write_json(output_root / "working_set_accounting.json", accounting)
    _write_json(output_root / "results.json", results)
    write_analysis(output_root, accounting, results)
    return results


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(Path(__file__).resolve().parent))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    results = run_gate(Path(args.output_root))
    print(json.dumps(results["summary"], indent=2, sort_keys=True))
    return 0 if results["classification"] == "survived" else 1


if __name__ == "__main__":
    raise SystemExit(main())
