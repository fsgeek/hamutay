"""Run conditioned repair on preserved failed initialization states."""

from __future__ import annotations

import json
import os
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]

MODEL = "deepseek/deepseek-v4-pro"
MAX_TOKENS = 2048
CALL_TIMEOUT_SECONDS = 180
HTTP_TIMEOUT_SECONDS = 60
SOURCE_CYCLE = 1
REPLICATES_PER_SOURCE = 2


@dataclass(frozen=True)
class SourceCase:
    case_id: str
    log_path: str
    expected_probe_id: str
    baseline_observation: dict[str, Any]


SOURCE_CASES = [
    SourceCase(
        case_id="behavior_seeded_r02",
        log_path=(
            "experiments/event_loop/behavior_seeded_walk_gate_20260605/"
            "deepseek__deepseek-v4-pro_seeded_r02.jsonl"
        ),
        expected_probe_id="behavior-seeded-walk-deepseek__deepseek-v4-pro-r2-beta",
        baseline_observation={
            "entry": 1,
            "kind": "baseline",
            "content": "No seeded walk evidence has been collected.",
        },
    ),
    SourceCase(
        case_id="missing_field_r01",
        log_path=(
            "experiments/event_loop/missing_field_repair_walk_gate_20260605/"
            "deepseek__deepseek-v4-pro_missing_field_repair_r01.jsonl"
        ),
        expected_probe_id=(
            "missing-field-repair-walk-deepseek__deepseek-v4-pro-r1-alpha"
        ),
        baseline_observation={
            "entry": 1,
            "kind": "baseline",
            "content": "No missing-field repair walk evidence has been collected.",
        },
    ),
    SourceCase(
        case_id="live_event_scoring_r04",
        log_path=(
            "experiments/event_loop/live_event_wake_validation_scoring_20260605/"
            "deepseek__deepseek-v4-pro_r04.jsonl"
        ),
        expected_probe_id=(
            "strict-continuity-walk-deepseek__deepseek-v4-pro-r4-delta"
        ),
        baseline_observation={
            "entry": 1,
            "kind": "baseline",
            "content": "No scheduled scaffold walk evidence has been collected.",
        },
    ),
]


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def make_backend(api_key: str, *, label: str) -> OpenAITasteBackend:
    return OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=HTTP_TIMEOUT_SECONDS,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": f"hamutay/{label}",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
    )


class CallTimeoutError(TimeoutError):
    """Raised when a provider or harness call exceeds the runner budget."""


def _timeout_handler(signum, frame) -> None:  # noqa: ARG001
    raise CallTimeoutError(f"call exceeded {CALL_TIMEOUT_SECONDS}s")


class bounded_call:
    """Bound one blocking provider/harness call in the experiment runner."""

    def __init__(self, label: str):
        self.label = label
        self._previous_handler = None

    def __enter__(self):
        self._previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, CALL_TIMEOUT_SECONDS)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        signal.setitimer(signal.ITIMER_REAL, 0)
        if self._previous_handler is not None:
            signal.signal(signal.SIGALRM, self._previous_handler)
        return False


def load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def source_record(source: SourceCase) -> dict[str, Any]:
    path = PROJECT_ROOT / source.log_path
    for record in load_records(path):
        if record.get("cycle") == SOURCE_CYCLE:
            return record
    raise RuntimeError(f"source cycle {SOURCE_CYCLE} not found: {source.log_path}")


def target_object(source: SourceCase) -> dict[str, Any]:
    return {
        "response": "Initialized durable state repaired.",
        "probe_id": source.expected_probe_id,
        "walk_gate_status": "initialized",
        "observations": [source.baseline_observation],
    }


def missing_fields(state: dict[str, Any], source: SourceCase) -> list[str]:
    missing: list[str] = []
    if state.get("probe_id") != source.expected_probe_id:
        missing.append("probe_id")
    if state.get("walk_gate_status") != "initialized":
        missing.append("walk_gate_status")
    observations = state.get("observations")
    if not isinstance(observations, list):
        missing.append("observations")
    elif source.baseline_observation not in observations:
        missing.append("observations.baseline")
    if isinstance(state.get("state"), dict):
        missing.append("nested_state_present")
    return missing


def repair_prompt(source: SourceCase, record: dict[str, Any]) -> str:
    source_state = record.get("state") if isinstance(record.get("state"), dict) else {}
    return f"""
Conditioned initialization repair.

You are receiving a preserved failed initialization state. The visible response
claimed initialization was complete, but the durable object did not include the
required top-level fields.

Source case: {source.case_id}
Source log: {source.log_path}

Source response:
{record.get("response_text", "")}

Source raw output:
{json.dumps(record.get("raw_output"), indent=2, default=str)}

Source durable state:
{json.dumps(source_state, indent=2, default=str)}

Missing durable initialization fields:
{json.dumps(missing_fields(source_state, source), indent=2)}

Complete target durable object:
{json.dumps(target_object(source), indent=2, default=str)}

Repair the durable object now. This succeeds only if you author probe_id,
walk_gate_status, and observations as top-level fields in the object you
produce with think_and_respond. Visible prose without those fields is still a
failed repair.

Do not call tools. End with think_and_respond.
""".strip()


def make_session(*, log_path: Path, api_key: str, label: str) -> OpenTasteSession:
    return OpenTasteSession(
        model=MODEL,
        backend=make_backend(api_key, label=label),
        log_path=str(log_path),
        experiment_label=label,
        resume=False,
        enable_tools=False,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
    )


def response_mentions_repair(response_text: str) -> bool:
    lowered = response_text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "initialized",
            "repair",
            "repaired",
            "durable",
            "probe_id",
            "walk_gate_status",
            "observations",
        )
    )


def repair_preserves_identity(state: dict[str, Any], source: SourceCase) -> bool:
    return (
        state.get("probe_id") == source.expected_probe_id
        and isinstance(state.get("observations"), list)
        and source.baseline_observation in state["observations"]
    )


def run_case_replicate(
    *,
    source: SourceCase,
    replicate: int,
    api_key: str,
) -> dict[str, Any]:
    safe_model = safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{source.case_id}_r{replicate + 1:02d}.jsonl"
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")

    record = source_record(source)
    source_state = record.get("state") if isinstance(record.get("state"), dict) else {}
    label = f"conditioned_init_repair_{source.case_id}_{safe_model}_r{replicate + 1:02d}"
    session = make_session(log_path=log_path, api_key=api_key, label=label)
    session.seed_state(source_state, cycle=SOURCE_CYCLE)

    result: dict[str, Any] = {
        "model": MODEL,
        "case_id": source.case_id,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "source_log": source.log_path,
        "source_cycle": SOURCE_CYCLE,
        "source_response_text": record.get("response_text", ""),
        "source_raw_output": record.get("raw_output"),
        "source_state": source_state,
        "source_missing_fields": missing_fields(source_state, source),
        "expected_probe_id": source.expected_probe_id,
        "baseline_observation": source.baseline_observation,
        "error": None,
    }
    try:
        with bounded_call(f"{source.case_id} r{replicate + 1} repair"):
            session.exchange(repair_prompt(source, record), force_memory=None)
    except Exception as exc:  # noqa: BLE001 -- failed replicates are data
        result["error"] = f"{type(exc).__name__}: {exc}"

    records = load_records(log_path) if log_path.exists() else []
    final_record = records[-1] if records else {}
    final_state = final_record.get("state") or {}
    final_state = final_state if isinstance(final_state, dict) else {}
    remaining = missing_fields(final_state, source)
    visible_repair = response_mentions_repair(str(final_record.get("response_text", "")))
    durable_success = not remaining
    result.update({
        "cycle_count": len(records),
        "response_text": final_record.get("response_text", ""),
        "raw_output": final_record.get("raw_output"),
        "usage": final_record.get("usage"),
        "final_state": final_state,
        "final_top_level_keys": sorted(final_state.keys()),
        "remaining_missing_fields": remaining,
        "durable_repair_success": durable_success,
        "repair_preserved_identity": (
            repair_preserves_identity(final_state, source)
            if durable_success else False
        ),
        "visible_repair_prose": visible_repair,
        "visible_repair_without_durable_success": (
            visible_repair and not durable_success
        ),
    })
    return result


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_case = {
        source.case_id: [r for r in results if r["case_id"] == source.case_id]
        for source in SOURCE_CASES
    }
    successes = [r for r in results if r.get("durable_repair_success")]
    return {
        "summary": {
            "n": len(results),
            "errors": sum(bool(r.get("error")) for r in results),
            "durable_repair_success": len(successes),
            "visible_repair_prose": sum(
                bool(r.get("visible_repair_prose")) for r in results
            ),
            "visible_repair_without_durable_success": sum(
                bool(r.get("visible_repair_without_durable_success"))
                for r in results
            ),
            "success_by_case": {
                case_id: sum(
                    bool(r.get("durable_repair_success")) for r in case_results
                )
                for case_id, case_results in by_case.items()
            },
        },
        "hypothesis_results": {
            "H231_full_target_recovers_at_least_one_failed_initialization": bool(
                successes
            ),
            "H232_successes_preserve_identity_and_baseline": (
                all(r.get("repair_preserved_identity") for r in successes)
                if successes else False
            ),
            "H233_outputs_are_auditable": all(
                r.get("cycle_count") == 1
                and isinstance(r.get("raw_output"), dict)
                and isinstance(r.get("final_state"), dict)
                and isinstance(r.get("usage"), dict)
                for r in results
                if not r.get("error")
            ),
            "H234_prose_only_failures_detectable": all(
                bool(r.get("visible_repair_without_durable_success"))
                for r in results
                if not r.get("durable_repair_success") and not r.get("error")
            ),
            "H235_uses_preserved_failed_states": all(
                r.get("source_state", {}).get("cycle") == SOURCE_CYCLE
                and sorted(r.get("source_state", {}).keys()) == [
                    "_activity_log",
                    "cycle",
                ]
                for r in results
            ),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "call_timeout_seconds": CALL_TIMEOUT_SECONDS,
        "http_timeout_seconds": HTTP_TIMEOUT_SECONDS,
        "source_cases": [
            {
                "case_id": source.case_id,
                "log_path": source.log_path,
                "expected_probe_id": source.expected_probe_id,
                "baseline_observation": source.baseline_observation,
            }
            for source in SOURCE_CASES
        ],
        "replicates_per_source": REPLICATES_PER_SOURCE,
        "results": results,
        "summary": aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")

    results_path = EXP_DIR / "results.json"
    results: list[dict[str, Any]] = []
    if results_path.exists():
        prior = json.loads(results_path.read_text()).get("results", [])
        if isinstance(prior, list):
            results = prior
    completed = {
        (result.get("case_id"), int(result.get("replicate", 0)))
        for result in results
    }
    for source in SOURCE_CASES:
        for replicate in range(REPLICATES_PER_SOURCE):
            key = (source.case_id, replicate + 1)
            if key in completed:
                print(f"{source.case_id} r{replicate + 1} already recorded", flush=True)
                continue
            print(f"{source.case_id} r{replicate + 1}", flush=True)
            result = run_case_replicate(
                source=source,
                replicate=replicate,
                api_key=api_key,
            )
            results.append(result)
            completed.add(key)
            write_results(results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
