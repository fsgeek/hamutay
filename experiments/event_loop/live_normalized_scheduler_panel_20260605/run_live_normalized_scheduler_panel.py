"""Live normalized scheduler panel with prospective result envelopes."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
ENVELOPE_DIR = PROJECT_ROOT / "experiments/event_loop/scheduler_result_envelope_20260605"
sys.path.insert(0, str(ENVELOPE_DIR))

from scheduler_result_envelope import normalize_row  # noqa: E402


BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/scheduled_walk_strict_continuity_20260605/"
    / "run_scheduled_walk_strict_continuity.py"
)
FIRST_PASS_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/init_repair_scheduler_gate_20260605/"
    / "run_init_repair_scheduler_gate.py"
)
REPAIRED_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/repaired_init_scheduler_integration_20260605/"
    / "run_repaired_init_scheduler_integration.py"
)
FAILED_SENTINEL_RESULTS = (
    PROJECT_ROOT
    / "experiments/event_loop/live_event_wake_validation_scoring_20260605/"
    / "results.json"
)

N_LIVE_REPLICATES = 2


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_module(module) -> None:
    module.EXP_DIR = EXP_DIR
    module.PROJECT_ROOT = PROJECT_ROOT


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def failed_sentinel_raw_result() -> dict[str, Any]:
    payload = load_json(FAILED_SENTINEL_RESULTS)
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise RuntimeError("failed sentinel source has no results list")
    for row in rows:
        if isinstance(row, dict) and row.get("init_valid") is False:
            return dict(row)
    raise RuntimeError("failed sentinel source has no failed initialization row")


def envelope_for(
    *,
    condition: str,
    result_index: int,
    raw_result: dict[str, Any],
) -> dict[str, Any]:
    return normalize_row(
        experiment=EXP_DIR.name,
        result_index=result_index,
        results_path=str((RESULTS_PATH).relative_to(PROJECT_ROOT)),
        row=raw_result,
    )


def wrap_result(
    *,
    condition: str,
    replicate: int,
    raw_result: dict[str, Any],
    expected_class: str,
    expected_eligible: bool,
    result_index: int,
) -> dict[str, Any]:
    envelope = envelope_for(
        condition=condition,
        result_index=result_index,
        raw_result=raw_result,
    )
    actual_class = envelope["initialization"]["class"]
    actual_eligible = envelope["initialization"]["scheduler_score_eligible"]
    return {
        "condition": condition,
        "replicate": replicate,
        "expected_class": expected_class,
        "expected_eligible": expected_eligible,
        "actual_class": actual_class,
        "actual_eligible": actual_eligible,
        "class_matches_expected": actual_class == expected_class,
        "eligibility_matches_expected": actual_eligible is expected_eligible,
        "raw_result": raw_result,
        "result_envelope": envelope,
    }


def completed_keys(results: list[dict[str, Any]]) -> set[tuple[str, int]]:
    return {
        (str(result.get("condition")), int(result.get("replicate", 0)))
        for result in results
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "live_normalized_scheduler_panel_20260605",
        "model": "deepseek/deepseek-v4-pro",
        "n_live_replicates_per_eligible_condition": N_LIVE_REPLICATES,
        "results": results,
        "summary": aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def condition_summary(group: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in group if row["actual_eligible"]]
    completed = [
        row for row in eligible if row["result_envelope"]["scheduler"]["event_completed"]
    ]
    wake_sources = Counter(row["result_envelope"]["wake"]["source"] for row in group)
    wake_status = Counter(
        str(row["result_envelope"]["wake"]["validation_status"])
        for row in group
        if row["result_envelope"]["wake"]["validation_status"] is not None
    )
    return {
        "n": len(group),
        "eligible": len(eligible),
        "class_counts": dict(
            sorted(Counter(row["actual_class"] for row in group).items())
        ),
        "event_completed": len(completed),
        "wake_sources": dict(sorted(wake_sources.items())),
        "wake_status_counts": dict(sorted(wake_status.items())),
        "bounded_init_call_violations": sum(
            row["raw_result"].get("bounded_init_calls") is False
            or row["raw_result"].get("bounded_init_repair_calls") is False
            for row in group
        ),
        "bounded_wake_call_violations": sum(
            not bool(row["raw_result"].get("bounded_wake_calls", True))
            for row in group
        ),
        "class_mismatches": sum(
            not bool(row["class_matches_expected"]) for row in group
        ),
        "eligibility_mismatches": sum(
            not bool(row["eligibility_matches_expected"]) for row in group
        ),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        by_condition[str(result["condition"])].append(result)

    summaries = {
        condition: condition_summary(group)
        for condition, group in sorted(by_condition.items())
    }
    eligible_conditions = {
        key: value
        for key, value in summaries.items()
        if key in {"first_pass_valid", "repaired_valid"}
    }
    first_pass = summaries.get("first_pass_valid", {})
    repaired = summaries.get("repaired_valid", {})
    failed = summaries.get("failed_culled", {})

    first_pass_completed = int(first_pass.get("event_completed") or 0)
    repaired_completed = int(repaired.get("event_completed") or 0)
    first_pass_wake_present = bool((first_pass.get("wake_status_counts") or {}))
    repaired_wake_present = bool((repaired.get("wake_status_counts") or {}))

    return {
        "n": len(results),
        "conditions": summaries,
        "initialization_class_counts": dict(
            sorted(Counter(row["actual_class"] for row in results).items())
        ),
        "scheduler_eligible_count": sum(bool(row["actual_eligible"]) for row in results),
        "hypothesis_results": {
            "H256_rows_have_raw_and_envelope": all(
                isinstance(row.get("raw_result"), dict)
                and isinstance(row.get("result_envelope"), dict)
                for row in results
            ),
            "H257_eligible_conditions_scheduler_score_eligible": all(
                summary.get("eligible") == summary.get("n")
                for summary in eligible_conditions.values()
            ) if eligible_conditions else False,
            "H258_failed_sentinel_ineligible": (
                failed.get("eligible") == 0 if failed else False
            ),
            "H259_repaired_matches_first_pass_qualitatively": (
                first_pass_completed > 0
                and repaired_completed > 0
                and first_pass_wake_present
                and repaired_wake_present
            ),
            "H260_init_and_wake_provenance_distinct": all(
                row["result_envelope"]["initialization"]["class"]
                in {"first_pass_valid", "repaired_valid"}
                and row["result_envelope"]["wake"]["source"]
                in {"event_log_scoring", "session_state_validation"}
                for row in results
                if row["actual_eligible"]
                and row["result_envelope"]["scheduler"]["event_completed"]
            ),
        },
    }


def next_result_index(results: list[dict[str, Any]]) -> int:
    return len(results) + 1


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")

    base = load_module("scheduled_walk_strict_continuity_base", BASE_RUNNER_PATH)
    first_pass_runner = load_module("first_pass_runner", FIRST_PASS_RUNNER_PATH)
    repaired_runner = load_module("repaired_runner", REPAIRED_RUNNER_PATH)
    configure_module(base)
    configure_module(first_pass_runner)
    configure_module(repaired_runner)

    results: list[dict[str, Any]] = []
    if RESULTS_PATH.exists():
        prior = load_json(RESULTS_PATH).get("results", [])
        if isinstance(prior, list):
            results = prior
    done = completed_keys(results)

    if ("failed_culled", 1) not in done:
        raw = failed_sentinel_raw_result()
        results.append(
            wrap_result(
                condition="failed_culled",
                replicate=1,
                raw_result=raw,
                expected_class="failed_or_culled",
                expected_eligible=False,
                result_index=next_result_index(results),
            )
        )
        done.add(("failed_culled", 1))
        write_results(results)

    for replicate in range(N_LIVE_REPLICATES):
        key = ("first_pass_valid", replicate + 1)
        if key in done:
            print(f"{key[0]} r{key[1]} already recorded", flush=True)
            continue
        print(f"{key[0]} r{key[1]}", flush=True)
        raw = first_pass_runner.run_replicate(base, replicate, api_key)
        results.append(
            wrap_result(
                condition="first_pass_valid",
                replicate=replicate + 1,
                raw_result=raw,
                expected_class="first_pass_valid",
                expected_eligible=True,
                result_index=next_result_index(results),
            )
        )
        done.add(key)
        write_results(results)

    for replicate in range(N_LIVE_REPLICATES):
        key = ("repaired_valid", replicate + 1)
        if key in done:
            print(f"{key[0]} r{key[1]} already recorded", flush=True)
            continue
        print(f"{key[0]} r{key[1]}", flush=True)
        raw = repaired_runner.run_replicate(base, replicate, api_key)
        results.append(
            wrap_result(
                condition="repaired_valid",
                replicate=replicate + 1,
                raw_result=raw,
                expected_class="repaired_valid",
                expected_eligible=True,
                result_index=next_result_index(results),
            )
        )
        done.add(key)
        write_results(results)

    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
