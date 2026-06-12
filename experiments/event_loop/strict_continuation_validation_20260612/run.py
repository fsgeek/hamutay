"""Run the Goal 4 strict continuation validation probe."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.memory.actions import parse_autonomous_action


JsonDict = dict[str, Any]

EXPERIMENT_ID = "strict_continuation_validation_20260612"
ROOT_DIR = Path(__file__).resolve().parent
RID = UUID("30000000-0000-0000-0000-000000000001")
REJECTION_CODE = "continue_after_without_continuation_request"


def matrix() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": False,
        "rows": [
            {
                "row_id": "invalid_continue_no_request",
                "expected": "classified_before_acceptance",
            },
            {
                "row_id": "invalid_continue_malformed_request",
                "expected": "classified_before_acceptance",
            },
            {
                "row_id": "valid_continue_with_request",
                "expected": "accepted",
            },
            {
                "row_id": "stop_complete_no_request",
                "expected": "accepted",
            },
        ],
    }


def budget_manifest() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": False,
        "max_live_calls": 0,
        "max_estimated_cost_usd": 0.0,
        "output_cap_policy": "No provider calls are made.",
    }


def failure_taxonomy() -> JsonDict:
    return {
        "schema_version": "hamutay.strict_continuation_validation_taxonomy.v1",
        "entries": [
            {
                "layer": "validator",
                "code": REJECTION_CODE,
                "meaning": (
                    "The model chose continue_after without an accepted "
                    "schedule_request continuation request."
                ),
            },
            {
                "layer": "validator",
                "code": "valid_continue_rejected",
                "meaning": (
                    "The stricter validator rejected a valid continuation "
                    "request, creating a new failure mode."
                ),
            },
            {
                "layer": "artifact",
                "code": "first_pass_not_preserved",
                "meaning": "The probe did not preserve the raw first-pass output.",
            },
        ],
    }


def fixtures() -> list[JsonDict]:
    return [
        {
            "row_id": "invalid_continue_no_request",
            "expected": "classified_before_acceptance",
            "first_pass_output": {
                "response": (
                    "I should continue after this, but I have not supplied a "
                    "scheduler request."
                ),
                "policy_action": "continue_after",
            },
        },
        {
            "row_id": "invalid_continue_malformed_request",
            "expected": "classified_before_acceptance",
            "first_pass_output": {
                "response": "Resume me with the record later.",
                "schedule_requests": [
                    {
                        "purpose": "resume with malformed context",
                        "requested_context": {
                            "tool": "recall",
                            "record_id": str(RID),
                        },
                    }
                ],
                "policy_action": "continue_after",
            },
        },
        {
            "row_id": "valid_continue_with_request",
            "expected": "accepted",
            "first_pass_output": {
                "response": "I will continue after the scheduled recall wake.",
                "schedule_requests": [
                    {
                        "purpose": "resume with the record",
                        "requested_context": [
                            {
                                "tool": "recall",
                                "record_id": str(RID),
                            }
                        ],
                    }
                ],
                "policy_action": "continue_after",
            },
        },
        {
            "row_id": "stop_complete_no_request",
            "expected": "accepted",
            "first_pass_output": {
                "response": "This bounded item is complete.",
                "policy_action": "stop_complete",
            },
        },
    ]


def run_probe(output_dir: Path = ROOT_DIR) -> JsonDict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_dir = output_dir / "rows"
    if rows_dir.exists():
        for path in sorted(rows_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    rows_dir.mkdir(exist_ok=True)

    for name, payload in {
        "matrix.json": matrix(),
        "budget.json": budget_manifest(),
        "failure_taxonomy.json": failure_taxonomy(),
    }.items():
        write_json(output_dir / name, payload)

    started_at = now_iso()
    row_results = []
    for fixture in fixtures():
        row_results.append(run_row(rows_dir, fixture))
    finished_at = now_iso()

    summary = summarize(row_results)
    results = {
        "schema_version": "hamutay.strict_continuation_validation_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "started_at": started_at,
        "finished_at": finished_at,
        "live_model_calls": False,
        "row_count": len(row_results),
        "classification": summary["classification"],
        "interpretability_decision": summary["interpretability_decision"],
        "new_failure_mode": summary["new_failure_mode"],
        "row_results": row_results,
        "summary": summary,
    }
    write_json(output_dir / "results.json", results)
    (output_dir / "analysis.md").write_text(render_analysis(results), encoding="utf-8")
    return results


def run_row(rows_dir: Path, fixture: JsonDict) -> JsonDict:
    row_id = fixture["row_id"]
    row_dir = rows_dir / row_id
    row_dir.mkdir(parents=True, exist_ok=False)
    first_pass = deepcopy(fixture["first_pass_output"])
    trace = parse_autonomous_action(first_pass).to_dict()
    result = score_row(fixture=fixture, trace=trace)

    write_json(row_dir / "first_pass_output.json", first_pass)
    write_json(row_dir / "action_trace.json", trace)
    write_json(row_dir / "row_result.json", result)
    return result


def score_row(*, fixture: JsonDict, trace: JsonDict) -> JsonDict:
    first_pass = fixture["first_pass_output"]
    accepted_types = [
        action["action_type"] for action in trace.get("accepted_actions", [])
    ]
    rejection_codes = [
        rejection["code"] for rejection in trace.get("rejected_actions", [])
    ]
    parsed = trace.get("parsed_action") if isinstance(trace.get("parsed_action"), dict) else {}
    schedule_count = len(parsed.get("schedule_requests") or [])
    raw_policy = first_pass.get("policy_action")
    policy_accepted = "policy_action" in accepted_types
    continuation_intent = raw_policy == "continue_after" or response_mentions_continue(
        first_pass.get("response")
    )
    valid_continuation_request = schedule_count > 0
    continuation_mismatch = continuation_intent and not valid_continuation_request
    classified_before_acceptance = (
        REJECTION_CODE in rejection_codes and not policy_accepted
    )
    legacy_policy_would_accept = raw_policy == "continue_after"

    expected = fixture["expected"]
    if expected == "classified_before_acceptance":
        row_passed = classified_before_acceptance
    else:
        row_passed = (
            trace["validation_status"] == "accepted"
            and policy_accepted
            and REJECTION_CODE not in rejection_codes
        )

    if continuation_mismatch and classified_before_acceptance:
        interpretability = "improved_trace_interpretability"
    elif continuation_mismatch:
        interpretability = "unclassified_mismatch"
    elif row_passed:
        interpretability = "control_ok"
    else:
        interpretability = "unexpected_validator_failure"

    return {
        "row_id": fixture["row_id"],
        "expected": expected,
        "passed": row_passed,
        "validation_status": trace["validation_status"],
        "raw_policy_action": raw_policy,
        "policy_action_accepted": policy_accepted,
        "valid_continuation_request_count": schedule_count,
        "continuation_mismatch": continuation_mismatch,
        "classified_before_acceptance": classified_before_acceptance,
        "legacy_policy_would_accept": legacy_policy_would_accept,
        "rejection_codes": rejection_codes,
        "interpretability": interpretability,
        "artifact_paths": {
            "first_pass_output": f"rows/{fixture['row_id']}/first_pass_output.json",
            "action_trace": f"rows/{fixture['row_id']}/action_trace.json",
            "row_result": f"rows/{fixture['row_id']}/row_result.json",
        },
    }


def summarize(row_results: list[JsonDict]) -> JsonDict:
    failures = [row for row in row_results if not row["passed"]]
    invalid_rows = [
        row for row in row_results
        if row["expected"] == "classified_before_acceptance"
    ]
    valid_rows = [row for row in row_results if row["expected"] == "accepted"]
    invalid_classified = all(
        row["classified_before_acceptance"] for row in invalid_rows
    )
    valid_preserved = all(row["passed"] for row in valid_rows)
    improved_rows = [
        row for row in row_results
        if row["interpretability"] == "improved_trace_interpretability"
    ]
    new_failure_mode = not valid_preserved
    if not failures and invalid_classified:
        classification = "survived"
        decision = (
            "Stricter continuation validation improved trace interpretability "
            "without creating a new failure mode in this probe."
        )
    elif new_failure_mode:
        classification = "boundary"
        decision = (
            "The validator classified invalid continuations, but also rejected "
            "a valid control row, so it may create a new failure mode."
        )
    else:
        classification = "falsified"
        decision = (
            "At least one invalid continue_after row was not classified before "
            "policy acceptance."
        )
    return {
        "classification": classification,
        "interpretability_decision": decision,
        "new_failure_mode": new_failure_mode,
        "failed_rows": [row["row_id"] for row in failures],
        "invalid_rows_classified_before_acceptance": invalid_classified,
        "valid_rows_preserved": valid_preserved,
        "improved_trace_rows": [row["row_id"] for row in improved_rows],
    }


def response_mentions_continue(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return any(word in lowered for word in ("continue", "resume", "later"))


def render_analysis(results: JsonDict) -> str:
    lines = [
        "# Strict Continuation Validation Analysis",
        "",
        f"Experiment ID: `{EXPERIMENT_ID}`",
        "",
        "## Result",
        "",
        f"- Classification: `{results['classification']}`",
        f"- Live model calls: `{results['live_model_calls']}`",
        f"- Rows: `{results['row_count']}`",
        f"- New failure mode observed: `{results['new_failure_mode']}`",
        f"- Decision: {results['interpretability_decision']}",
        "",
        "## Rows",
        "",
        "| Row | Expected | Passed | Validation | Policy accepted | Valid requests | Classified before acceptance | Legacy would accept | Interpretation |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in results["row_results"]:
        lines.append(
            f"| {row['row_id']} | `{row['expected']}` | {row['passed']} | "
            f"`{row['validation_status']}` | {row['policy_action_accepted']} | "
            f"{row['valid_continuation_request_count']} | "
            f"{row['classified_before_acceptance']} | "
            f"{row['legacy_policy_would_accept']} | "
            f"`{row['interpretability']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            results["interpretability_decision"],
            "",
            "The two invalid `continue_after` fixtures would have passed a "
            "vocabulary-only policy-action check, but the strict validator now "
            "records an explicit policy rejection before acceptance. The raw "
            "first-pass objects remain available in row artifacts, so the "
            "failure is inspectable rather than silently repaired.",
            "",
            "## Artifact Trail",
            "",
            "- `PRE_REGISTRATION.md` defines H5 and falsification conditions.",
            "- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the execution frame.",
            "- `rows/<row_id>/first_pass_output.json` preserves each authored first pass.",
            "- `rows/<row_id>/action_trace.json` preserves accepted and rejected subactions.",
            "- `rows/<row_id>/row_result.json` preserves row-level scoring.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--write-prereg", action="store_true")
    args = parser.parse_args()
    if args.write_prereg:
        for name, payload in {
            "matrix.json": matrix(),
            "budget.json": budget_manifest(),
            "failure_taxonomy.json": failure_taxonomy(),
        }.items():
            write_json(ROOT_DIR / name, payload)
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "preregistered": True}, indent=2))
        return
    if args.run:
        print(json.dumps(run_probe(), indent=2, sort_keys=True))
        return
    parser.error("choose --write-prereg or --run")


if __name__ == "__main__":
    main()
