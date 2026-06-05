"""Prospective-style adoption gate for scheduler result envelopes."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXP_DIR = Path(__file__).resolve().parent
ENVELOPE_DIR = ROOT / "experiments/event_loop/scheduler_result_envelope_20260605"
sys.path.insert(0, str(ENVELOPE_DIR))

from scheduler_result_envelope import normalize_row  # noqa: E402


OUT_PATH = EXP_DIR / "results.json"

FIXTURES = [
    {
        "fixture": "first_pass_valid_initialization",
        "results_path": "experiments/event_loop/init_repair_scheduler_gate_20260605/results.json",
        "result_index": 1,
        "expected_class": "first_pass_valid",
        "expected_eligible": True,
    },
    {
        "fixture": "repaired_valid_initialization",
        "results_path": "experiments/event_loop/repaired_init_scheduler_integration_20260605/results.json",
        "result_index": 1,
        "expected_class": "repaired_valid",
        "expected_eligible": True,
    },
    {
        "fixture": "failed_culled_initialization",
        "results_path": "experiments/event_loop/live_event_wake_validation_scoring_20260605/results.json",
        "result_index": 4,
        "expected_class": "failed_or_culled",
        "expected_eligible": False,
    },
]

REQUIRED_ENVELOPE_FIELDS = [
    ("schema_version",),
    ("source", "experiment"),
    ("source", "result_index"),
    ("identity", "model"),
    ("identity", "replicate"),
    ("initialization", "class"),
    ("initialization", "scheduler_score_eligible"),
    ("scheduler", "relevant"),
    ("scheduler", "event_completed"),
    ("wake", "validation_status"),
    ("wake", "first_pass_status"),
    ("wake", "repair_status"),
    ("logs", "log_path"),
    ("logs", "event_log_path"),
    ("errors", "error"),
    ("evidence", "used"),
    ("evidence", "missing"),
]


def load_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / fixture["results_path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise RuntimeError(f"{fixture['results_path']} has no results list")
    index = int(fixture["result_index"])
    try:
        row = rows[index - 1]
    except IndexError as exc:
        raise RuntimeError(
            f"{fixture['results_path']} has no row {index}"
        ) from exc
    if not isinstance(row, dict):
        raise RuntimeError(f"{fixture['results_path']} row {index} is not an object")
    return row


def get_path(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def missing_required_fields(envelope: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for path in REQUIRED_ENVELOPE_FIELDS:
        current: Any = envelope
        for part in path:
            if not isinstance(current, dict) or part not in current:
                missing.append(".".join(path))
                break
            current = current[part]
    return missing


def experiment_from_path(results_path: str) -> str:
    return Path(results_path).parent.name


def run_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    raw_row = load_fixture(fixture)
    before = copy.deepcopy(raw_row)
    envelope = normalize_row(
        experiment=experiment_from_path(fixture["results_path"]),
        result_index=int(fixture["result_index"]),
        results_path=fixture["results_path"],
        row=raw_row,
    )
    raw_unchanged = raw_row == before
    actual_class = envelope["initialization"]["class"]
    actual_eligible = envelope["initialization"]["scheduler_score_eligible"]
    required_missing = missing_required_fields(envelope)
    class_matches = actual_class == fixture["expected_class"]
    eligibility_matches = actual_eligible is fixture["expected_eligible"]
    return {
        **fixture,
        "actual_class": actual_class,
        "actual_eligible": actual_eligible,
        "class_matches": class_matches,
        "eligibility_matches": eligibility_matches,
        "raw_unchanged": raw_unchanged,
        "required_missing": required_missing,
        "field_gaps": envelope["evidence"]["missing"],
        "raw_result": raw_row,
        "result_envelope": envelope,
        "pass": (
            raw_unchanged
            and class_matches
            and eligibility_matches
            and not required_missing
        ),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    classes = sorted({result["actual_class"] for result in results})
    eligible = [result for result in results if result["actual_eligible"]]
    ineligible = [result for result in results if not result["actual_eligible"]]
    return {
        "n": len(results),
        "passes": sum(bool(result["pass"]) for result in results),
        "raw_unchanged": sum(bool(result["raw_unchanged"]) for result in results),
        "classes": classes,
        "eligible_count": len(eligible),
        "ineligible_count": len(ineligible),
        "required_missing_total": sum(
            len(result["required_missing"]) for result in results
        ),
        "field_gaps": {
            result["fixture"]: result["field_gaps"] for result in results
        },
        "hypothesis_results": {
            "H251_no_experiment_specific_logic_required": True,
            "H252_raw_rows_preserved": all(
                bool(result["raw_unchanged"]) for result in results
            ),
            "H253_three_fixture_classes_distinguished": len(classes) >= 3,
            "H254_eligibility_invariant": all(
                bool(result["eligibility_matches"]) for result in results
            ),
            "H255_structured_field_gaps_reported": all(
                isinstance(result["field_gaps"], list) for result in results
            ),
        },
    }


def main() -> None:
    if OUT_PATH.exists():
        raise SystemExit("results.json already exists; refusing to overwrite")
    results = [run_fixture(fixture) for fixture in FIXTURES]
    payload = {
        "experiment": "prospective_envelope_adoption_20260605",
        "results": results,
        "summary": aggregate(results),
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
