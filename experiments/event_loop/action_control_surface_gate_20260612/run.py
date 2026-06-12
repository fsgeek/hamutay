"""Run the Goal 1 action/control surface gate."""

from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from hamutay.memory.contract_literacy import (
    call_openrouter_action,
    evaluate_cycle1_action_object,
    failure_taxonomy as literacy_failure_taxonomy,
)
from hamutay.memory.contract_salience import secondary_recovery_evaluation
from hamutay.memory.failure_attribution import classify_action_row_failure
from hamutay.memory.live_pilot import _seed_messages


JsonDict = dict[str, Any]

EXPERIMENT_ID = "action_control_surface_gate_20260612"
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_ENDPOINT = "https://api.deepseek.com"
MODEL_KEY = "deepseek_v4_pro"
MODEL_ID = "deepseek-v4-pro"
LIVE_ROWS = 3
BASE_EVALUATOR_CONDITION_ID = "B_example_prompt_strict_contract"
ACTIONABLE_ATTRIBUTIONS = {
    "passed_primary_strict",
    "provider_substrate_failure",
    "protocol_transport_failure",
    "prompt_transport_contract",
    "prompt_schema_contract",
    "parser_recovery_boundary",
    "model_contract_boundary",
    "harness_failure",
    "substrate_failure",
    "scorer_failure",
}


def matrix() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_calls_per_condition": LIVE_ROWS,
        "conditions": [
            {
                "condition_id": "deepseek_v4_pro__hardened_live_action_surface",
                "model_key": MODEL_KEY,
                "model_id": MODEL_ID,
                "provider": "DeepSeek direct OpenAI-compatible",
                "endpoint_family": "deepseek_openai_chat",
                "endpoint_default": DEFAULT_ENDPOINT,
                "prompt_condition": "hardened_live_action_surface",
                "prompt_source": "hamutay.memory.live_pilot._action_object_system_prompt",
                "prompt_addendum_application": "none",
                "prompt_addendum": "",
                "base_evaluator_condition_id": BASE_EVALUATOR_CONDITION_ID,
                "contract": "strict_autonomous_action_v1",
                "acceptance_rule": (
                    "primary strict parser requires one accepted open_item and "
                    "one accepted schedule_request"
                ),
            }
        ],
    }


def budget_manifest() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "max_live_calls": LIVE_ROWS,
        "max_calls_per_condition": LIVE_ROWS,
        "max_cycles_per_call": 1,
        "max_output_tokens_per_call": None,
        "output_cap_policy": (
            "No artificial output cap; provider/model limits still apply."
        ),
        "max_estimated_cost_usd": 1.0,
        "stop_rule": (
            "Run exactly three planned rows unless missing credentials or a "
            "local harness error prevents preserving row artifacts."
        ),
    }


def failure_taxonomy() -> JsonDict:
    inherited = literacy_failure_taxonomy()
    return {
        "experiment_id": EXPERIMENT_ID,
        "source_taxonomy": inherited["schema_version"],
        "schema_version": "hamutay.action_control_surface_gate_taxonomy.v1",
        "entries": inherited["entries"]
        + [
            {
                "layer": "prompt_transport",
                "code": "visible_json_contract_failure",
                "meaning": (
                    "The row failed because visible content did not contain "
                    "exactly one parseable action object."
                ),
            },
            {
                "layer": "prompt_schema",
                "code": "nested_requested_context_contract_failure",
                "meaning": (
                    "The row failed because the nested requested_context list "
                    "or policy-field surface was not salient enough."
                ),
            },
            {
                "layer": "parser_recovery",
                "code": "secondary_recovery_strict_valid",
                "meaning": (
                    "Primary strict scoring failed, but secondary recovery "
                    "found a strict-valid action object. This remains audit "
                    "evidence only."
                ),
            },
        ],
    }


def write_preregistration_artifacts(output_dir: Path = ROOT_DIR) -> JsonDict:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matrix.json": matrix(),
        "budget.json": budget_manifest(),
        "failure_taxonomy.json": failure_taxonomy(),
    }
    for name, payload in artifacts.items():
        _write_json(output_dir / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": False,
        "output_dir": str(output_dir),
        "artifacts": sorted(artifacts),
        "preregistration": str(output_dir / "PRE_REGISTRATION.md"),
    }


def execute_live(
    *,
    output_dir: Path = ROOT_DIR,
    api_key: str,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout_seconds: float = 120.0,
) -> JsonDict:
    if not api_key:
        raise ValueError("api_key is required")

    output_dir.mkdir(parents=True, exist_ok=True)
    rows_dir = output_dir / "rows"
    rows_dir.mkdir(exist_ok=False)

    for name, payload in {
        "matrix.json": matrix(),
        "budget.json": budget_manifest(),
        "failure_taxonomy.json": failure_taxonomy(),
    }.items():
        _write_json(output_dir / name, payload)

    started_at = _now_iso()
    condition = matrix()["conditions"][0]
    row_results: list[JsonDict] = []
    for repetition in range(1, LIVE_ROWS + 1):
        provider = call_openrouter_action(
            api_key=api_key,
            endpoint=endpoint,
            model=MODEL_ID,
            messages=messages_for_row(condition, repetition=repetition),
            timeout_seconds=timeout_seconds,
            include_openrouter_options=False,
        )
        row_results.append(
            write_evaluated_row(
                condition=condition,
                repetition=repetition,
                rows_dir=rows_dir,
                provider=provider,
                endpoint=endpoint,
            )
        )

    summary = summarize_results(
        row_results=row_results,
        output_dir=output_dir,
        endpoint=endpoint,
        started_at=started_at,
        finished_at=_now_iso(),
    )
    _write_json(output_dir / "results.json", summary)
    (output_dir / "analysis.md").write_text(render_analysis(summary) + "\n")
    return summary


def messages_for_row(condition: JsonDict, *, repetition: int) -> list[JsonDict]:
    result_record_id = uuid5(
        NAMESPACE_URL,
        f"hamutay:{EXPERIMENT_ID}:{condition['condition_id']}:r{repetition:02d}",
    )
    return _seed_messages(result_record_id=result_record_id)


def write_evaluated_row(
    *,
    condition: JsonDict,
    repetition: int,
    rows_dir: Path,
    provider: JsonDict,
    endpoint: str,
) -> JsonDict:
    row_id = f"{condition['condition_id']}__r{repetition:02d}"
    row_dir = rows_dir / row_id
    row_dir.mkdir()
    _write_json(row_dir / "provider_request.json", provider["request_payload"])
    _write_json(row_dir / "provider_response.json", provider["response_payload"])
    _write_json(row_dir / "provider_attempts.json", {"attempts": provider["attempts"]})

    if provider["action_object"] is not None:
        raw_output: Any = provider["action_object"]
        _write_json(row_dir / "action_object.json", provider["action_object"])
    else:
        raw_output = provider.get("raw_content")

    strict_evaluation = evaluate_cycle1_action_object(
        raw_output,
        condition_id=str(condition["base_evaluator_condition_id"]),
        relaxed_open_item_contract=False,
    )
    relaxed_evaluation = evaluate_cycle1_action_object(
        raw_output,
        condition_id=str(condition["base_evaluator_condition_id"]),
        relaxed_open_item_contract=True,
    )
    row_result = {
        "schema_version": "hamutay.action_control_surface_gate_row.v1",
        "experiment_id": EXPERIMENT_ID,
        "row_id": row_id,
        "condition_id": condition["condition_id"],
        "model_key": condition["model_key"],
        "model_id": condition["model_id"],
        "prompt_condition": condition["prompt_condition"],
        "repetition": repetition,
        "condition": deepcopy(condition),
        "endpoint": endpoint,
        "endpoint_family": condition["endpoint_family"],
        "provider_ok": provider["ok"],
        "provider_failure": provider.get("failure"),
        "raw_content": provider.get("raw_content"),
        "usage": provider.get("usage", {}),
        "elapsed_seconds": provider.get("elapsed_seconds"),
        "provider_attempts": provider.get("attempts", []),
        "strict_evaluation": strict_evaluation,
        "relaxed_evaluation": relaxed_evaluation,
    }
    recovery_evaluation = secondary_recovery_evaluation(row_result)
    if recovery_evaluation["recovery_attempted"]:
        row_result["recovery_evaluation"] = recovery_evaluation
        _write_json(row_dir / "recovery_evaluation.json", recovery_evaluation)
    row_result["failure_attribution"] = classify_action_row_failure(row_result)

    _write_json(row_dir / "strict_evaluation.json", strict_evaluation)
    _write_json(row_dir / "relaxed_evaluation.json", relaxed_evaluation)
    _write_json(row_dir / "row_result.json", row_result)
    return row_result


def summarize_results(
    *,
    row_results: list[JsonDict],
    output_dir: Path,
    endpoint: str,
    started_at: str,
    finished_at: str,
) -> JsonDict:
    strict_pass_count = sum(
        1
        for row in row_results
        if row["strict_evaluation"]["strict_required_actions_valid"]
    )
    relaxed_pass_count = sum(
        1
        for row in row_results
        if row["relaxed_evaluation"]["relaxed_required_actions_valid"]
    )
    primary_scorable_count = sum(
        1 for row in row_results if not isinstance(row.get("provider_failure"), dict)
    )
    row_attributions = [row["failure_attribution"] for row in row_results]
    failed_attributions = [
        attribution
        for row, attribution in zip(row_results, row_attributions, strict=True)
        if not row["strict_evaluation"]["strict_required_actions_valid"]
    ]
    all_failures_actionable = all(
        attribution["primary_attribution"] in ACTIONABLE_ATTRIBUTIONS
        and attribution["primary_attribution"] != "inconclusive"
        for attribution in failed_attributions
    )
    adequate_for_live_evidence_resume = strict_pass_count >= 2
    gate_interpretable = adequate_for_live_evidence_resume or all_failures_actionable
    summary = {
        "schema_version": "hamutay.action_control_surface_gate_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "started_at": started_at,
        "finished_at": finished_at,
        "endpoint": endpoint,
        "output_dir": str(output_dir),
        "row_count": len(row_results),
        "primary_scorable_count": primary_scorable_count,
        "strict_pass_count": strict_pass_count,
        "relaxed_pass_count": relaxed_pass_count,
        "provider_failures": sum(
            1
            for row in row_results
            if isinstance(row.get("provider_failure"), dict)
            and row["provider_failure"].get("layer") == "provider"
        ),
        "protocol_failures": sum(
            1
            for row in row_results
            if isinstance(row.get("provider_failure"), dict)
            and row["provider_failure"].get("layer") == "protocol"
        ),
        "recovery_audit": protocol_recovery_totals(row_results),
        "usage_totals": usage_totals(row_results),
        "row_attributions": row_attributions,
        "row_failure_attributions": failed_attributions,
        "all_failures_actionable": all_failures_actionable,
        "gate_interpretable": gate_interpretable,
        "adequate_for_live_evidence_resume": adequate_for_live_evidence_resume,
        "decision_rule": (
            "adequate_for_live_evidence_resume requires at least two of three "
            "primary strict-valid rows; gate_interpretable also passes if every "
            "failed row has a clear actionable attribution layer."
        ),
        "row_result_paths": [
            str(Path("rows") / str(row["row_id"]) / "row_result.json")
            for row in row_results
        ],
    }
    return summary


def protocol_recovery_totals(row_results: list[JsonDict]) -> JsonDict:
    totals: JsonDict = {
        "protocol_failures": 0,
        "recoverable_protocol_failures": 0,
        "unrecoverable_protocol_failures": 0,
        "strict_pass_if_recovered": 0,
        "relaxed_pass_if_recovered": 0,
        "recovery_methods": {},
    }
    for row in row_results:
        failure = row.get("provider_failure")
        if not (
            isinstance(failure, dict)
            and failure.get("layer") == "protocol"
            and failure.get("code") == "invalid_action_schema"
        ):
            continue
        totals["protocol_failures"] += 1
        recovery = row.get("recovery_evaluation")
        if isinstance(recovery, dict) and recovery.get("recovered"):
            totals["recoverable_protocol_failures"] += 1
            if recovery.get("strict_pass_if_recovered"):
                totals["strict_pass_if_recovered"] += 1
            if recovery.get("relaxed_pass_if_recovered"):
                totals["relaxed_pass_if_recovered"] += 1
            method = str(recovery.get("method") or "unknown")
            methods = totals["recovery_methods"]
            methods[method] = int(methods.get(method, 0)) + 1
        else:
            totals["unrecoverable_protocol_failures"] += 1
    return totals


def usage_totals(row_results: list[JsonDict]) -> JsonDict:
    total_tokens = 0
    estimated_cost = 0.0
    for row in row_results:
        usage = row.get("usage", {})
        if not isinstance(usage, dict):
            continue
        total_tokens += int(
            usage.get("total_tokens")
            or usage.get("total_tokens_count")
            or usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            or 0
        )
        estimated_cost += float(usage.get("cost") or usage.get("estimated_cost") or 0.0)
    return {"total_tokens": total_tokens, "estimated_cost_usd": estimated_cost}


def render_analysis(summary: JsonDict) -> str:
    lines = [
        "# Action/Control Surface Gate Analysis",
        "",
        f"Experiment ID: `{summary['experiment_id']}`",
        "",
        "## Execution",
        "",
        f"- Started: `{summary['started_at']}`",
        f"- Finished: `{summary['finished_at']}`",
        f"- Endpoint: `{summary['endpoint']}`",
        f"- Rows: `{summary['row_count']}`",
        f"- Primary scorable rows: `{summary['primary_scorable_count']}`",
        f"- Primary strict pass count: `{summary['strict_pass_count']}`",
        f"- Relaxed pass count: `{summary['relaxed_pass_count']}`",
        f"- Total tokens: `{summary['usage_totals']['total_tokens']}`",
        f"- Estimated cost USD: `{summary['usage_totals']['estimated_cost_usd']:.6f}`",
        "",
        "## Gate Verdict",
        "",
        f"- Gate interpretable: `{summary['gate_interpretable']}`",
        f"- Adequate for live evidence-resume: `{summary['adequate_for_live_evidence_resume']}`",
        f"- Decision rule: {summary['decision_rule']}",
        "",
        "Interpretation:",
        "",
        interpretation(summary),
        "",
        "## Row Attribution",
        "",
        "| Row | Strict pass | Relaxed pass | Attribution | Rationale |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    output_dir = Path(str(summary["output_dir"]))
    rows = [load_json(output_dir / path) for path in summary["row_result_paths"]]
    for row in rows:
        attribution = row["failure_attribution"]
        lines.append(
            "| "
            f"{row['row_id']} | "
            f"{row['strict_evaluation']['strict_required_actions_valid']} | "
            f"{row['relaxed_evaluation']['relaxed_required_actions_valid']} | "
            f"`{attribution['primary_attribution']}` | "
            f"{attribution['rationale']} |"
        )

    recovery = summary["recovery_audit"]
    lines.extend(
        [
            "",
            "## Secondary Recovery Audit",
            "",
            f"- Protocol failures: `{recovery['protocol_failures']}`",
            f"- Recoverable protocol failures: `{recovery['recoverable_protocol_failures']}`",
            f"- Unrecoverable protocol failures: `{recovery['unrecoverable_protocol_failures']}`",
            f"- Strict pass if recovered: `{recovery['strict_pass_if_recovered']}`",
            f"- Relaxed pass if recovered: `{recovery['relaxed_pass_if_recovered']}`",
            f"- Recovery methods: `{recovery['recovery_methods']}`",
            "",
            "## Artifact Trail",
            "",
            "- `PRE_REGISTRATION.md` preserves the preregistered question, hypothesis, predictions, method, and success rule.",
            "- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the execution frame.",
            "- `results.json` preserves aggregate machine-readable results.",
            "- `rows/<row_id>/provider_request.json` preserves each request.",
            "- `rows/<row_id>/provider_response.json` preserves each response.",
            "- `rows/<row_id>/provider_attempts.json` preserves retry telemetry.",
            "- `rows/<row_id>/action_object.json` preserves parsed primary objects when present.",
            "- `rows/<row_id>/strict_evaluation.json` preserves primary strict scoring.",
            "- `rows/<row_id>/relaxed_evaluation.json` preserves counterfactual relaxed scoring.",
            "- `rows/<row_id>/recovery_evaluation.json` preserves secondary recovery audits when attempted.",
            "- `rows/<row_id>/row_result.json` ties row artifacts together.",
        ]
    )
    return "\n".join(lines)


def interpretation(summary: JsonDict) -> str:
    if summary["adequate_for_live_evidence_resume"]:
        return (
            "The hardened live action/control surface produced at least two "
            "primary strict-valid rows. This is adequate to proceed to the "
            "clean live evidence-resume panel, while continuing to preserve "
            "secondary recovery only as audit evidence."
        )
    if summary["gate_interpretable"]:
        return (
            "The gate did not establish adequacy for live evidence-resume, but "
            "the failures are interpretable. The next step should address the "
            "attributed layer before running Goal 2."
        )
    return (
        "The gate is not adequate and not interpretable enough for Goal 2. "
        "Do not proceed to live evidence-resume until the action surface or "
        "scoring boundary is repaired."
    )


def refresh_analysis(output_dir: Path = ROOT_DIR) -> JsonDict:
    rows_dir = output_dir / "rows"
    if not rows_dir.exists():
        raise FileNotFoundError(rows_dir)
    row_results = []
    for row_path in sorted(rows_dir.glob("*/row_result.json")):
        row = json.loads(row_path.read_text())
        row["failure_attribution"] = classify_action_row_failure(row)
        _write_json(row_path, row)
        row_results.append(row)
    existing = load_json(output_dir / "results.json")
    summary = summarize_results(
        row_results=row_results,
        output_dir=output_dir,
        endpoint=str(existing.get("endpoint") or DEFAULT_ENDPOINT),
        started_at=str(existing.get("started_at") or _now_iso()),
        finished_at=str(existing.get("finished_at") or _now_iso()),
    )
    _write_json(output_dir / "results.json", summary)
    (output_dir / "analysis.md").write_text(render_analysis(summary) + "\n")
    return summary


def load_json(path: Path) -> JsonDict:
    return json.loads(path.read_text())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: JsonDict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-preregistration", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--refresh-analysis", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT_DIR)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    args = parser.parse_args()

    if args.refresh_analysis:
        result = refresh_analysis(args.output_dir)
    elif args.run_live:
        result = execute_live(
            output_dir=args.output_dir,
            api_key=os.environ.get(args.api_key_env, ""),
            endpoint=args.endpoint,
        )
    else:
        result = write_preregistration_artifacts(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
