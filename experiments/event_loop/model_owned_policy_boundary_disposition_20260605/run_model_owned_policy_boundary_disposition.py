"""Live policy-boundary rerun with policy disposition capture enabled."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from hamutay.events import EventStore, summarize_event_log


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/model_owned_policy_boundary_20260605/"
    / "run_model_owned_policy_boundary.py"
)


def load_base_runner():
    spec = importlib.util.spec_from_file_location(
        "model_owned_policy_boundary_base",
        BASE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base runner from {BASE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base_runner = load_base_runner()

MODEL = base_runner.MODEL
N_REPLICATES = base_runner.N_REPLICATES
CONDITIONS = base_runner.CONDITIONS
EXPECTED_ACTION = base_runner.EXPECTED_ACTION
CONDITION = "model_owned_policy_boundary_disposition"

base_runner.EXP_DIR = EXP_DIR
base_runner.PROJECT_ROOT = PROJECT_ROOT
base_runner.RESULTS_PATH = RESULTS_PATH
base_runner.CONDITION = CONDITION
base_runner.gen.EXP_DIR = EXP_DIR
base_runner.gen.PROJECT_ROOT = PROJECT_ROOT
base_runner.sb.EXP_DIR = EXP_DIR
base_runner.sb.PROJECT_ROOT = PROJECT_ROOT
base_runner.base.EXP_DIR = EXP_DIR
base_runner.base.PROJECT_ROOT = PROJECT_ROOT

_step_pending_events = base_runner.step_pending_events


def step_pending_events_with_dispositions(*args, **kwargs):
    kwargs["policy_dispositions"] = True
    return _step_pending_events(*args, **kwargs)


base_runner.step_pending_events = step_pending_events_with_dispositions


def _event_ids_for_label(event_records: list[dict[str, Any]], label: str) -> set[str]:
    return {
        str(record.get("event_id"))
        for record in event_records
        if record.get("label") == label and record.get("event_id")
    }


def _latest_completed(event_records: list[dict[str, Any]], label: str) -> dict[str, Any]:
    ids = _event_ids_for_label(event_records, label)
    completed = [
        record
        for record in event_records
        if record.get("status") == "completed"
        and str(record.get("event_id")) in ids
    ]
    return completed[-1] if completed else {}


def _dispositions_for_source(
    event_records: list[dict[str, Any]],
    source_event_id: str | None,
) -> list[dict[str, Any]]:
    if not source_event_id:
        return []
    return [
        record
        for record in event_records
        if record.get("record_type") == "policy_disposition"
        and record.get("source_event_id") == source_event_id
    ]


_base_finalize_result = base_runner.finalize_result


def finalize_result(
    result: dict[str, Any],
    *,
    log_path: Path,
    event_path: Path,
    condition: str,
    replicate: int,
) -> dict[str, Any]:
    result = _base_finalize_result(
        result,
        log_path=log_path,
        event_path=event_path,
        condition=condition,
        replicate=replicate,
    )
    event_records = EventStore(event_path).read_records()
    summary = summarize_event_log(event_records)
    first_completed = _latest_completed(
        event_records,
        base_runner.first_label(condition, replicate),
    )
    followup_completed = _latest_completed(
        event_records,
        base_runner.followup_label(condition, replicate),
    )
    first_dispositions = _dispositions_for_source(
        event_records,
        first_completed.get("event_id"),
    )
    followup_dispositions = _dispositions_for_source(
        event_records,
        followup_completed.get("event_id"),
    )
    first_disposition = first_dispositions[-1] if first_dispositions else {}
    followup_disposition = (
        followup_dispositions[-1] if followup_dispositions else {}
    )
    expected_first = EXPECTED_ACTION[condition]
    result.update(
        {
            "policy_disposition_summary": {
                "policy_disposition_count": summary.get(
                    "policy_disposition_count"
                ),
                "policy_disposition_counts": summary.get(
                    "policy_disposition_counts"
                ),
                "lifecycle_anomalies": summary.get("lifecycle_anomalies"),
                "status_counts": summary.get("status_counts"),
                "event_count": summary.get("event_count"),
            },
            "first_policy_disposition_count": len(first_dispositions),
            "first_policy_disposition_action": first_disposition.get(
                "policy_action"
            ),
            "first_policy_disposition_classification": first_disposition.get(
                "classification"
            ),
            "first_policy_disposition_matches_action": (
                first_disposition.get("policy_action") == result.get("policy_action")
            ),
            "first_policy_disposition_expected": (
                first_disposition.get("policy_action") == expected_first
            ),
            "first_policy_disposition_continuation_event_id": (
                first_disposition.get("continuation_event_id")
            ),
            "first_policy_disposition_continuation_kind": (
                first_disposition.get("continuation_kind")
            ),
            "first_policy_disposition_missing_evidence": (
                first_disposition.get("missing_evidence") or []
            ),
            "followup_policy_disposition_count": len(followup_dispositions),
            "followup_policy_disposition_action": followup_disposition.get(
                "policy_action"
            ),
        }
    )
    return result


base_runner.finalize_result = finalize_result
_base_aggregate = base_runner.aggregate


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = base_runner.condition_summary(rows)
    summary.update(
        {
            "first_dispositions": sum(
                int(row.get("first_policy_disposition_count") or 0)
                for row in rows
            ),
            "first_disposition_matches_action": sum(
                bool(row.get("first_policy_disposition_matches_action"))
                for row in rows
            ),
            "first_disposition_expected": sum(
                bool(row.get("first_policy_disposition_expected"))
                for row in rows
            ),
            "evidence_missing_preserved": sum(
                bool(row.get("first_policy_disposition_missing_evidence"))
                for row in rows
                if row.get("condition") == "evidence_missing"
            ),
            "followup_dispositions": sum(
                int(row.get("followup_policy_disposition_count") or 0)
                for row in rows
            ),
        }
    )
    return summary


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row["condition"])].append(row)
    base_summary = _base_aggregate(results)
    rows = [row for condition in CONDITIONS for row in grouped.get(condition, [])]
    continue_rows = grouped.get("continue_required", [])
    stop_rows = grouped.get("stop_ready", [])
    evidence_rows = grouped.get("evidence_missing", [])
    base_summary["conditions"] = {
        condition: condition_summary(grouped.get(condition, []))
        for condition in CONDITIONS
    }
    base_summary["disposition_hypothesis_results"] = {
        "H531_live_first_wake_choices_produce_dispositions": bool(rows)
        and all(
            row.get("first_policy_disposition_count") == 1
            and row.get("first_policy_disposition_matches_action")
            for row in rows
        ),
        "H532_continue_disposition_links_to_continuation": bool(continue_rows)
        and all(
            row.get("first_policy_disposition_action") == "continue_after"
            and row.get("first_policy_disposition_continuation_event_id")
            == row.get("step1", {})
            .get("batch", {})
            .get("results", [{}])[0]
            .get("auto_continuation_event", {})
            .get("event_id")
            and row.get("first_policy_disposition_continuation_kind")
            == "policy_boundary_followup"
            and row.get("followup_wake_state_valid")
            for row in continue_rows
        ),
        "H533_non_continuation_dispositions_terminal": (
            bool(stop_rows)
            and bool(evidence_rows)
            and all(
                row.get("first_policy_disposition_classification") == "complete"
                and not row.get("followup_event_appended")
                and row.get("step3_stop_reason") in {"idle", "waiting"}
                for row in stop_rows
            )
            and all(
                row.get("first_policy_disposition_classification")
                == "evidence_blocked"
                and not row.get("followup_event_appended")
                and row.get("step3_stop_reason") in {"idle", "waiting"}
                for row in evidence_rows
            )
        ),
        "H534_evidence_disposition_preserves_missing_evidence": bool(evidence_rows)
        and all(
            bool(row.get("first_policy_disposition_missing_evidence"))
            for row in evidence_rows
        ),
        "H535_lifecycle_summaries_remain_clean": bool(rows)
        and all(
            not (row.get("policy_disposition_summary") or {}).get(
                "lifecycle_anomalies"
            )
            for row in rows
        ),
    }
    return base_summary


base_runner.aggregate = aggregate


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "model_owned_policy_boundary_disposition_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "conditions": CONDITIONS,
        "expected_actions": EXPECTED_ACTION,
        "continue_request_option": base_runner.continuation_option(
            "continue_required",
            0,
        ),
        "first_terminal_surface": base_runner.first_surface(
            "continue_required",
            0,
        ),
        "followup_terminal_surface_template": base_runner.followup_surface(
            "<result_record_id>"
        ),
        "scheduler_flags": {
            "auto_continuations": True,
            "policy_dispositions": True,
        },
        "results": results,
        "summary": aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


base_runner.write_results = write_results


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    base_runner.main()


if __name__ == "__main__":
    main()
