"""Score live scheduled wakes from completed event wake_validation summaries."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

from hamutay.events import EventStore, summarize_event_log

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/scheduled_walk_strict_continuity_20260605/"
    / "run_scheduled_walk_strict_continuity.py"
)


def load_base_runner():
    spec = importlib.util.spec_from_file_location(
        "scheduled_walk_strict_continuity_base",
        BASE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base runner from {BASE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def latest_completed_event_summary(event_path: Path) -> dict:
    summary = summarize_event_log(EventStore(event_path).read_records())
    completed = summary.get("completed") or []
    if not completed:
        return {}
    return completed[0]


def add_event_log_scores(result: dict, base) -> dict:
    scored = dict(result)
    event_path = PROJECT_ROOT / scored["event_log_path"]
    event_summary = latest_completed_event_summary(event_path)
    scored["event_log_scoring"] = {
        "has_completed_event_summary": bool(event_summary),
        "wake_validation_status": event_summary.get("wake_validation_status"),
        "wake_first_pass_status": event_summary.get("wake_first_pass_status"),
        "wake_repair_attempted": event_summary.get("wake_repair_attempted"),
        "wake_repair_status": event_summary.get("wake_repair_status"),
        "wake_repaired": event_summary.get("wake_repaired"),
        "wake_repair_ignored_protected_attempt_count": event_summary.get(
            "wake_repair_ignored_protected_attempt_count"
        ),
        "context_error_count": event_summary.get("context_error_count"),
        "response_state_mismatch": event_summary.get("response_state_mismatch"),
        "outcome_warning_count": event_summary.get("outcome_warning_count"),
    }
    session_status = scored.get("state_validation_status")
    event_status = scored["event_log_scoring"]["wake_validation_status"]
    scored["event_log_scoring"]["session_event_validation_status_agree"] = (
        bool(event_status) and event_status == session_status
    )
    scored["event_log_scoring"]["event_classified_without_session_validation"] = (
        bool(event_status)
        and scored["event_log_scoring"]["wake_first_pass_status"] is not None
        and (
            scored["event_log_scoring"]["wake_repair_attempted"] is False
            or scored["event_log_scoring"]["wake_repair_status"] is not None
        )
    )
    scored["event_log_scoring"]["expected_model"] = base.MODEL
    return scored


def summarize_event_log_scores(results: list[dict]) -> dict:
    completed = [r for r in results if r.get("event_completed")]
    scores = [r.get("event_log_scoring") or {} for r in completed]

    def count(key: str, value) -> int:
        return sum(score.get(key) == value for score in scores)

    status_counts: dict[str, int] = {}
    first_pass_counts: dict[str, int] = {}
    repair_counts: dict[str, int] = {}
    for score in scores:
        status = score.get("wake_validation_status")
        if status is not None:
            status_counts[str(status)] = status_counts.get(str(status), 0) + 1
        first_pass = score.get("wake_first_pass_status")
        if first_pass is not None:
            first_pass_counts[str(first_pass)] = (
                first_pass_counts.get(str(first_pass), 0) + 1
            )
        repair = score.get("wake_repair_status")
        if repair is not None:
            repair_counts[str(repair)] = repair_counts.get(str(repair), 0) + 1
    return {
        "completed_count": len(completed),
        "event_wake_validation_present": sum(
            bool(score.get("wake_validation_status")) for score in scores
        ),
        "event_classified_without_session_validation": sum(
            bool(score.get("event_classified_without_session_validation"))
            for score in scores
        ),
        "session_event_validation_agreement": sum(
            bool(score.get("session_event_validation_status_agree"))
            for score in scores
        ),
        "wake_validation_status_counts": dict(sorted(status_counts.items())),
        "wake_first_pass_status_counts": dict(sorted(first_pass_counts.items())),
        "wake_repair_status_counts": dict(sorted(repair_counts.items())),
        "wake_repaired": count("wake_repaired", True),
        "wake_repair_attempted": count("wake_repair_attempted", True),
        "context_error_total": sum(
            int(score.get("context_error_count") or 0) for score in scores
        ),
    }


def aggregate(results: list[dict], base) -> dict:
    base_aggregate = base.aggregate(results)
    event_scores = summarize_event_log_scores(results)
    completed = [r for r in results if r.get("event_completed")]
    valid_initializations = [r for r in results if r.get("init_valid")]
    return {
        "base_summary": base_aggregate["summary"],
        "event_log_summary": event_scores,
        "hypothesis_results": {
            "H221_scheduled_walk_gate_completes": bool(completed),
            "H222_completed_validated_events_have_wake_validation": (
                all(
                    bool((r.get("event_log_scoring") or {}).get(
                        "wake_validation_status"
                    ))
                    for r in completed
                ) if completed else False
            ),
            "H223_event_status_matches_session_status": (
                all(
                    bool((r.get("event_log_scoring") or {}).get(
                        "session_event_validation_status_agree"
                    ))
                    for r in completed
                ) if completed else False
            ),
            "H224_event_summary_classifies_first_pass_and_repair": (
                all(
                    bool((r.get("event_log_scoring") or {}).get(
                        "event_classified_without_session_validation"
                    ))
                    for r in completed
                ) if completed else False
            ),
            "H225_context_and_bounded_repair_diagnostics_preserved": (
                all(
                    r.get("context_error_count") == 0
                    and r.get("event_context_has_walk_path")
                    and r.get("bounded_wake_calls")
                    for r in completed
                ) if completed else False
            ),
            "diagnostic_any_valid_initialization": bool(valid_initializations),
        },
        "base_hypothesis_results": base_aggregate["hypothesis_results"],
    }


def write_results(results: list[dict], base) -> None:
    payload = {
        "model": base.MODEL,
        "n_replicates": base.N_REPLICATES,
        "max_tokens": base.MAX_TOKENS,
        "call_timeout_seconds": base.CALL_TIMEOUT_SECONDS,
        "http_timeout_seconds": base.HTTP_TIMEOUT_SECONDS,
        "expected_wake_cycle": base.EXPECTED_WAKE_CYCLE,
        "results": results,
        "summary": aggregate(results, base),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    base = load_base_runner()
    base.EXP_DIR = EXP_DIR
    base.PROJECT_ROOT = PROJECT_ROOT
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")

    results_path = EXP_DIR / "results.json"
    results: list[dict] = []
    if results_path.exists():
        payload = json.loads(results_path.read_text())
        prior = payload.get("results", [])
        if isinstance(prior, list):
            results = prior

    completed = {
        (result.get("model"), int(result.get("replicate", 0)))
        for result in results
    }
    for replicate in range(base.N_REPLICATES):
        key = (base.MODEL, replicate + 1)
        if key in completed:
            print(f"{base.MODEL} r{replicate + 1} already recorded", flush=True)
            continue
        print(f"{base.MODEL} r{replicate + 1}", flush=True)
        result = base.run_replicate(base.MODEL, replicate, api_key)
        results.append(add_event_log_scores(result, base))
        completed.add(key)
        write_results(results, base)

    print(json.dumps(aggregate(results, base), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
