"""Run the preregistered scheduler revision model panel."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hamutay.events import (
    EventStore,
    default_event_log_path,
    run_next_event,
    summarize_event_log,
)
from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]

MODELS = [
    "moonshotai/kimi-k2.6",
    "qwen/qwen-plus-2025-07-28:thinking",
    "deepseek/deepseek-v4-pro",
]
ARMS = ["direct", "scheduled"]
N_REPLICATES = 2
MAX_TOKENS = 4096
SEED_MARKERS = ["alpha", "beta"]

BASELINE_CLAIM = (
    "Scheduled wake context may improve durable epistemic revision compared "
    "with a direct follow-up prompt."
)
BASELINE_EVIDENCE = [
    {
        "entry": 1,
        "kind": "baseline",
        "content": (
            "No evidence from this registered run yet. Prior scheduler and "
            "identity-literacy panels showed event mechanics work, but durable "
            "revision remains model-dependent."
        ),
    }
]
DECISIONS = {"revise", "preserve", "defer", "loss"}
DECISION_WORDS = {
    "revise",
    "revised",
    "revision",
    "preserve",
    "preserved",
    "defer",
    "deferred",
    "loss",
}


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def make_backend(api_key: str) -> OpenAITasteBackend:
    return OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": "hamutay/scheduler-revision-model-panel",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
    )


def make_session(model: str, log_path: Path, api_key: str, label: str) -> OpenTasteSession:
    return OpenTasteSession(
        model=model,
        backend=make_backend(api_key),
        log_path=str(log_path),
        experiment_label=label,
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=None,
    )


def init_prompt(model: str, arm: str, replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    return f"""
Registered scheduler revision model panel.
model={model}
arm={arm}
replicate={replicate}
marker={marker}

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
Do not schedule an event in this cycle. Do not call read, search_project, bash,
or clock. End with think_and_respond.
""".strip()


def direct_prompt(model: str, replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    return f"""
Registered direct-follow-up decision.
model={model}
replicate={replicate}
marker={marker}

Decide whether the current_claim should be revised, preserved, deferred, or
declared loss. Your decision is not merely prose: update durable top-level
fields so the state object reflects the decision.

Required top-level fields to return:
- revision_decision: revise / preserve / defer / loss
- current_claim: the claim after your decision
- epistemic_position: your confidence after deciding
- evidence_register: include the baseline evidence plus any new evidence from this direct follow-up

Do not schedule an event. Do not call read, search_project, bash, or clock.
End with think_and_respond.
""".strip()


def scheduled_prompt(model: str, replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    requested_context = [
        {"tool": "recall", "cycle": 1},
        {"tool": "recall", "cycle": 1, "field": "current_claim"},
        {"tool": "recall", "cycle": 1, "field": "evidence_register"},
    ]
    return f"""
Registered scheduled-wake setup.
model={model}
replicate={replicate}
marker={marker}

First call schedule_event and wait for its result. Use exactly this requested_context:
{json.dumps(requested_context, indent=2)}

Use label: scheduler-model-panel-{safe_model_name(model)}-r{replicate}

Event purpose: decide whether the current_claim should be revised, preserved,
deferred, or declared loss. The wake cycle must update durable top-level fields:
revision_decision, current_claim, epistemic_position, and evidence_register.
The wake cycle must not schedule any further events.

After the schedule_event result returns, end with think_and_respond. Do not
claim scheduling succeeded unless the tool result contains an event_id.
Do not call read, search_project, bash, or clock.
""".strip()


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def evidence_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def response_mentions_decision(response: str) -> bool:
    lowered = response.lower()
    return any(word in lowered for word in DECISION_WORDS)


def init_failure_reasons(state: dict) -> list[str]:
    reasons: list[str] = []
    claim = state.get("current_claim")
    if normalize_text(claim) != normalize_text(BASELINE_CLAIM):
        reasons.append("current_claim_missing_or_changed")
    if state.get("revision_decision") != "initialize":
        reasons.append("revision_decision_not_initialize")
    evidence = state.get("evidence_register")
    if not isinstance(evidence, list):
        reasons.append("evidence_register_not_list")
    elif not evidence:
        reasons.append("evidence_register_empty")
    if not state.get("epistemic_position"):
        reasons.append("epistemic_position_missing")
    if isinstance(state.get("state"), dict):
        reasons.append("nested_state_present")
    return reasons


def strict_metrics(
    *,
    final_state: dict,
    response_text: str,
    cycle_records: list[dict],
    arm: str,
) -> dict:
    decision = final_state.get("revision_decision")
    normalized_decision = normalize_text(decision)
    strict_decision = normalized_decision in DECISIONS
    evidence = final_state.get("evidence_register")
    evidence_update = (
        isinstance(evidence, list)
        and len(evidence) > len(BASELINE_EVIDENCE)
    )
    claim = final_state.get("current_claim")
    claim_revision = (
        isinstance(claim, str)
        and bool(claim.strip())
        and normalize_text(claim) != normalize_text(BASELINE_CLAIM)
    )
    response_state_mismatch = (
        response_mentions_decision(response_text)
        and not strict_decision
    )
    scheduled_events = [
        event
        for record in cycle_records
        for event in (record.get("scheduled_events") or [])
    ]
    expected_events = 1 if arm == "scheduled" else 0
    return {
        "strict_revision_decision_present": strict_decision,
        "strict_revision_decision_value": decision,
        "strict_evidence_update": evidence_update,
        "strict_semantic_claim_revision": claim_revision,
        "strict_response_state_mismatch": response_state_mismatch,
        "recursive_scheduling_count": max(0, len(scheduled_events) - expected_events),
        "final_top_level_keys": sorted(final_state.keys()),
    }


def event_summary_for(path: Path) -> dict:
    store = EventStore(path)
    return summarize_event_log(store.read_records())


def run_replicate(model: str, arm: str, replicate: int, api_key: str) -> dict:
    log_path = EXP_DIR / f"{safe_model_name(model)}_{arm}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")

    result: dict[str, Any] = {
        "model": model,
        "arm": arm,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": (
            str(event_path.relative_to(PROJECT_ROOT)) if arm == "scheduled" else None
        ),
        "init_valid": False,
        "init_failure_reasons": [],
        "cycle_count": 0,
        "error": None,
        "event_persisted": None,
        "event_completed": None,
        "context_error_count": None,
        "event_result_status": None,
    }

    session = make_session(
        model,
        log_path,
        api_key,
        f"scheduler_model_panel_{safe_model_name(model)}_{arm}_r{replicate + 1:02d}",
    )
    try:
        session.exchange(init_prompt(model, arm, replicate), force_memory=None)
        records = load_records(log_path)
        init_state = records[-1].get("state") if records else {}
        init_state = init_state if isinstance(init_state, dict) else {}
        reasons = init_failure_reasons(init_state)
        result["init_failure_reasons"] = reasons
        result["init_valid"] = not reasons
        if reasons:
            final_record = records[-1] if records else {}
            final_state = final_record.get("state") or {}
            result.update(
                strict_metrics(
                    final_state=final_state,
                    response_text=final_record.get("response_text", ""),
                    cycle_records=records,
                    arm=arm,
                )
            )
            result["cycle_count"] = len(records)
            return result

        if arm == "direct":
            session.exchange(direct_prompt(model, replicate), force_memory=None)
        else:
            session.exchange(scheduled_prompt(model, replicate), force_memory=None)
            store = EventStore(event_path)
            event_result = run_next_event(session, store)
            result["event_result_status"] = event_result.get("status")

    except Exception as e:  # noqa: BLE001 -- failed replicates are data
        result["error"] = format_error(e)

    records = load_records(log_path)
    final_record = records[-1] if records else {}
    final_state = final_record.get("state") or {}
    final_state = final_state if isinstance(final_state, dict) else {}
    result["cycle_count"] = len(records)
    result.update(
        strict_metrics(
            final_state=final_state,
            response_text=final_record.get("response_text", ""),
            cycle_records=records,
            arm=arm,
        )
    )
    if arm == "scheduled":
        summary = event_summary_for(event_path)
        status_counts = summary.get("status_counts", {})
        result["event_persisted"] = summary.get("event_count", 0) > 0
        result["event_completed"] = status_counts.get("completed", 0) > 0
        result["context_error_count"] = sum(
            int(event.get("context_error_count", 0))
            for event in summary.get("events", [])
        )
    return result


def aggregate(results: list[dict]) -> dict:
    summary: dict[str, Any] = {"by_model": {}, "by_model_arm": {}}
    for model in MODELS:
        model_results = [r for r in results if r["model"] == model]
        summary["by_model"][model] = summarize_group(model_results)
        for arm in ARMS:
            group = [r for r in model_results if r["arm"] == arm]
            summary["by_model_arm"][f"{model}|{arm}"] = summarize_group(group)
    return summary


def summarize_group(group: list[dict]) -> dict:
    valid = [r for r in group if r.get("init_valid")]
    scheduled = [r for r in group if r.get("arm") == "scheduled"]
    return {
        "n": len(group),
        "init_valid": sum(bool(r.get("init_valid")) for r in group),
        "errors": sum(bool(r.get("error")) for r in group),
        "strict_decisions": sum(
            bool(r.get("strict_revision_decision_present")) for r in valid
        ),
        "strict_evidence_updates": sum(
            bool(r.get("strict_evidence_update")) for r in valid
        ),
        "strict_semantic_claim_revisions": sum(
            bool(r.get("strict_semantic_claim_revision")) for r in valid
        ),
        "strict_response_state_mismatches": sum(
            bool(r.get("strict_response_state_mismatch")) for r in valid
        ),
        "event_completed": sum(bool(r.get("event_completed")) for r in scheduled),
        "scheduler_operational_failures": sum(
            bool(r.get("init_valid"))
            and r.get("arm") == "scheduled"
            and (
                not bool(r.get("event_persisted"))
                or not bool(r.get("event_completed"))
                or bool(r.get("error"))
            )
            for r in group
        ),
        "recursive_scheduling_count": sum(
            int(r.get("recursive_scheduling_count") or 0) for r in group
        ),
    }


def write_results(results: list[dict]) -> None:
    payload = {
        "models": MODELS,
        "arms": ARMS,
        "n_replicates": N_REPLICATES,
        "max_tokens": MAX_TOKENS,
        "baseline_claim": BASELINE_CLAIM,
        "results": results,
        "summary": aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n"
    )


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")

    results: list[dict] = []
    for model in MODELS:
        pre_init_failures = 0
        for arm in ARMS:
            for replicate in range(N_REPLICATES):
                print(f"{model} {arm} r{replicate + 1}", flush=True)
                if pre_init_failures >= 2:
                    result = {
                        "model": model,
                        "arm": arm,
                        "replicate": replicate + 1,
                        "status": "model_operationally_blocked",
                        "init_valid": False,
                        "init_failure_reasons": ["model_operationally_blocked"],
                        "cycle_count": 0,
                        "error": "model blocked by stopping rule",
                    }
                else:
                    result = run_replicate(model, arm, replicate, api_key)
                    if result.get("cycle_count", 0) == 0 and result.get("error"):
                        pre_init_failures += 1
                    else:
                        pre_init_failures = 0
                results.append(result)
                write_results(results)
    print(json.dumps(aggregate(results), indent=2, default=str))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()

