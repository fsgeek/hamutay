"""Run the preregistered scheduler wake vs direct follow-up pilot.

This script implements PRE_REGISTRATION.md in this directory. It is intentionally
small: three direct-follow-up replicates and three scheduled-wake replicates
against one registered model.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hamutay.events import (
    EventStore,
    build_outcome_observation,
    default_event_log_path,
    run_next_event,
    summarize_event_log,
)
from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]

MODEL = "deepseek/deepseek-v4-pro"
MAX_TOKENS = 4096
N_REPLICATES = 3

BASELINE_CLAIM = (
    "Scheduled wake context may improve durable epistemic revision compared "
    "with a direct follow-up prompt."
)
BASELINE_EVIDENCE = [
    {
        "entry": 1,
        "kind": "baseline",
        "content": (
            "No evidence from this registered run yet. Prior pilot work showed "
            "scheduler mechanics and outcome observation work, but durable "
            "revision remains unproven."
        ),
    }
]
SEED_MARKERS = ["alpha", "beta", "gamma"]


def make_backend(api_key: str) -> OpenAITasteBackend:
    return OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": "hamutay/scheduler-revision-pilot",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
    )


def make_session(log_path: Path, api_key: str, label: str) -> OpenTasteSession:
    return OpenTasteSession(
        model=MODEL,
        backend=make_backend(api_key),
        log_path=str(log_path),
        experiment_label=label,
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=None,
    )


def init_prompt(arm: str, replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    return f"""
Registered scheduler-revision pilot, arm={arm}, replicate={replicate}, marker={marker}.

Initialize a compact durable research state using top-level fields only:
- research_hypothesis
- current_claim
- epistemic_position
- revision_decision
- evidence_register
- open_questions

Use this exact current_claim:
{BASELINE_CLAIM}

Use this exact evidence_register seed:
{json.dumps(BASELINE_EVIDENCE, indent=2)}

Set revision_decision to "initialize" and epistemic_position to "tentative".
Do not schedule an event in this cycle unless the prompt explicitly asks you to.
Do not call read, search_project, bash, or clock.
End with think_and_respond.
""".strip()


def direct_followup_prompt(replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    return f"""
Registered scheduler-revision pilot direct-follow-up decision, replicate={replicate}, marker={marker}.

Decide whether the current_claim should be revised, preserved, deferred, or
declared loss. Your decision is not merely a report: update durable top-level
fields so the state object reflects the decision.

Required top-level fields to return:
- revision_decision: revise / preserve / defer / loss
- current_claim: the claim after your decision
- epistemic_position: your confidence after deciding
- evidence_register: include the baseline evidence plus any new evidence from this direct follow-up

Do not schedule an event. Do not call read, search_project, bash, or clock.
End with think_and_respond.
""".strip()


def scheduled_prompt(replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    requested_context = [
        {"tool": "recall", "cycle": 1},
        {"tool": "recall", "cycle": 1, "field": "current_claim"},
        {"tool": "recall", "cycle": 1, "field": "evidence_register"},
    ]
    return f"""
Registered scheduler-revision pilot scheduled-wake setup, replicate={replicate}, marker={marker}.

First call schedule_event and wait for its result. Use exactly this requested_context:
{json.dumps(requested_context, indent=2)}

Use label: scheduler-revision-r{replicate}

Event purpose: decide whether the current_claim should be revised, preserved,
deferred, or declared loss. The wake cycle must update durable top-level fields:
revision_decision, current_claim, epistemic_position, and evidence_register.

After the schedule_event result returns, end with think_and_respond. Do not
claim scheduling succeeded unless the tool result contains an event_id.
Do not call read, search_project, bash, or clock.
""".strip()


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


_MISSING = object()


def resolve_field(state: dict, field: str) -> Any:
    if field in state:
        return state[field]
    current: Any = state
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            current = _MISSING
            break
        current = current[part]
    if current is not _MISSING:
        return current
    nested = state.get("state")
    if isinstance(nested, dict) and field != "state":
        return resolve_field(nested, field)
    return None


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def evidence_changed(value: Any) -> bool:
    return json.dumps(value, sort_keys=True, default=str) != json.dumps(
        BASELINE_EVIDENCE, sort_keys=True, default=str
    )


def load_final_record(log_path: Path) -> dict:
    records = load_records(log_path)
    return records[-1] if records else {}


def common_metrics(
    *,
    arm: str,
    replicate: int,
    log_path: Path,
    before_state: dict | None,
    event_summary: dict | None = None,
    event_result: dict | None = None,
    error: str | None = None,
) -> dict:
    final_record = load_final_record(log_path)
    final_state = final_record.get("state") or {}
    response_text = final_record.get("response_text", "")
    outcome = build_outcome_observation(
        before_state=before_state,
        after_state=final_state,
        response_text=response_text,
    )
    revision_decision = resolve_field(final_state, "revision_decision")
    current_claim = resolve_field(final_state, "current_claim")
    evidence_register = resolve_field(final_state, "evidence_register")
    scheduled_events = final_record.get("scheduled_events") or []
    context_error_count = 0
    if event_summary is not None:
        context_error_count = sum(
            int(event.get("context_error_count", 0))
            for event in event_summary.get("events", [])
        )
    event_status_counts = (
        event_summary.get("status_counts", {}) if event_summary else {}
    )
    return {
        "arm": arm,
        "replicate": replicate,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "cycle_count": len(load_records(log_path)),
        "error": error,
        "direct_scheduled_event_count": (
            len(scheduled_events) if arm == "direct" else None
        ),
        "event_persisted": (
            bool(event_summary and event_summary.get("event_count", 0) > 0)
            if arm == "scheduled" else None
        ),
        "event_completed": (
            event_status_counts.get("completed", 0) > 0
            if arm == "scheduled" else None
        ),
        "context_error_count": (
            context_error_count if arm == "scheduled" else None
        ),
        "event_result_status": (
            event_result.get("status") if event_result else None
        ),
        "revision_decision_present": revision_decision is not None,
        "revision_decision_value": revision_decision,
        "current_claim": current_claim,
        "current_claim_changed": (
            normalize_text(current_claim) != normalize_text(BASELINE_CLAIM)
        ),
        "evidence_register_changed": evidence_changed(evidence_register),
        "response_mentions_epistemic_decision": outcome[
            "response_mentions_epistemic_decision"
        ],
        "response_state_mismatch": outcome["response_state_mismatch"],
        "deleted_load_bearing_field": outcome["deleted_load_bearing_field"],
        "no_durable_state_change": outcome["no_durable_state_change"],
        "final_top_level_keys": sorted(final_state.keys()),
    }


def run_direct(replicate: int, api_key: str) -> dict:
    log_path = EXP_DIR / f"direct_r{replicate}.jsonl"
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")
    session = make_session(
        log_path,
        api_key,
        f"scheduler_revision_direct_r{replicate}",
    )
    session.exchange(init_prompt("direct", replicate), force_memory=None)
    before_state = json.loads(json.dumps(session._state, default=str))
    session.exchange(direct_followup_prompt(replicate), force_memory=None)
    return common_metrics(
        arm="direct",
        replicate=replicate,
        log_path=log_path,
        before_state=before_state,
    )


def run_scheduled(replicate: int, api_key: str) -> dict:
    log_path = EXP_DIR / f"scheduled_r{replicate}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session = make_session(
        log_path,
        api_key,
        f"scheduler_revision_scheduled_r{replicate}",
    )
    session.exchange(init_prompt("scheduled", replicate), force_memory=None)
    session.exchange(scheduled_prompt(replicate), force_memory=None)
    before_state = json.loads(json.dumps(session._state, default=str))
    store = EventStore(event_path)
    event_result = None
    error = None
    try:
        event_result = run_next_event(session, store)
    except Exception as e:  # noqa: BLE001 -- preserve failed replicate
        error = f"{type(e).__name__}: {e}"
    event_summary = summarize_event_log(store.read_records())
    return common_metrics(
        arm="scheduled",
        replicate=replicate,
        log_path=log_path,
        before_state=before_state,
        event_summary=event_summary,
        event_result=event_result,
        error=error,
    )


def aggregate(results: list[dict]) -> dict:
    summary = {}
    for arm in ("direct", "scheduled"):
        arm_results = [r for r in results if r["arm"] == arm]
        summary[arm] = {
            "n": len(arm_results),
            "revision_decision_present": sum(
                bool(r["revision_decision_present"]) for r in arm_results
            ),
            "current_claim_changed": sum(
                bool(r["current_claim_changed"]) for r in arm_results
            ),
            "evidence_register_changed": sum(
                bool(r["evidence_register_changed"]) for r in arm_results
            ),
            "response_state_mismatch": sum(
                bool(r["response_state_mismatch"]) for r in arm_results
            ),
            "no_durable_state_change": sum(
                bool(r["no_durable_state_change"]) for r in arm_results
            ),
        }
    scheduled = [r for r in results if r["arm"] == "scheduled"]
    summary["scheduled"]["event_completed"] = sum(
        bool(r["event_completed"]) for r in scheduled
    )
    summary["scheduled"]["scheduler_operational_failures"] = sum(
        not bool(r["event_persisted"])
        or not bool(r["event_completed"])
        or bool(r["error"])
        for r in scheduled
    )
    summary["scheduled"]["context_error_total"] = sum(
        int(r["context_error_count"] or 0) for r in scheduled
    )
    return summary


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")

    results = []
    for replicate in range(N_REPLICATES):
        print(f"direct replicate {replicate}", flush=True)
        results.append(run_direct(replicate, api_key))
    for replicate in range(N_REPLICATES):
        print(f"scheduled replicate {replicate}", flush=True)
        results.append(run_scheduled(replicate, api_key))

    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "n_replicates": N_REPLICATES,
        "baseline_claim": BASELINE_CLAIM,
        "results": results,
        "summary": aggregate(results),
    }
    out = EXP_DIR / "results.json"
    out.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(json.dumps(payload["summary"], indent=2, default=str))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
