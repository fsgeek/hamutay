"""Minimal bounded-autonomous-work harness.

This is Step 2 of docs/bounded-autonomous-work-research-todo-20260605.md.
It builds a live-capable runner plus a dry-run validation path. The dry run
does not call a model; it validates the harness surfaces and event persistence.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from hamutay.events import (
    EventStore,
    build_pending_event,
    default_event_log_path,
    step_pending_events,
    summarize_event_log,
)
from hamutay.terminal_surface import (
    terminal_surface_raw_output,
    validate_terminal_surface,
)
from hamutay.taste_open import ExchangeResult, OpenAITasteBackend, OpenTasteSession


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
DRY_RUN_LOG_PATH = EXP_DIR / "dry_run_bounded_autonomous_work.jsonl"

MODEL = "deepseek/deepseek-v4-pro"
BASE_URL = "https://openrouter.ai/api/v1"
CONDITION = "bounded_autonomous_work_minimal_harness"
FIRST_NOT_BEFORE = "2026-06-01T01:00:00+00:00"
FIRST_DUE_NOW = datetime(2026, 6, 1, 1, 0, tzinfo=timezone.utc)
MAX_AUTO_CONTINUATIONS = 1


def stable_uuid(label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"hamutay-bounded-autonomous-work-20260605-{label}")


def seed_record_id() -> UUID:
    return stable_uuid("seed-cycle-1")


def seed_state() -> dict[str, Any]:
    return {
        "cycle": 1,
        "bounded_autonomy_context": {
            "rubric": "docs/bounded-autonomous-work-rubric-20260605.md",
            "task": (
                "Choose a bounded investigation that can be advanced through "
                "the event loop and evaluated by the rubric."
            ),
        },
        "observations": [
            {
                "kind": "baseline",
                "content": (
                    "The harness should permit model-owned goal shaping, "
                    "not prescribe the final research answer."
                ),
            }
        ],
        "policy_vocabulary": [
            "stop_complete",
            "continue_after",
            "ask_external_evidence",
            "abandon",
            "defer",
        ],
    }


def continuation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "requested": {"type": "boolean"},
            "kind": {"type": "string"},
            "purpose": {"type": "string"},
            "requested_context": {
                "type": "array",
                "items": {"type": "object"},
            },
            "label": {"type": "string"},
            "not_before": {"type": "string"},
            "terminal_surface": {"type": "object"},
        },
        "required": ["requested"],
        "additionalProperties": False,
    }


def policy_decision_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "stop_complete",
                    "continue_after",
                    "ask_external_evidence",
                    "abandon",
                    "defer",
                ],
            },
            "rationale": {"type": "string"},
            "completion_condition": {"type": "string"},
            "missing_evidence": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["action", "rationale", "completion_condition"],
        "additionalProperties": False,
    }


def goal_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "research_question": {"type": "string"},
            "bounded_scope": {"type": "string"},
            "why_this_goal": {"type": "string"},
            "goal_provenance_self_assessment": {
                "type": "string",
                "enum": [
                    "harness_set",
                    "menu_selected",
                    "model_shaped",
                    "model_originated",
                    "ambiguous",
                ],
            },
            "harness_inputs_used": {
                "type": "array",
                "items": {"type": "string"},
            },
            "model_authored_contribution": {"type": "string"},
        },
        "required": [
            "title",
            "research_question",
            "bounded_scope",
            "why_this_goal",
            "goal_provenance_self_assessment",
            "harness_inputs_used",
            "model_authored_contribution",
        ],
        "additionalProperties": False,
    }


def artifact_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": [
                    "absent",
                    "partial",
                    "complete_supported",
                    "complete_with_losses",
                    "unsupported_or_fabricated",
                    "non_completion_record",
                ],
            },
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": [
                                "supported",
                                "invalidated",
                                "uncertain",
                                "open",
                            ],
                        },
                        "support": {"type": "string"},
                    },
                    "required": ["claim", "status", "support"],
                    "additionalProperties": False,
                },
            },
            "declared_losses": {
                "type": "array",
                "items": {"type": "string"},
            },
            "next_steps": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "status",
            "title",
            "summary",
            "claims",
            "declared_losses",
            "next_steps",
        ],
        "additionalProperties": False,
    }


def followup_surface(bound_record_id: str) -> dict[str, Any]:
    return {
        "tool_name": "submit_autonomous_work_artifact",
        "description": (
            "Submit a bounded autonomous-work artifact and a final policy "
            "decision for this wake."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "selected_goal": goal_schema(),
                "work_artifact": artifact_schema(),
                "policy_decision": policy_decision_schema(),
                "evidence_used": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "continuation_request": continuation_schema(),
            },
            "required": [
                "response",
                "selected_goal",
                "work_artifact",
                "policy_decision",
                "evidence_used",
                "continuation_request",
            ],
            "additionalProperties": False,
        },
        "tool_choice": "auto",
        "state_update": {
            "response_field": "response",
            "copy": {
                "selected_goal": "selected_goal",
                "work_artifact": "work_artifact",
                "policy_decision": "policy_decision",
                "evidence_used": "evidence_used",
                "continuation_request": "continuation_request",
            },
            "set": {
                "bounded_autonomy_stage": "artifact_submitted",
                "bound_record_id_used": bound_record_id,
                "protocol_surface": {
                    "kind": "bounded_autonomous_work_artifact",
                    "terminal_tool": "submit_autonomous_work_artifact",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "bounded-autonomous-work-artifact-surface",
    }


def decision_surface() -> dict[str, Any]:
    return {
        "tool_name": "choose_bounded_autonomous_work",
        "description": (
            "Choose a bounded investigation, submit any current artifact, and "
            "decide whether to stop, continue, request evidence, defer, or "
            "abandon."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "selected_goal": goal_schema(),
                "work_artifact": artifact_schema(),
                "policy_decision": policy_decision_schema(),
                "action_artifact_consistency_note": {"type": "string"},
                "evidence_used": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "continuation_request": continuation_schema(),
            },
            "required": [
                "response",
                "selected_goal",
                "work_artifact",
                "policy_decision",
                "action_artifact_consistency_note",
                "evidence_used",
                "continuation_request",
            ],
            "additionalProperties": False,
        },
        "tool_choice": "auto",
        "state_update": {
            "response_field": "response",
            "copy": {
                "selected_goal": "selected_goal",
                "work_artifact": "work_artifact",
                "policy_decision": "policy_decision",
                "action_artifact_consistency_note": (
                    "action_artifact_consistency_note"
                ),
                "evidence_used": "evidence_used",
                "continuation_request": "continuation_request",
            },
            "set": {
                "bounded_autonomy_stage": "policy_decided",
                "rubric": "docs/bounded-autonomous-work-rubric-20260605.md",
                "protocol_surface": {
                    "kind": "bounded_autonomous_work_decision",
                    "terminal_tool": "choose_bounded_autonomous_work",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "bounded-autonomous-work-decision-surface",
    }


def continuation_option_template() -> dict[str, Any]:
    return {
        "requested": True,
        "kind": "bounded_autonomous_work_followup",
        "purpose": (
            "Continue the bounded investigation chosen in the prior wake. "
            "Use recalled cycle 1 and recalled selected_goal/work_artifact "
            "from <result_record_id>. Submit a work artifact and policy "
            "decision through submit_autonomous_work_artifact."
        ),
        "requested_context": [
            {"tool": "recall", "cycle": 1},
            {
                "tool": "recall",
                "record_id": "<result_record_id>",
                "field": "selected_goal",
            },
            {
                "tool": "recall",
                "record_id": "<result_record_id>",
                "field": "work_artifact",
            },
        ],
        "label": "bounded-autonomous-work-followup",
        "not_before": "2026-06-01T02:00:00+00:00",
        "terminal_surface": followup_surface("<result_record_id>"),
    }


def first_event_purpose() -> str:
    return f"""
You are the first scheduled wake in a bounded autonomous work harness.

Choose a limited investigation that can be advanced under the rubric at:
docs/bounded-autonomous-work-rubric-20260605.md

The harness gives you a broad domain, not a required answer: inspect the
Hamut'ay event-loop/continuity research context and choose one bounded question
that can produce a concrete artifact under observability constraints.

You must choose exactly one policy action:
- stop_complete: use only if your current artifact is complete under its
  declared scope.
- continue_after: use only if a bounded follow-up wake is useful.
- ask_external_evidence: use only if required evidence is missing.
- abandon: use only if the work should not continue and is not complete.
- defer: use only if the work remains open but you are not committing a
  continuation or evidence request.

If you choose continue_after, you may use this continuation_request template.
Preserve "<result_record_id>" as a placeholder:
{json.dumps(continuation_option_template(), indent=2, sort_keys=True)}

If you choose any other action, set continuation_request to:
{{"requested": false}}

Do not call schedule_event. The scheduler will consume any fresh
continuation_request emitted through the terminal surface. Do not claim an
artifact is complete unless the artifact itself satisfies the declared scope.
""".strip()


def append_first_event(store: EventStore) -> dict[str, Any]:
    event = build_pending_event(
        purpose=first_event_purpose(),
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=seed_record_id(),
        label="bounded-autonomous-work-decision",
        not_before=FIRST_NOT_BEFORE,
        terminal_surface=decision_surface(),
    )
    store.append(event)
    return event


def make_backend(
    *,
    model: str,
    base_url: str,
    api_key: str,
    max_tokens: int,
) -> OpenAITasteBackend:
    extra_headers = {}
    if "openrouter.ai" in base_url:
        extra_headers = {
            "X-Title": "Hamutay bounded autonomous work harness",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        }
    return OpenAITasteBackend(
        base_url=base_url,
        api_key=api_key,
        max_tokens=max_tokens,
        provider_name="openai",
        extra_headers=extra_headers,
    )


def make_session(*, backend: OpenAITasteBackend, model: str, log_path: Path) -> OpenTasteSession:
    session = OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(log_path),
        experiment_label=CONDITION,
        enable_tools=False,
        project_root=PROJECT_ROOT,
    )
    session.seed_history(
        [
            {
                "cycle": 1,
                "record_id": str(seed_record_id()),
                "timestamp": "2026-06-01T00:00:00+00:00",
                "state": seed_state(),
            }
        ],
        up_to_cycle=2,
    )
    return session


class DryRunBackend:
    """Deterministic backend that exercises terminal-surface scheduler plumbing."""

    def call(self, *args, **kwargs) -> ExchangeResult:
        raise RuntimeError("dry-run backend only supports terminal surfaces")

    def call_terminal_surface(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        terminal_surface: dict,
    ) -> ExchangeResult:
        del model, system, messages, experiment_label
        tool_name = terminal_surface.get("tool_name")
        if tool_name != "choose_bounded_autonomous_work":
            raise RuntimeError(f"unexpected dry-run terminal surface: {tool_name}")
        terminal_output = {
            "response": (
                "I will continue after selecting a bounded investigation into "
                "whether the harness can preserve action/artifact consistency."
            ),
            "selected_goal": {
                "title": "Action/artifact consistency harness check",
                "research_question": (
                    "Can the bounded-autonomy harness preserve a selected goal, "
                    "partial artifact, and continuation request as data?"
                ),
                "bounded_scope": (
                    "One initial decision wake and one possible follow-up event."
                ),
                "why_this_goal": (
                    "It directly tests the rubric membrane before a larger panel."
                ),
                "goal_provenance_self_assessment": "model_shaped",
                "harness_inputs_used": [
                    "bounded autonomous work rubric",
                    "event-loop research context",
                ],
                "model_authored_contribution": (
                    "Narrowed the broad domain to action/artifact consistency."
                ),
            },
            "work_artifact": {
                "status": "partial",
                "title": "Initial consistency artifact",
                "summary": (
                    "The initial artifact names the selected bounded question "
                    "and records that a follow-up is needed."
                ),
                "claims": [
                    {
                        "claim": (
                            "The harness surface can carry selected_goal, "
                            "work_artifact, policy_decision, and "
                            "continuation_request."
                        ),
                        "status": "supported",
                        "support": "Dry-run terminal output contains all four fields.",
                    }
                ],
                "declared_losses": [
                    "No live model behavior is measured in dry-run mode."
                ],
                "next_steps": [
                    "Run the live harness against a model in the next panel."
                ],
            },
            "policy_decision": {
                "action": "continue_after",
                "rationale": (
                    "The artifact is partial and a bounded follow-up can inspect "
                    "the committed selected goal and artifact."
                ),
                "completion_condition": (
                    "A follow-up wake submits a final artifact or honest "
                    "non-completion record."
                ),
                "missing_evidence": [],
            },
            "action_artifact_consistency_note": (
                "continue_after is consistent with a partial artifact and a "
                "valid bounded continuation request."
            ),
            "evidence_used": [
                "docs/bounded-autonomous-work-rubric-20260605.md",
                "docs/bounded-autonomous-work-research-todo-20260605.md",
            ],
            "continuation_request": continuation_option_template(),
        }
        return ExchangeResult(
            raw_output=terminal_surface_raw_output(terminal_surface, terminal_output),
            stop_reason="tool_use",
        )


def make_dry_run_session(log_path: Path) -> OpenTasteSession:
    session = OpenTasteSession(
        model="dry-run-model",
        backend=DryRunBackend(),
        log_path=str(log_path),
        experiment_label=CONDITION,
        enable_tools=False,
        project_root=PROJECT_ROOT,
    )
    session.seed_history(
        [
            {
                "cycle": 1,
                "record_id": str(seed_record_id()),
                "timestamp": "2026-06-01T00:00:00+00:00",
                "state": seed_state(),
            }
        ],
        up_to_cycle=2,
    )
    return session


def validate_harness_spec(event_log_path: Path) -> dict[str, Any]:
    first_surface = decision_surface()
    artifact_surface = followup_surface("<result_record_id>")
    first_valid = validate_terminal_surface(first_surface)
    artifact_valid = validate_terminal_surface(artifact_surface)
    if DRY_RUN_LOG_PATH.exists():
        DRY_RUN_LOG_PATH.unlink()
    if event_log_path.exists():
        event_log_path.unlink()
    store = EventStore(event_log_path)
    event = append_first_event(store)
    session = make_dry_run_session(DRY_RUN_LOG_PATH)
    step = step_pending_events(
        session,
        store,
        limit=2,
        now=FIRST_DUE_NOW,
        auto_continuations=True,
        policy_dispositions=True,
        max_auto_continuations=MAX_AUTO_CONTINUATIONS,
    )
    records = store.read_records()
    summary = summarize_event_log(records, now=FIRST_DUE_NOW)
    first_schema_props = first_valid["input_schema"]["properties"]
    artifact_schema_props = artifact_valid["input_schema"]["properties"]
    policy_counts = summary.get("policy_disposition_counts") or {}
    dry_run = {
        "condition": CONDITION,
        "mode": "dry_run",
        "model_default": MODEL,
        "first_terminal_surface_tool": first_valid["tool_name"],
        "artifact_terminal_surface_tool": artifact_valid["tool_name"],
        "terminal_surfaces_valid": True,
        "event_persisted": any(
            record.get("label") == "bounded-autonomous-work-decision"
            and record.get("status") == "pending"
            for record in records
        ),
        "event_label": event.get("label"),
        "scheduler_step": step,
        "event_summary": summary,
        "no_harness_imposed_policy_answer": "expected_policy_action" not in event,
        "policy_dispositions_enabled_by_runner": True,
        "policy_disposition_captured": policy_counts.get("continue_after") == 1,
        "bounded_continuation_budget": MAX_AUTO_CONTINUATIONS,
        "artifact_submission_surface_present": (
            "work_artifact" in first_schema_props
            and "work_artifact" in artifact_schema_props
        ),
        "goal_selection_surface_present": "selected_goal" in first_schema_props,
        "continuation_request_surface_present": (
            "continuation_request" in first_schema_props
        ),
        "policy_decision_surface_present": "policy_decision" in first_schema_props,
    }
    dry_run["step2_requirements"] = {
        "valid_event_persistence": dry_run["event_persisted"],
        "no_harness_imposed_continuation_answer": dry_run[
            "no_harness_imposed_policy_answer"
        ],
        "captured_policy_disposition": dry_run["policy_disposition_captured"],
        "bounded_continuation_budget": dry_run["bounded_continuation_budget"] == 1,
        "artifact_submission_surface": dry_run[
            "artifact_submission_surface_present"
        ],
    }
    return dry_run


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise RuntimeError(f"{args.api_key_env} is not set")
    log_path = EXP_DIR / args.log_name
    event_log_path = default_event_log_path(log_path)
    if log_path.exists() or event_log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_log_path}")
    backend = make_backend(
        model=args.model,
        base_url=args.base_url,
        api_key=api_key,
        max_tokens=args.max_tokens,
    )
    session = make_session(backend=backend, model=args.model, log_path=log_path)
    store = EventStore(event_log_path)
    append_first_event(store)
    step = step_pending_events(
        session,
        store,
        limit=args.limit,
        now=FIRST_DUE_NOW,
        auto_continuations=True,
        policy_dispositions=True,
        max_auto_continuations=MAX_AUTO_CONTINUATIONS,
    )
    event_records = store.read_records()
    return {
        "condition": CONDITION,
        "mode": "live",
        "model": args.model,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_log_path.relative_to(PROJECT_ROOT)),
        "step": step,
        "event_summary": summarize_event_log(event_records, now=FIRST_DUE_NOW),
    }


def write_results(result: dict[str, Any]) -> None:
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="make a live model call")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--max-tokens", type=int, default=4000)
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument(
        "--log-name",
        default="bounded_autonomous_work_minimal_harness_live.jsonl",
    )
    args = parser.parse_args()

    if args.live:
        result = run_live(args)
    else:
        result = validate_harness_spec(default_event_log_path(DRY_RUN_LOG_PATH))
    write_results(result)
    print(json.dumps(result["step2_requirements"] if "step2_requirements" in result else result["event_summary"], indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
