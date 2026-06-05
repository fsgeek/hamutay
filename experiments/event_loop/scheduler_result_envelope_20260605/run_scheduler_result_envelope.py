"""Build scheduler result envelopes over existing event-loop artifacts."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scheduler_result_envelope import normalize_row


ROOT = Path(__file__).resolve().parents[3]
EVENT_LOOP_DIR = ROOT / "experiments" / "event_loop"
EXP_DIR = Path(__file__).resolve().parent
OUT_PATH = EXP_DIR / "envelopes.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def result_rows(data: Any) -> tuple[list[Any] | None, str]:
    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, list):
            return results, "dict.results"
        return None, f"dict.{type(results).__name__}"
    if isinstance(data, list):
        return data, "list"
    return None, type(data).__name__


def aggregate(envelopes: list[dict[str, Any]], files: list[dict[str, Any]]) -> dict[str, Any]:
    scheduler = [env for env in envelopes if env["scheduler"]["relevant"]]
    eligible = [
        env
        for env in scheduler
        if env["initialization"]["scheduler_score_eligible"]
    ]
    init_counts = Counter(env["initialization"]["class"] for env in envelopes)
    scheduler_init_counts = Counter(env["initialization"]["class"] for env in scheduler)
    eligibility_counts = Counter(
        str(env["initialization"]["scheduler_score_eligible"]).lower()
        for env in scheduler
    )
    wake_source_counts = Counter(env["wake"]["source"] for env in scheduler)

    by_experiment: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for env in envelopes:
        by_experiment[env["source"]["experiment"]].append(env)

    experiment_summaries: dict[str, dict[str, Any]] = {}
    for experiment, group in sorted(by_experiment.items()):
        exp_scheduler = [env for env in group if env["scheduler"]["relevant"]]
        exp_eligible = [
            env
            for env in exp_scheduler
            if env["initialization"]["scheduler_score_eligible"]
        ]
        exp_init_counts = Counter(env["initialization"]["class"] for env in group)
        missing_wake = [
            env
            for env in exp_scheduler
            if env["wake"]["source"] == "absent"
        ]
        unclassifiable = [
            env
            for env in exp_scheduler
            if env["initialization"]["class"] == "unclassifiable"
        ]
        legacy = [
            env
            for env in exp_scheduler
            if env["initialization"]["class"] == "valid_legacy"
        ]
        completed_all = sum(env["scheduler"]["event_completed"] for env in exp_scheduler)
        completed_eligible = sum(
            env["scheduler"]["event_completed"] for env in exp_eligible
        )
        experiment_summaries[experiment] = {
            "row_count": len(group),
            "scheduler_relevant_count": len(exp_scheduler),
            "eligible_count": len(exp_eligible),
            "class_counts": dict(sorted(exp_init_counts.items())),
            "missing_wake_validation_count": len(missing_wake),
            "unclassifiable_initialization_count": len(unclassifiable),
            "valid_legacy_count": len(legacy),
            "all_attempt_event_completed_count": completed_all,
            "eligible_event_completed_count": completed_eligible,
            "all_attempt_event_completion_rate": (
                completed_all / len(exp_scheduler) if exp_scheduler else None
            ),
            "eligible_event_completion_rate": (
                completed_eligible / len(exp_eligible) if exp_eligible else None
            ),
            "needs_schema_update": bool(missing_wake or unclassifiable or legacy),
            "schema_update_reasons": sorted(
                {
                    reason
                    for reason, condition in [
                        ("missing_wake_validation", bool(missing_wake)),
                        ("unclassifiable_initialization", bool(unclassifiable)),
                        ("legacy_initialization", bool(legacy)),
                    ]
                    if condition
                }
            ),
        }

    aggregate_files = [
        file_record
        for file_record in files
        if file_record.get("class") == "malformed_or_aggregate"
    ]
    schema_update_experiments = {
        experiment: summary
        for experiment, summary in experiment_summaries.items()
        if summary["scheduler_relevant_count"] and summary["needs_schema_update"]
    }

    return {
        "envelope_count": len(envelopes),
        "file_count": len(files),
        "scheduler_relevant_count": len(scheduler),
        "scheduler_score_eligible_count": len(eligible),
        "initialization_class_counts": dict(sorted(init_counts.items())),
        "scheduler_initialization_class_counts": dict(
            sorted(scheduler_init_counts.items())
        ),
        "scheduler_eligibility_counts": dict(sorted(eligibility_counts.items())),
        "wake_source_counts": dict(sorted(wake_source_counts.items())),
        "aggregate_or_malformed_files": aggregate_files,
        "schema_update_experiment_count": len(schema_update_experiments),
        "schema_update_experiments": schema_update_experiments,
        "experiments": experiment_summaries,
    }


def build() -> dict[str, Any]:
    envelopes: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []

    for path in sorted(EVENT_LOOP_DIR.glob("*/results.json")):
        rel_path = path.relative_to(ROOT).as_posix()
        experiment = path.parent.name
        try:
            data = load_json(path)
        except Exception as exc:  # pragma: no cover - defensive audit path
            files.append(
                {
                    "experiment": experiment,
                    "results_path": rel_path,
                    "root_shape": "unreadable",
                    "class": "malformed_or_aggregate",
                    "error": str(exc),
                }
            )
            continue

        rows, root_shape = result_rows(data)
        if rows is None:
            files.append(
                {
                    "experiment": experiment,
                    "results_path": rel_path,
                    "root_shape": root_shape,
                    "class": "malformed_or_aggregate",
                    "error": "missing row-level results list",
                }
            )
            continue

        files.append(
            {
                "experiment": experiment,
                "results_path": rel_path,
                "root_shape": root_shape,
                "row_count": len(rows),
            }
        )

        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                files.append(
                    {
                        "experiment": experiment,
                        "results_path": rel_path,
                        "root_shape": root_shape,
                        "class": "malformed_or_aggregate",
                        "error": f"non-dict row {index}",
                    }
                )
                continue
            envelopes.append(
                normalize_row(
                    experiment=experiment,
                    result_index=index,
                    results_path=rel_path,
                    row=row,
                )
            )

    summary = aggregate(envelopes, files)
    return {
        "experiment": "scheduler_result_envelope_20260605",
        "generated_from": "experiments/event_loop/*/results.json",
        "summary": summary,
        "files": files,
        "envelopes": envelopes,
    }


def main() -> None:
    payload = build()
    with OUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
