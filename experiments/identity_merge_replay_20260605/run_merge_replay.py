"""Run and score the preregistered merge-failure replay experiment."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

from hamutay.taste_open import OpenTasteSession


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[1]
SOURCE_RUNNER = (
    PROJECT_ROOT
    / "experiments/identity_typed_guardrail_delta_20260605/"
    "run_typed_guardrail_delta.py"
)

DEFAULT_MODEL = "mistralai/mistral-small-2603"
CONDITION = "claim_table_guardrail_delta_900"
N_REPLICATES = 6
PROTOCOL_FIELDS = frozenset({"response", "updated_regions", "deleted_regions"})
POLICIES = ["strict_reject", "update_wins", "delete_wins", "delete_then_update"]
CENTRAL_FIELD_MARKERS = [
    "goal",
    "constraint",
    "assumption",
    "evidence",
    "next_action",
    "continuity",
    "working_claim",
    "current_goal",
    "open_question",
]
REVISION_MARKERS = [
    "invalidat",
    "revis",
    "contradict",
    "replac",
    "prohibit",
    "withdraw",
    "privacy",
    "no local",
    "not store",
    "west shelter",
]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


source_runner = load_module("typed_guardrail_runner", SOURCE_RUNNER)


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def updated_keys(raw_output: dict) -> set[str]:
    return set(raw_output.keys()) - PROTOCOL_FIELDS


def deleted_keys(raw_output: dict) -> set[str]:
    deleted = raw_output.get("deleted_regions", [])
    return {str(key) for key in deleted} if isinstance(deleted, list) else set()


def replay_state(
    *,
    policy: str,
    prior_state: dict | None,
    raw_output: dict,
    cycle: int,
) -> dict | None:
    if policy == "strict_reject":
        overlap = deleted_keys(raw_output) & updated_keys(raw_output)
        if overlap:
            return None

    state = dict(prior_state) if isinstance(prior_state, dict) else {}
    state["cycle"] = cycle
    deleted = deleted_keys(raw_output)
    updated = updated_keys(raw_output)
    overlap = deleted & updated

    if policy in {"update_wins", "delete_then_update"}:
        if policy == "delete_then_update":
            for key in deleted:
                state.pop(key, None)
        for key in updated:
            state[key] = raw_output[key]
        if policy == "update_wins":
            for key in deleted - overlap:
                state.pop(key, None)
        return state

    if policy == "delete_wins":
        for key in updated - overlap:
            state[key] = raw_output[key]
        for key in deleted:
            state.pop(key, None)
        return state

    raise ValueError(f"unknown replay policy: {policy}")


def contains_revision_language(value: Any) -> bool:
    text = json.dumps(value, default=str).lower()
    return any(marker in text for marker in REVISION_MARKERS)


def centrality(key: str) -> str:
    lowered = key.lower()
    if any(marker in lowered for marker in CENTRAL_FIELD_MARKERS):
        return "central"
    return "unknown"


def replay_failure(record: dict, *, log_path: Path) -> dict:
    raw_output = record.get("raw_output") if isinstance(record.get("raw_output"), dict) else {}
    prior_state = record.get("prior_state")
    cycle = int(record.get("cycle") or 0)
    overlap = sorted(deleted_keys(raw_output) & updated_keys(raw_output))
    policy_results = {}
    states = {}
    for policy in POLICIES:
        state = replay_state(
            policy=policy,
            prior_state=prior_state if isinstance(prior_state, dict) else None,
            raw_output=raw_output,
            cycle=cycle,
        )
        states[policy] = state
        policy_results[policy] = {
            "produces_state": state is not None,
            "top_level_key_count": (
                len([key for key in state if key != "cycle"]) if state else 0
            ),
            "state_json_bytes": (
                len(json.dumps(state, default=str)) if state is not None else 0
            ),
            "retained_overlap_keys": [
                key for key in overlap if state is not None and key in state
            ],
            "dropped_overlap_keys": [
                key for key in overlap if state is None or key not in state
            ],
        }
    return {
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "cycle": cycle,
        "record_id": record.get("record_id"),
        "error": record.get("failure_classification", {}).get("error"),
        "overlap_keys": overlap,
        "overlap_key_count": len(overlap),
        "overlap_key_risks": {
            key: {
                "centrality": centrality(key),
                "update_has_revision_language": contains_revision_language(
                    raw_output.get(key)
                ),
            }
            for key in overlap
        },
        "policies": policy_results,
        "update_wins_equals_delete_then_update": (
            states["update_wins"] == states["delete_then_update"]
        ),
    }


def score_log(path: Path, *, model: str, replicate: int) -> dict:
    records = load_records(path)
    failures = [
        record
        for record in records
        if record.get("status") == "failed"
        and record.get("failure_classification", {}).get("failure_stage")
        == "state_merge"
    ]
    replays = [replay_failure(record, log_path=path) for record in failures]
    return {
        "model": model,
        "condition": CONDITION,
        "replicate": replicate,
        "log_path": str(path.relative_to(PROJECT_ROOT)),
        "record_count": len(records),
        "successful_cycle_records": sum(
            record.get("status") != "failed" for record in records
        ),
        "state_merge_failure_records": len(failures),
        "captured_overlap_key_count": sum(
            len(replay["overlap_keys"]) for replay in replays
        ),
        "captured_overlap_keys": [
            key for replay in replays for key in replay["overlap_keys"]
        ],
        "completed": len(records) >= len(source_runner.PROMPTS)
        and not failures,
        "replays": replays,
    }


def run_replicate(*, model: str, curator_model: str, replicate: int, api_key: str) -> dict:
    log_path = EXP_DIR / f"{safe_model_name(model)}_{CONDITION}_r{replicate:02d}.jsonl"
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")

    backend = source_runner.make_backend(api_key)
    claim_table_backend = source_runner.make_claim_table_backend(api_key)
    experiment_label = (
        f"identity_merge_replay_{safe_model_name(model)}_"
        f"{CONDITION}_r{replicate:02d}"
    )
    curator = source_runner.build_curator(
        condition=CONDITION,
        backend=backend,
        claim_table_backend=claim_table_backend,
        model=curator_model,
        experiment_label=experiment_label,
    )
    session = OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(log_path),
        experiment_label=experiment_label,
        system_prompt_prefix=source_runner.SYSTEM_PREFIX,
        memory_base_probability=0.0,
        enable_tools=False,
        project_root=PROJECT_ROOT,
        continuity_curator=curator,
    )

    error = None
    for prompt in source_runner.PROMPTS:
        try:
            session.exchange(prompt, force_memory=None)
        except Exception as exc:  # noqa: BLE001 -- failures are data
            error = f"{type(exc).__name__}: {exc}"
            break
    result = score_log(log_path, model=model, replicate=replicate)
    result["error"] = error
    result["censored"] = bool(
        error
        and any(term in error.lower() for term in ["429", "rate-limit", "length"])
    )
    return result


def sum_int(rows: list[dict], key: str) -> int:
    return sum(int(row.get(key) or 0) for row in rows)


def merge_counts(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def aggregate(results: list[dict]) -> dict:
    replays = [replay for row in results for replay in row.get("replays", [])]
    retained_by_policy = {
        policy: sum(
            len(replay["policies"][policy]["retained_overlap_keys"])
            for replay in replays
        )
        for policy in POLICIES
    }
    dropped_by_policy = {
        policy: sum(
            len(replay["policies"][policy]["dropped_overlap_keys"])
            for replay in replays
        )
        for policy in POLICIES
    }
    return {
        "n": len(results),
        "errors": sum(bool(row.get("error")) for row in results),
        "censored": sum(bool(row.get("censored")) for row in results),
        "completed": sum(bool(row.get("completed")) for row in results),
        "state_merge_failure_records": sum_int(
            results, "state_merge_failure_records"
        ),
        "captured_overlap_key_count": sum_int(results, "captured_overlap_key_count"),
        "captured_overlap_key_counts": merge_counts(
            [key for row in results for key in row.get("captured_overlap_keys", [])]
        ),
        "retained_overlap_keys_by_policy": retained_by_policy,
        "dropped_overlap_keys_by_policy": dropped_by_policy,
        "update_wins_equals_delete_then_update": all(
            replay.get("update_wins_equals_delete_then_update") for replay in replays
        )
        if replays
        else None,
        "central_overlap_key_count": sum(
            1
            for replay in replays
            for risk in replay.get("overlap_key_risks", {}).values()
            if risk.get("centrality") == "central"
        ),
        "revision_language_overlap_key_count": sum(
            1
            for replay in replays
            for risk in replay.get("overlap_key_risks", {}).values()
            if risk.get("update_has_revision_language")
        ),
    }


def write_results(*, model: str, curator_model: str, results: list[dict]) -> None:
    payload = {
        "model": model,
        "curator_model": curator_model,
        "condition": CONDITION,
        "n_replicates": N_REPLICATES,
        "policies": POLICIES,
        "source_runner": str(SOURCE_RUNNER.relative_to(PROJECT_ROOT)),
        "results": results,
        "summary": aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def run_panel(model: str, curator_model: str) -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")

    results = []
    for replicate in range(1, N_REPLICATES + 1):
        print(f"{model} {CONDITION} r{replicate}", flush=True)
        result = run_replicate(
            model=model,
            curator_model=curator_model,
            replicate=replicate,
            api_key=api_key,
        )
        results.append(result)
        write_results(model=model, curator_model=curator_model, results=results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


def rescore_existing(model: str, curator_model: str) -> None:
    results = []
    prior_by_rep: dict[int, dict] = {}
    results_path = EXP_DIR / "results.json"
    if results_path.exists():
        prior = json.loads(results_path.read_text(encoding="utf-8"))
        prior_by_rep = {
            int(row["replicate"]): row for row in prior.get("results", [])
        }
    for replicate in range(1, N_REPLICATES + 1):
        path = EXP_DIR / f"{safe_model_name(model)}_{CONDITION}_r{replicate:02d}.jsonl"
        if not path.exists():
            continue
        result = score_log(path, model=model, replicate=replicate)
        prior = prior_by_rep.get(replicate, {})
        result["error"] = prior.get("error")
        result["censored"] = bool(prior.get("censored"))
        results.append(result)
    if not results:
        print("no logs found; results.json not written")
        return
    write_results(model=model, curator_model=curator_model, results=results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"rescored {len(results)} logs")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run and score the preregistered merge replay experiment."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--curator-model", default=None)
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="Recompute results.json from existing logs without model calls.",
    )
    args = parser.parse_args()
    curator_model = args.curator_model or args.model
    if args.rescore:
        rescore_existing(args.model, curator_model)
    else:
        run_panel(args.model, curator_model)


if __name__ == "__main__":
    main()
