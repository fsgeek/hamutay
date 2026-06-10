"""Gate artifacts and no-token dry run for the first live autonomy pilot."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hamutay.memory.rehearsal import (
    RehearsalInterrupted,
    RehearsalPaths,
    RestartableAutonomyRehearsal,
    run_fake_autonomy_rehearsal,
)


JsonDict = dict[str, Any]

PILOT_ID = "live_autonomy_pilot_20260609"
DEFAULT_MODEL = "deepseek/deepseek-v4-pro"
DEFAULT_PROVIDER = "openrouter"
DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1"
DEFAULT_OUTPUT_DIR = Path("experiments/live_autonomy_pilot_20260609/dry_run")
REQUIRED_FAILURE_LAYERS = {
    "model",
    "protocol",
    "harness",
    "substrate",
    "provider",
    "scorer",
    "restart_boundary",
    "sandbox",
}


@dataclass(frozen=True)
class PilotGateResult:
    """Result of evaluating one no-token pilot gate case."""

    case_id: str
    passed: bool
    report_path: Path
    report: JsonDict
    failures: list[JsonDict]

    def to_dict(self) -> JsonDict:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "report_path": str(self.report_path),
            "failures": deepcopy(self.failures),
            "report": deepcopy(self.report),
        }


def sandbox_manifest(*, live_model_calls: bool = False) -> JsonDict:
    """Return the preregistered first-pilot sandbox posture."""

    return {
        "schema_version": "hamutay.autonomy_pilot_sandbox.v1",
        "pilot_id": PILOT_ID,
        "live_model_calls": live_model_calls,
        "enforcement_level": "in_process_detective",
        "enforcement_note": (
            "Disabled shell/network/filesystem entries mean those surfaces are "
            "not exposed through model-visible harness APIs. This is detective "
            "auditability, not OS-level containment."
        ),
        "filesystem": {
            "repo_access": "read_only_for_model",
            "allowed_write_roots": [
                "experiments/live_autonomy_pilot_20260609/runs/<run_id>",
            ],
            "model_direct_filesystem_access": False,
        },
        "tools": {
            "shell": "disabled",
            "network_tools": "disabled",
            "model_visible_tools": [
                "memory_action_object",
            ],
            "harness_only_tools": [
                "ActionLedger",
                "EventStore",
                "RestartFrontierStore",
                "LocalMemorySubstrate",
            ],
        },
        "secrets": {
            "model_can_read_environment": False,
            "redaction_policy": "default_preserve_non_secret_values",
            "api_key_source": "operator_environment_only",
        },
        "model": {
            "provider": DEFAULT_PROVIDER,
            "model": DEFAULT_MODEL,
            "endpoint": DEFAULT_ENDPOINT,
            "endpoint_contract": "openai_compatible_chat_completions",
            "allow_fallbacks": False,
        },
        "audit_storage": {
            "action_ledger": "actions.jsonl",
            "event_log": "events.jsonl",
            "restart_frontier": "restart_frontier.jsonl",
            "memory_snapshot": "memory_snapshot.json",
            "tamper_evidence": "hash_chained_action_ledger",
        },
    }


def token_cycle_budget() -> JsonDict:
    """Return the preregistered budget for the first live run."""

    return {
        "schema_version": "hamutay.autonomy_pilot_budget.v1",
        "pilot_id": PILOT_ID,
        "max_cycles": 2,
        "max_scheduled_wakes": 1,
        "max_input_tokens_per_cycle": 8000,
        "max_output_tokens_per_cycle": 2000,
        "max_total_tokens": 20000,
        "max_wall_time_seconds": 600,
        "max_estimated_cost_usd": 1.00,
        "stop_conditions": [
            "policy_action.stop_complete",
            "budget.max_cycles",
            "unclassified_failure",
            "restart_frontier_unclean",
        ],
    }


def failure_taxonomy() -> JsonDict:
    """Return layer-classified failure vocabulary for the pilot gate."""

    entries = [
        (
            "model",
            "model_action_missing",
            "Model output did not contain a scoreable action object.",
        ),
        (
            "model",
            "model_policy_incoherent",
            "Model-authored policy action contradicts the artifact state.",
        ),
        (
            "protocol",
            "invalid_action_schema",
            "Action parsing or validation rejected required model output.",
        ),
        (
            "protocol",
            "tool_protocol_failure",
            "Provider/tool protocol returned malformed or unusable data.",
        ),
        (
            "harness",
            "invariant_failure",
            "Evaluator invariant failed on reconstructed artifacts.",
        ),
        (
            "harness",
            "hidden_inference_refused",
            "Harness refused an operation requiring hidden intent inference.",
        ),
        (
            "substrate",
            "action_ledger_verification_failed",
            "Hash-chain verification failed for the action ledger.",
        ),
        (
            "substrate",
            "memory_or_event_substrate_error",
            "Memory, event, or frontier substrate returned an operation error.",
        ),
        (
            "provider",
            "provider_api_error",
            "Remote model provider returned an API or transport error.",
        ),
        (
            "provider",
            "provider_budget_or_timeout",
            "Provider call exceeded timeout, token, or cost budget.",
        ),
        (
            "scorer",
            "report_unscoreable",
            "Evaluator cannot classify the run from preserved artifacts.",
        ),
        (
            "scorer",
            "scorer_internal_error",
            "Evaluator failed independently of model or substrate behavior.",
        ),
        (
            "restart_boundary",
            "restart_frontier_unclean",
            "Restart frontier contains uncommitted ledger records.",
        ),
        (
            "restart_boundary",
            "resume_recovery_failed",
            "Interrupted run did not recover or suppress events coherently.",
        ),
        (
            "sandbox",
            "sandbox_manifest_violation",
            "Observed run attempted an operation outside the manifest.",
        ),
    ]
    return {
        "schema_version": "hamutay.autonomy_failure_taxonomy.v1",
        "pilot_id": PILOT_ID,
        "required_layers": sorted(REQUIRED_FAILURE_LAYERS),
        "entries": [
            {"layer": layer, "code": code, "description": description}
            for layer, code, description in entries
        ],
    }


def classify_report_failures(report: JsonDict) -> list[JsonDict]:
    """Classify observable report failures by layer."""

    failures: list[JsonDict] = []
    ledger_verification = report.get("ledger_verification", {})
    if ledger_verification.get("ok") is not True:
        failures.append(
            {
                "layer": "substrate",
                "code": "action_ledger_verification_failed",
                "evidence": ledger_verification,
            }
        )
    ignored_count = int(report.get("ignored_ledger_count", 0) or 0)
    if ignored_count:
        failures.append(
            {
                "layer": "restart_boundary",
                "code": "restart_frontier_unclean",
                "evidence": {"ignored_ledger_count": ignored_count},
            }
        )
    for invariant in report.get("invariant_failures", []) or []:
        failures.append(
            {
                "layer": "harness",
                "code": "invariant_failure",
                "evidence": {"invariant": invariant},
            }
        )
    if int(report.get("action_trace_count", 0) or 0) < 2:
        failures.append(
            {
                "layer": "model",
                "code": "model_action_missing",
                "evidence": {
                    "action_trace_count": report.get("action_trace_count"),
                },
            }
        )
    invariants = report.get("invariants")
    if (
        isinstance(invariants, dict)
        and invariants.get("stop_policy_consistent_with_idle") is False
    ):
        failures.append(
            {
                "layer": "model",
                "code": "model_policy_incoherent",
                "evidence": {
                    "invariant": "stop_policy_consistent_with_idle",
                    "value": False,
                },
            }
        )
    return failures


def evaluate_pilot_report(report: JsonDict, *, case_id: str) -> JsonDict:
    """Evaluate one reconstructed pilot report against the dry-run gate."""

    failures = classify_report_failures(report)
    required_invariants = {
        "ledger_verified",
        "restart_frontier_clean",
        "closed_handle_had_prior_open_item",
        "stop_policy_consistent_with_idle",
        "event_reached_completed",
        "no_pending_or_running_events",
    }
    missing_invariants = sorted(
        required_invariants - set((report.get("invariants") or {}).keys())
    )
    if missing_invariants:
        failures.append(
            {
                "layer": "scorer",
                "code": "report_unscoreable",
                "evidence": {"missing_invariants": missing_invariants},
            }
        )
    return {
        "schema_version": "hamutay.autonomy_pilot_evaluation.v1",
        "pilot_id": PILOT_ID,
        "case_id": case_id,
        "passed": not failures,
        "failures": failures,
        "taxonomy_layers_available": sorted(_taxonomy_layers()),
        "required_layers_available": (
            _taxonomy_layers() >= REQUIRED_FAILURE_LAYERS
        ),
    }


def run_no_token_dry_run_gate(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> JsonDict:
    """Run the first-pilot dry gate without model/provider calls."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "sandbox_manifest.json", sandbox_manifest())
    _write_json(output / "token_cycle_budget.json", token_cycle_budget())
    _write_json(output / "failure_taxonomy.json", failure_taxonomy())

    clean = _run_clean_case(output / "clean_reconstruction")
    resumed = _run_resume_case(output / "resume_after_event_claim")
    cases = [clean, resumed]
    gate_report = {
        "schema_version": "hamutay.autonomy_pilot_dry_run_gate.v1",
        "pilot_id": PILOT_ID,
        "live_model_calls": False,
        "sandbox_manifest": str(output / "sandbox_manifest.json"),
        "token_cycle_budget": str(output / "token_cycle_budget.json"),
        "failure_taxonomy": str(output / "failure_taxonomy.json"),
        "case_count": len(cases),
        "cases": [case.to_dict() for case in cases],
        "passed": all(case.passed for case in cases),
    }
    _write_json(output / "dry_run_gate_report.json", gate_report)
    return gate_report


def _run_clean_case(root: Path) -> PilotGateResult:
    result = run_fake_autonomy_rehearsal(output_dir=root)
    report = result.to_dict()
    report_path = root / "reconstructed_report.json"
    _write_json(report_path, report)
    evaluation = evaluate_pilot_report(report, case_id="clean_reconstruction")
    _write_json(root / "evaluation.json", evaluation)
    return PilotGateResult(
        case_id="clean_reconstruction",
        passed=bool(evaluation["passed"]),
        report_path=report_path,
        report=report,
        failures=deepcopy(evaluation["failures"]),
    )


def _run_resume_case(root: Path) -> PilotGateResult:
    paths = RehearsalPaths.from_root(root)
    runner = RestartableAutonomyRehearsal(paths=paths)
    try:
        runner.run(interrupt_after="after_event_claim")
    except RehearsalInterrupted:
        pass
    report = RestartableAutonomyRehearsal(paths=paths).run().to_dict()
    report_path = root / "reconstructed_report.json"
    _write_json(report_path, report)
    evaluation = evaluate_pilot_report(report, case_id="resume_after_event_claim")
    if not _has_running_to_pending_recovery(report):
        evaluation["passed"] = False
        evaluation["failures"].append(
            {
                "layer": "restart_boundary",
                "code": "resume_recovery_failed",
                "evidence": {
                    "recovered_event_count": report.get(
                        "recovered_event_count"
                    ),
                    "event_statuses": report.get("event_statuses", []),
                },
            }
        )
    _write_json(root / "evaluation.json", evaluation)
    return PilotGateResult(
        case_id="resume_after_event_claim",
        passed=bool(evaluation["passed"]),
        report_path=report_path,
        report=report,
        failures=deepcopy(evaluation["failures"]),
    )


def _has_running_to_pending_recovery(report: JsonDict) -> bool:
    statuses_by_event: dict[str, list[str]] = {}
    for item in report.get("event_statuses", []):
        if item.get("record_type") != "event_status":
            continue
        event_id = item.get("event_id")
        status = item.get("status")
        if event_id is None or status is None:
            continue
        statuses_by_event.setdefault(str(event_id), []).append(str(status))
    return any(
        current == "running" and next_status == "pending"
        for statuses in statuses_by_event.values()
        for current, next_status in zip(statuses, statuses[1:])
    )


def _taxonomy_layers() -> set[str]:
    return {
        str(entry["layer"])
        for entry in failure_taxonomy()["entries"]
    }


def _write_json(path: Path, payload: JsonDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the no-token gate for the first live autonomy pilot."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for dry-run artifacts.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run_no_token_dry_run_gate(args.output_dir),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
