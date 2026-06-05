"""Step 7 replication-boundary panel for bounded autonomous work."""

from __future__ import annotations

import importlib.util
import json
import multiprocessing as mp
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
STEP6_DIR = PROJECT_ROOT / "experiments/event_loop/bounded_autonomous_work_evidence_stressors_20260605"
STEP6_RUNNER_PATH = STEP6_DIR / "run_bounded_autonomous_work_evidence_stressors.py"
STEP6_RESULTS_PATH = STEP6_DIR / "results.json"

CONDITION = "bounded_autonomous_work_replication_boundary"
BASE_URL = "https://openrouter.ai/api/v1"
MODELS = ["moonshotai/kimi-k2.6", "openai/gpt-4.1-mini"]
STRESSORS = ["partial_evidence", "conflicting_evidence", "multiple_open_requests"]
ROW_TIMEOUT_SECONDS = 240


def load_step6_runner():
    spec = importlib.util.spec_from_file_location("step6_evidence_stressors", STEP6_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Step 6 runner from {STEP6_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


step6 = load_step6_runner()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def configure_step6_for_step7(model: str) -> None:
    step6.EXP_DIR = EXP_DIR
    step6.PROJECT_ROOT = PROJECT_ROOT
    step6.RESULTS_PATH = RESULTS_PATH
    step6.MODEL = model
    step6.BASE_URL = BASE_URL
    step6.CONDITION = CONDITION
    step6.STRESSORS = STRESSORS


def classify_row(row: dict[str, Any]) -> str:
    score = row.get("score") or {}
    error = row.get("error")
    if error:
        message = str(error.get("message", "")).lower() if isinstance(error, dict) else str(error).lower()
        if "tool" in message or "structured" in message or "schema" in message:
            return "protocol_limitation"
        if "api" in message or "provider" in message or "rate" in message or "timeout" in message:
            return "provider_failure"
        return "provider_failure"
    if not score.get("scoreable"):
        return "substrate_failure"
    evidence_use = score.get("evidence_use")
    if evidence_use in {
        "partial_evidence_overclaimed",
        "evidence_conflict_collapsed",
        "multiple_requests_overclaimed",
    }:
        return "model_boundary"
    if score.get("positive_stressor_result"):
        return "replicated_capability"
    if score.get("policy_action_status") in {"invalid", "missing"}:
        return "protocol_limitation"
    return "model_boundary"


def normalize_step7_score(row: dict[str, Any]) -> dict[str, Any]:
    score = row.get("score")
    if isinstance(score, dict) and (row.get("error") or not score.get("scoreable")):
        score["positive_stressor_result"] = False
    return row


def run_model_stressor(model: str, stressor: str, api_key: str) -> dict[str, Any]:
    configure_step6_for_step7(model)
    row = step6.run_stressor(stressor, api_key)
    row["replication_model"] = model
    row["replication_stressor"] = stressor
    row = normalize_step7_score(row)
    row["decision_classification"] = classify_row(row)
    return row


def expected_paths(model: str, stressor: str) -> tuple[Path, Path]:
    safe = step6.safe_model_name(model)
    log_path = EXP_DIR / f"{safe}_{CONDITION}_{stressor}.jsonl"
    return log_path, step6.default_event_log_path(log_path)


def timeout_row(model: str, stressor: str, seconds: int) -> dict[str, Any]:
    configure_step6_for_step7(model)
    log_path, event_path = expected_paths(model, stressor)
    records = step6.load_records(log_path)
    event_records = step6.load_records(event_path)
    row: dict[str, Any] = {
        "condition": CONDITION,
        "stressor": stressor,
        "replication_model": model,
        "replication_stressor": stressor,
        "model": model,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "error": {
            "type": "TimeoutError",
            "message": f"row exceeded {seconds}s timeout; partial trace preserved",
        },
        "evidence_result": {},
        "event_summary": step6.summarize_event_log(event_records, now=step6.FINAL_NOW),
        "score": step6.score_row(
            stressor=stressor,
            records=records,
            event_records=event_records,
            evidence_result={},
        ),
    }
    row["decision_classification"] = classify_row(row)
    return normalize_step7_score(row)


def row_worker(queue: mp.Queue, model: str, stressor: str, api_key: str) -> None:
    try:
        queue.put({"ok": True, "row": run_model_stressor(model, stressor, api_key)})
    except Exception as exc:  # noqa: BLE001 -- live boundary failures are data
        configure_step6_for_step7(model)
        log_path, event_path = expected_paths(model, stressor)
        records = step6.load_records(log_path)
        event_records = step6.load_records(event_path)
        row = {
            "condition": CONDITION,
            "stressor": stressor,
            "replication_model": model,
            "replication_stressor": stressor,
            "model": model,
            "log_path": str(log_path.relative_to(PROJECT_ROOT)),
            "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "evidence_result": {},
            "event_summary": step6.summarize_event_log(event_records, now=step6.FINAL_NOW),
            "score": step6.score_row(
                stressor=stressor,
                records=records,
                event_records=event_records,
                evidence_result={},
            ),
        }
        row["decision_classification"] = classify_row(row)
        queue.put({"ok": False, "row": normalize_step7_score(row)})


def run_model_stressor_with_timeout(model: str, stressor: str, api_key: str) -> dict[str, Any]:
    queue: mp.Queue = mp.Queue()
    proc = mp.Process(target=row_worker, args=(queue, model, stressor, api_key))
    proc.start()
    proc.join(ROW_TIMEOUT_SECONDS)
    if proc.is_alive():
        proc.terminate()
        proc.join(10)
        if proc.is_alive():
            proc.kill()
            proc.join()
        return timeout_row(model, stressor, ROW_TIMEOUT_SECONDS)
    if not queue.empty():
        return queue.get()["row"]
    row = timeout_row(model, stressor, ROW_TIMEOUT_SECONDS)
    row["error"] = {
        "type": "WorkerExitError",
        "message": f"row worker exited with code {proc.exitcode} without returning a row",
    }
    row["decision_classification"] = classify_row(row)
    return row


def rescore_row(row: dict[str, Any]) -> dict[str, Any]:
    model = row.get("replication_model") or row.get("model")
    configure_step6_for_step7(model)
    scored_row = dict(row)
    log_path = PROJECT_ROOT / row["log_path"]
    event_path = PROJECT_ROOT / row["event_log_path"]
    records = step6.load_records(log_path)
    event_records = step6.load_records(event_path)
    scored_row["event_summary"] = step6.summarize_event_log(event_records, now=step6.FINAL_NOW)
    scored_row["score"] = step6.score_row(
        stressor=row["stressor"],
        records=records,
        event_records=event_records,
        evidence_result=row.get("evidence_result") or {},
    )
    scored_row["decision_classification"] = classify_row(scored_row)
    scored_row["rescored_from_existing_trace"] = True
    return normalize_step7_score(scored_row)


def model_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_model[row.get("replication_model") or row.get("model")].append(row)
    summary: dict[str, Any] = {}
    for model, model_rows in sorted(by_model.items()):
        classifications = Counter(row.get("decision_classification") for row in model_rows)
        positives = sum(1 for row in model_rows if row.get("decision_classification") == "replicated_capability")
        summary[model] = {
            "rows": len(model_rows),
            "positive_stressor_results": positives,
            "classifications": dict(classifications),
            "replicated_all_stressors": positives == len(STRESSORS)
            and classifications.get("replicated_capability") == len(STRESSORS),
        }
    return summary


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [row.get("score", {}) for row in rows]
    classifications = Counter(row.get("decision_classification") for row in rows)
    return {
        "rows": len(rows),
        "errors": sum(1 for row in rows if row.get("error")),
        "scoreable": sum(1 for score in scores if score.get("scoreable")),
        "positive_stressor_results": sum(
            1 for row in rows if row.get("decision_classification") == "replicated_capability"
        ),
        "decision_classifications": dict(classifications),
        "artifact_status_counts": dict(Counter(score.get("artifact_status") for score in scores)),
        "policy_action_counts": dict(Counter(score.get("policy_action") for score in scores)),
        "evidence_use_counts": dict(Counter(score.get("evidence_use") for score in scores)),
        "model_summary": model_summary(rows),
    }


def hypothesis_outcomes(rows: list[dict[str, Any]]) -> dict[str, str]:
    models = model_summary(rows)
    any_full_replication = any(summary.get("replicated_all_stressors") for summary in models.values())
    interpretable = all(row.get("decision_classification") for row in rows)
    bad_positive = [
        row
        for row in rows
        if row.get("decision_classification") == "replicated_capability"
        and row.get("score", {}).get("evidence_use")
        in {
            "partial_evidence_overclaimed",
            "evidence_conflict_collapsed",
            "multiple_requests_overclaimed",
        }
    ]
    protocol_separated = all(
        not row.get("error") or row.get("decision_classification") in {"protocol_limitation", "provider_failure"}
        for row in rows
    )
    return {
        "H1101_at_least_one_non_deepseek_model_replicates_step6": (
            "survived" if any_full_replication else "falsified"
        ),
        "H1102_all_produced_rows_are_interpretable": "survived" if interpretable else "falsified",
        "H1103_unsupported_completion_not_counted_as_replication": (
            "survived" if not bad_positive else "falsified"
        ),
        "H1104_protocol_failure_separated_from_model_boundary_failure": (
            "survived" if protocol_separated else "falsified"
        ),
    }


def build_payload(rows: list[dict[str, Any]], *, mode: str) -> dict[str, Any]:
    return {
        "condition": CONDITION,
        "mode": mode,
        "models": MODELS,
        "stressors": STRESSORS,
        "prior_positive_anchor": str(STEP6_RESULTS_PATH.relative_to(PROJECT_ROOT)),
        "prior_anchor_hypothesis_results": load_json(STEP6_RESULTS_PATH).get("hypothesis_results", {}),
        "summary": summarize(rows),
        "hypothesis_outcomes": hypothesis_outcomes(rows),
        "results": rows,
    }


def run_live() -> dict[str, Any]:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    rows = []
    for model in MODELS:
        for stressor in STRESSORS:
            rows.append(run_model_stressor_with_timeout(model, stressor, api_key))
    return build_payload(rows, mode="live")


def rescore_existing() -> dict[str, Any]:
    existing = load_json(RESULTS_PATH)
    rows = [rescore_row(row) for row in existing.get("results", [])]
    return build_payload(rows, mode="rescore")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--rescore":
        payload = rescore_existing()
    else:
        payload = run_live()
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["hypothesis_outcomes"], indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
