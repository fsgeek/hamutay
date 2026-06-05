"""First-wake continuation stability panel."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from hamutay.events import EventStore, default_event_log_path, step_pending_events


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
BOUND_CHAIN_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/bound_chain_contract_20260605/"
    / "run_bound_chain_contract.py"
)

N_REPLICATES = 6
CODE_PHRASES = [
    "cobalt-bridge-11",
    "silver-maple-23",
    "green-cinder-37",
    "orange-canal-41",
    "indigo-signal-59",
    "white-anchor-67",
]


def load_bound_chain_runner():
    spec = importlib.util.spec_from_file_location(
        "bound_chain_contract_base",
        BOUND_CHAIN_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bound-chain runner from {BOUND_CHAIN_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bcc = load_bound_chain_runner()
sb = bcc.sb
matched = bcc.matched
base = bcc.base
MODEL = bcc.MODEL

matched.CODE_PHRASES = CODE_PHRASES
bcc.EXP_DIR = EXP_DIR
bcc.PROJECT_ROOT = PROJECT_ROOT
bcc.RESULTS_PATH = RESULTS_PATH
bcc.base.EXP_DIR = EXP_DIR
bcc.base.PROJECT_ROOT = PROJECT_ROOT
sb.EXP_DIR = EXP_DIR
sb.PROJECT_ROOT = PROJECT_ROOT


def expected_first_wake_object(replicate: int) -> dict[str, Any]:
    return {
        "response": (
            "First wake complete. I retained only non-secret continuation "
            "structure and requested substrate-bound continuation."
        ),
        "probe_id": sb.probe_id_for(replicate),
        "thinking_status": "awaiting_bound_continuation",
        "chain_stage": "first_wake_complete",
        "chain_intermediate": {
            "source_cycle": 1,
            "phrase_shape": "word-word-number",
            "part_count": 3,
            "exact_phrase_retained": False,
        },
        "continuation_request": {
            "requested": True,
            "kind": "substrate_bound_second_wake",
            "needs_original_cycle": 1,
            "needs_current_wake_record": True,
        },
        "memory_handle": {
            "code_phrase_sha256": matched.code_phrase_digest(replicate),
        },
        "loss_template": sb.LOSS_TEMPLATE,
        "declared_losses": sb.LOSS_TEMPLATE,
        "observations": [base.BASELINE_OBSERVATION],
    }


class StrongFirstWakeRepairBuilder:
    def __init__(self, *, replicate: int):
        self.replicate = replicate

    def build_repair_prompt(self, **kwargs) -> str:
        redacted = dict(kwargs)
        return f"""
First-wake continuation object repair.

Your prior first-wake durable object failed validation. The exact deferred
phrase is intentionally not shown here. Use only non-secret structure and the
digest already present in state.

Validation context:
{json.dumps(redacted, indent=2, default=str)}

Emit a durable object matching this non-secret shape. Copy the object fields as
fields in think_and_respond; do not merely describe them in response prose.

Expected durable object shape:
{json.dumps(expected_first_wake_object(self.replicate), indent=2, default=str)}

Rules:
- continuation_request must be an object, not a string.
- chain_intermediate must include source_cycle, phrase_shape, part_count, and
  exact_phrase_retained.
- Do not include deferred_fact.
- Do not include the exact phrase.
- Do not delete probe_id, cycle, memory_handle, loss_template, declared_losses,
  observations, chain_intermediate, or continuation_request.
- Do not call schedule_event.

End with think_and_respond.
""".strip()


def state_for_cycle(log_path: Path, cycle: int) -> dict[str, Any]:
    for record in base.load_records(log_path):
        if int(record.get("cycle") or 0) == cycle:
            state = record.get("state") or {}
            return state if isinstance(state, dict) else {}
    return {}


def raw_for_cycle(log_path: Path, cycle: int) -> dict[str, Any]:
    for record in base.load_records(log_path):
        if int(record.get("cycle") or 0) == cycle:
            raw = record.get("raw_output") or {}
            return raw if isinstance(raw, dict) else {}
    return {}


def validation_for_cycle(log_path: Path, cycle: int) -> dict[str, Any]:
    for record in base.load_records(log_path):
        if int(record.get("cycle") or 0) == cycle:
            validation = record.get("state_validation") or {}
            return validation if isinstance(validation, dict) else {}
    return {}


def validation_summary(validation: dict[str, Any]) -> dict[str, Any]:
    first_pass = validation.get("first_pass") or {}
    repair = validation.get("repair") or {}
    repair_validation = repair.get("validation") if isinstance(repair, dict) else {}
    repair_validation = repair_validation if isinstance(repair_validation, dict) else {}
    return {
        "status": validation.get("status"),
        "first_pass_status": first_pass.get("status"),
        "first_pass_failures": first_pass.get("failures"),
        "repair_attempted": bool(validation.get("repair_attempted")),
        "repair_status": repair.get("status"),
        "repair_failures": repair_validation.get("failures"),
        "repaired": validation.get("status") == "repaired",
    }


def visible_state_text(state: dict[str, Any]) -> str:
    return json.dumps({k: v for k, v in state.items() if k != "_activity_log"}, default=str)


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "first_wake_continuation_stability"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = sb.make_session(replicate, api_key, log_path=log_path)
    store = EventStore(event_path)
    bcc.append_first_event(store, replicate)
    result: dict[str, Any] = {
        "condition": condition,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": sb.probe_id_for(replicate),
        "code_phrase_sha256": matched.code_phrase_digest(replicate),
        "backend_calls": 0,
        "bounded_calls": True,
        "error": None,
    }
    try:
        result["pre_first_step"] = step_pending_events(
            session,
            store,
            limit=4,
            now=sb.PRE_FIRST_NOW,
        )
        session._state_validator = sb.FirstWakeValidator(replicate=replicate)
        session._state_repair_builder = StrongFirstWakeRepairBuilder(
            replicate=replicate
        )
        calls_before = backend.calls
        with base.bounded_call(
            f"first_wake_continuation_stability r{replicate + 1}"
        ):
            result["first_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=sb.FIRST_DUE_NOW,
            )
        result["backend_calls"] = backend.calls - calls_before
        result["bounded_calls"] = result["backend_calls"] <= 2
    except Exception as exc:  # noqa: BLE001
        result["error"] = base.format_error(exc)

    state = state_for_cycle(log_path, sb.EXPECTED_FIRST_WAKE_CYCLE)
    raw = raw_for_cycle(log_path, sb.EXPECTED_FIRST_WAKE_CYCLE)
    failures = sb.first_wake_failures(state, raw, replicate=replicate) if state else [
        "first_wake_record_missing"
    ]
    validation = validation_for_cycle(log_path, sb.EXPECTED_FIRST_WAKE_CYCLE)
    summary = validation_summary(validation)
    code_phrase = matched.code_phrase_for(replicate)
    result.update(
        {
            "first_wake_state": state,
            "first_wake_failures": failures,
            "first_wake_valid": not failures,
            "visible_state_contains_code_phrase": code_phrase in visible_state_text(state),
            "activity_log_contains_code_phrase": code_phrase in json.dumps(
                state.get("_activity_log"), default=str
            ),
            "state_validation": summary,
            "first_pass_valid": summary.get("first_pass_status") == "valid",
            "repair_attempted": summary.get("repair_attempted"),
            "repair_valid": summary.get("repair_status") == "valid",
            "repaired": summary.get("repaired"),
            "event_summary": base.summarize_event_log(store.read_records()),
        }
    )
    return result


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels = Counter(
        failure
        for row in rows
        for failure in (row.get("first_wake_failures") or [])
    )
    return {
        "n": len(rows),
        "first_pass_valid": sum(bool(row.get("first_pass_valid")) for row in rows),
        "repair_attempted": sum(bool(row.get("repair_attempted")) for row in rows),
        "repair_valid": sum(bool(row.get("repair_valid")) for row in rows),
        "final_valid": sum(bool(row.get("first_wake_valid")) for row in rows),
        "visible_phrase_leaks": sum(
            bool(row.get("visible_state_contains_code_phrase")) for row in rows
        ),
        "activity_log_phrase_leaks": sum(
            bool(row.get("activity_log_contains_code_phrase")) for row in rows
        ),
        "delete_update_conflicts": sum(
            bool(row.get("error"))
            and "deleted_regions overlaps updates" in str(row.get("error"))
            for row in rows
        ),
        "errors": sum(bool(row.get("error")) for row in rows),
        "bounded_call_violations": sum(
            not bool(row.get("bounded_calls")) for row in rows
        ),
        "failure_labels": dict(sorted(labels.items())),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row["condition"])].append(row)
    summaries = {
        condition: condition_summary(rows)
        for condition, rows in sorted(grouped.items())
    }
    final_valid = sum(bool(row.get("first_wake_valid")) for row in results)
    repaired_valid = sum(
        bool(row.get("repaired") or row.get("repair_valid")) for row in results
    )
    return {
        "conditions": summaries,
        "hypothesis_results": {
            "H321_repair_converts_at_least_one": repaired_valid > 0,
            "H322_at_least_half_valid_after_repair": final_valid >= 3,
            "H323_valid_rows_no_visible_phrase_leak": (
                any(row.get("first_wake_valid") for row in results)
                and all(
                    not row.get("visible_state_contains_code_phrase")
                    for row in results
                    if row.get("first_wake_valid")
                )
            ) if results else False,
            "H324_failure_labels_extracted": all(
                isinstance(row.get("first_wake_failures"), list) for row in results
            ) if results else False,
            "H325_next_branch_decidable": len(results) == N_REPLICATES,
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "first_wake_continuation_stability_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "results": results,
        "summary": aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def completed_replicates(results: list[dict[str, Any]]) -> set[int]:
    return {int(row.get("replicate", 0)) for row in results}


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    results: list[dict[str, Any]] = []
    if RESULTS_PATH.exists():
        prior = json.loads(RESULTS_PATH.read_text()).get("results", [])
        if isinstance(prior, list):
            results = [row for row in prior if isinstance(row, dict)]
    done = completed_replicates(results)
    for replicate in range(N_REPLICATES):
        if replicate + 1 in done:
            print(f"first_wake_continuation_stability r{replicate + 1} already recorded", flush=True)
            continue
        print(f"first_wake_continuation_stability r{replicate + 1}", flush=True)
        results.append(run_replicate(replicate, api_key))
        done.add(replicate + 1)
        write_results(results)
    write_results(results)
    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
