"""Run the Goal 5 audit/restart boundary readiness validation."""

from __future__ import annotations

import argparse
import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.actions import parse_autonomous_action
from hamutay.memory.rehearsal import (
    RehearsalInterrupted,
    RehearsalPaths,
    RestartableAutonomyRehearsal,
    reconstruct_rehearsal_report,
    run_fake_autonomy_rehearsal,
)


JsonDict = dict[str, Any]

EXPERIMENT_ID = "audit_restart_boundary_20260612"
ROOT_DIR = Path(__file__).resolve().parent
REQUIRED_FAILURE_LAYERS = {
    "model",
    "protocol",
    "harness",
    "substrate",
    "provider",
    "scorer",
    "restart_boundary",
}


def matrix() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": False,
        "rows": [
            {"row_id": "happy_rehearsal", "kind": "completion"},
            {"row_id": "resume_after_seed_apply", "kind": "interruption_resume"},
            {"row_id": "resume_after_event_claim", "kind": "interruption_resume"},
            {"row_id": "rejected_operation_trace", "kind": "rejection_audit"},
            {"row_id": "tamper_detection", "kind": "hash_chain"},
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
        "schema_version": "hamutay.audit_restart_boundary_taxonomy.v1",
        "layers": sorted(REQUIRED_FAILURE_LAYERS),
        "entries": [
            {
                "layer": "restart_boundary",
                "code": "frontier_not_clean",
                "meaning": "The run cannot resume from a committed frontier.",
            },
            {
                "layer": "harness",
                "code": "missing_audit_artifact",
                "meaning": "A required audit artifact is absent.",
            },
            {
                "layer": "substrate",
                "code": "ledger_tamper_detection_failed",
                "meaning": "Hash-chain verification did not detect mutation.",
            },
            {
                "layer": "scorer",
                "code": "readiness_report_incomplete",
                "meaning": "The replay report cannot answer Goal 5 questions.",
            },
        ],
    }


def write_preregistration(output_dir: Path = ROOT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in {
        "matrix.json": matrix(),
        "budget.json": budget_manifest(),
        "failure_taxonomy.json": failure_taxonomy(),
    }.items():
        write_json(output_dir / name, payload)


def run_readiness(output_dir: Path = ROOT_DIR) -> JsonDict:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_preregistration(output_dir)
    rows_dir = output_dir / "rows"
    if rows_dir.exists():
        shutil.rmtree(rows_dir)
    rows_dir.mkdir()

    started_at = now_iso()
    rows = [
        run_happy_rehearsal(rows_dir),
        run_resume_after_seed_apply(rows_dir),
        run_resume_after_event_claim(rows_dir),
        run_rejected_operation_trace(rows_dir),
        run_tamper_detection(rows_dir),
    ]
    summary = summarize(rows)
    results = {
        "schema_version": "hamutay.audit_restart_boundary_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "started_at": started_at,
        "finished_at": now_iso(),
        "live_model_calls": False,
        "classification": summary["classification"],
        "ready_for_goal_6": summary["ready_for_goal_6"],
        "row_count": len(rows),
        "rows": rows,
        "summary": summary,
    }
    write_json(output_dir / "results.json", results)
    (output_dir / "analysis.md").write_text(render_analysis(results), encoding="utf-8")
    return results


def run_happy_rehearsal(rows_dir: Path) -> JsonDict:
    row_dir = rows_dir / "happy_rehearsal"
    run_dir = row_dir / "run"
    report = run_fake_autonomy_rehearsal(output_dir=run_dir).to_dict()
    reconstructed = reconstruct_rehearsal_report(RehearsalPaths.from_root(run_dir))
    row = rehearsal_row(
        row_id="happy_rehearsal",
        report=report,
        extra_checks={"report_matches_reconstruction": report == reconstructed},
    )
    write_json(row_dir / "report.json", report)
    write_json(row_dir / "row_result.json", row)
    return row


def run_resume_after_seed_apply(rows_dir: Path) -> JsonDict:
    row_dir = rows_dir / "resume_after_seed_apply"
    run_dir = row_dir / "run"
    paths = RehearsalPaths.from_root(run_dir)
    interrupted = False
    try:
        RestartableAutonomyRehearsal(paths=paths).run(
            interrupt_after="after_seed_apply"
        )
    except RehearsalInterrupted:
        interrupted = True
    report = RestartableAutonomyRehearsal(paths=paths).run().to_dict()
    row = rehearsal_row(
        row_id="resume_after_seed_apply",
        report=report,
        extra_checks={
            "interruption_observed": interrupted,
            "suppressed_uncommitted_event": report["suppressed_event_count"] >= 1,
        },
    )
    write_json(row_dir / "report.json", report)
    write_json(row_dir / "row_result.json", row)
    return row


def run_resume_after_event_claim(rows_dir: Path) -> JsonDict:
    row_dir = rows_dir / "resume_after_event_claim"
    run_dir = row_dir / "run"
    paths = RehearsalPaths.from_root(run_dir)
    interrupted = False
    try:
        RestartableAutonomyRehearsal(paths=paths).run(
            interrupt_after="after_event_claim"
        )
    except RehearsalInterrupted:
        interrupted = True
    report = RestartableAutonomyRehearsal(paths=paths).run().to_dict()
    row = rehearsal_row(
        row_id="resume_after_event_claim",
        report=report,
        extra_checks={
            "interruption_observed": interrupted,
            "recovered_running_event": report["recovered_event_count"] >= 1,
        },
    )
    write_json(row_dir / "report.json", report)
    write_json(row_dir / "row_result.json", row)
    return row


def run_rejected_operation_trace(rows_dir: Path) -> JsonDict:
    row_dir = rows_dir / "rejected_operation_trace"
    row_dir.mkdir(parents=True, exist_ok=True)
    ledger = ActionLedger(row_dir / "actions.jsonl")
    ledger.append_run_manifest(
        run_id="rejected-operation-trace",
        manifest={"experiment_id": EXPERIMENT_ID, "row_id": "rejected_operation_trace"},
        sandbox={"live_model_calls": False, "tool_surface": "action parser only"},
    )
    raw = {
        "response": "Continue later without a schedule request.",
        "policy_action": "continue_after",
    }
    trace = parse_autonomous_action(raw).to_dict()
    ledger.append_action_trace(
        run_id="rejected-operation-trace",
        cycle_id=1,
        trace=trace,
    )
    ledger.append_validation_operations(
        run_id="rejected-operation-trace",
        cycle_id=1,
        trace=trace,
    )
    records = ledger.read_records()
    operations = [
        record["payload"] for record in records
        if record.get("record_type") == "operation"
    ]
    rejected = [
        op for op in operations
        if op.get("result_status") == "rejected"
    ]
    verification = ledger.verify().to_dict()
    row = {
        "row_id": "rejected_operation_trace",
        "passed": bool(
            verification["ok"]
            and trace["raw_output"] == raw
            and rejected
            and any(
                op.get("error", {}).get("code")
                == "continue_after_without_continuation_request"
                for op in rejected
            )
        ),
        "ledger_verification": verification,
        "raw_output_preserved": trace["raw_output"] == raw,
        "rejected_operation_count": len(rejected),
        "operation_statuses": [
            {
                "operation_type": op.get("operation_type"),
                "result_status": op.get("result_status"),
                "error": deepcopy(op.get("error")),
            }
            for op in operations
        ],
        "artifact_paths": {
            "ledger": "rows/rejected_operation_trace/actions.jsonl",
            "action_trace": "rows/rejected_operation_trace/action_trace.json",
        },
    }
    write_json(row_dir / "first_pass_output.json", raw)
    write_json(row_dir / "action_trace.json", trace)
    write_json(row_dir / "row_result.json", row)
    return row


def run_tamper_detection(rows_dir: Path) -> JsonDict:
    row_dir = rows_dir / "tamper_detection"
    row_dir.mkdir(parents=True, exist_ok=True)
    path = row_dir / "actions.jsonl"
    ledger = ActionLedger(path)
    ledger.append_run_manifest(
        run_id="tamper-detection",
        manifest={"experiment_id": EXPERIMENT_ID, "row_id": "tamper_detection"},
    )
    ledger.append_operation(
        run_id="tamper-detection",
        operation_id="op-1",
        operation_type="noop",
        actor="harness",
        result_status="accepted",
        result={"ok": True},
    )
    before = ledger.verify().to_dict()
    records = ledger.read_records()
    records[0]["payload"]["manifest"]["row_id"] = "tampered"
    (row_dir / "tampered_actions.jsonl").write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )
    after = ledger.verify().to_dict()
    row = {
        "row_id": "tamper_detection",
        "passed": before["ok"] is True and after["ok"] is False,
        "verification_before_tamper": before,
        "verification_after_tamper": after,
        "artifact_paths": {
            "tampered_ledger": "rows/tamper_detection/tampered_actions.jsonl"
        },
    }
    write_json(row_dir / "row_result.json", row)
    return row


def rehearsal_row(
    *,
    row_id: str,
    report: JsonDict,
    extra_checks: JsonDict,
) -> JsonDict:
    checks = {
        "ledger_verified": report["ledger_verification"]["ok"] is True,
        "frontier_clean": report["invariants"]["restart_frontier_clean"] is True,
        "model_inputs_recorded": report["invariants"]["model_inputs_recorded"] is True,
        "model_emissions_recorded": report["invariants"]["model_emissions_recorded"] is True,
        "accepted_rejected_actions_reconstructable": report["invariants"][
            "accepted_rejected_actions_reconstructable"
        ] is True,
        "memory_operations_recorded": report["invariants"]["memory_operations_recorded"] is True,
        "scheduler_operations_recorded": report["invariants"][
            "scheduler_operations_recorded"
        ] is True,
        "run_manifest_recorded": report["invariants"]["run_manifest_recorded"] is True,
        "policy_disposition_recorded": report["invariants"]["stop_policy_recorded"] is True,
        "idle_due_to_model_closure": report[
            "no_open_items_due_to_model_authored_closure"
        ] is True,
        "failure_taxonomy_layers_present": REQUIRED_FAILURE_LAYERS.issubset(
            set(report["failure_taxonomy_layers"])
        ),
        **extra_checks,
    }
    return {
        "row_id": row_id,
        "passed": all(checks.values()),
        "checks": checks,
        "frontier": deepcopy(report["frontier"]),
        "operation_count": len(report["operations"]),
        "memory_operation_count": len(report["memory_operations"]),
        "scheduler_operation_count": len(report["scheduler_operations"]),
        "action_trace_count": report["action_trace_count"],
        "invariant_failures": deepcopy(report["invariant_failures"]),
        "artifact_paths": {
            "report": f"rows/{row_id}/report.json",
            "ledger": f"rows/{row_id}/run/actions.jsonl",
            "events": f"rows/{row_id}/run/events.jsonl",
            "frontier": f"rows/{row_id}/run/restart_frontier.jsonl",
            "memory_snapshot": f"rows/{row_id}/run/memory_snapshot.json",
        },
    }


def summarize(rows: list[JsonDict]) -> JsonDict:
    failed = [row["row_id"] for row in rows if not row["passed"]]
    ready = not failed
    return {
        "classification": "survived" if ready else "falsified",
        "ready_for_goal_6": ready,
        "failed_rows": failed,
        "passed_rows": [row["row_id"] for row in rows if row["passed"]],
        "decision": (
            "Audit/restart boundary is ready for less-scaffolded no-token or "
            "tiny-token autonomy panels."
            if ready else
            "Audit/restart boundary is not ready; at least one required row failed."
        ),
    }


def render_analysis(results: JsonDict) -> str:
    lines = [
        "# Audit/Restart Boundary Readiness Analysis",
        "",
        f"Experiment ID: `{EXPERIMENT_ID}`",
        "",
        "## Result",
        "",
        f"- Classification: `{results['classification']}`",
        f"- Ready for Goal 6: `{results['ready_for_goal_6']}`",
        f"- Live model calls: `{results['live_model_calls']}`",
        f"- Rows: `{results['row_count']}`",
        f"- Decision: {results['summary']['decision']}",
        "",
        "## Rows",
        "",
        "| Row | Passed | Key evidence |",
        "| --- | ---: | --- |",
    ]
    for row in results["rows"]:
        if "checks" in row:
            failed_checks = [
                key for key, ok in row["checks"].items() if not ok
            ]
            evidence = (
                "all readiness checks passed"
                if not failed_checks else f"failed checks: {failed_checks}"
            )
        elif row["row_id"] == "tamper_detection":
            evidence = "tamper detected by hash-chain verification"
        else:
            evidence = f"rejected operations: {row.get('rejected_operation_count')}"
        lines.append(f"| {row['row_id']} | {row['passed']} | {evidence} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            results["summary"]["decision"],
            "",
            "The readiness rows preserve model-facing wake inputs, raw model "
            "emissions, accepted/rejected action traces, scheduler event "
            "lifecycle records, memory operations, policy dispositions, run "
            "manifests, restart frontiers, and replay reports. Tampering with "
            "the action ledger is detected by hash-chain verification.",
            "",
            "## Artifact Trail",
            "",
            "- `PRE_REGISTRATION.md` fixes H6 and falsification conditions.",
            "- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the execution frame.",
            "- `rows/<row_id>/report.json` preserves replay reports for rehearsal rows.",
            "- `rows/<row_id>/run/actions.jsonl`, `events.jsonl`, `restart_frontier.jsonl`, and `memory_snapshot.json` preserve persisted run state.",
            "- `rows/rejected_operation_trace/action_trace.json` preserves a rejected first-pass action.",
            "- `rows/tamper_detection/tampered_actions.jsonl` preserves the mutated ledger used for tamper detection.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-prereg", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.write_prereg:
        write_preregistration()
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "preregistered": True}, indent=2))
        return
    if args.run:
        print(json.dumps(run_readiness(), indent=2, sort_keys=True))
        return
    parser.error("choose --write-prereg or --run")


if __name__ == "__main__":
    main()
