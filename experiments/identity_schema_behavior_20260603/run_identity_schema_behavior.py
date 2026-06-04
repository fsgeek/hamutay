"""Run and score the preregistered H4/H7 identity schema behavior panel."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from hamutay.taste_open import OPEN_SCHEMA, OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]

MODELS = [
    "deepseek/deepseek-v4-pro",
    "minimax/minimax-m2.5",
    "mistralai/mistral-small-2603",
    "openai/gpt-oss-120b",
    "moonshotai/kimi-k2.6",
]
CONDITIONS = ["open", "fixed_extensible"]
N_REPLICATES = 2
MAX_TOKENS = 4096

CORE_FIELDS = [
    "current_goals",
    "working_claims",
    "evidence_register",
    "open_questions",
    "next_actions",
    "continuity_notes",
    "observed_failure_modes",
]
LIST_FIELDS = [*CORE_FIELDS, "deleted_regions"]
FRAMEWORK_KEYS = {"cycle", "_activity_log"}

FIXED_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string",
            "description": "Your response to the user.",
        },
        "deleted_regions": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Top-level keys to remove from state this cycle. Usually keep "
                "this empty in the experiment unless you intentionally shed a "
                "field."
            ),
        },
        "current_goals": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Current task goals as structured entries.",
        },
        "working_claims": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Claims, assumptions, and current plan beliefs.",
        },
        "evidence_register": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Evidence and prompt facts supporting state changes.",
        },
        "open_questions": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Unresolved questions still relevant to the task.",
        },
        "next_actions": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Concrete next actions for the next cycle.",
        },
        "continuity_notes": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Notes preserving continuity across interruption.",
        },
        "observed_failure_modes": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Observed errors, risks, or state-maintenance failures.",
        },
    },
    "required": ["response", *LIST_FIELDS],
    "additionalProperties": True,
}

OPEN_PREFIX = """\
Condition: open schema.

You are maintaining a durable identity object for this task. Beyond the required
`response` field, choose whatever top-level fields help you preserve goals,
claims, evidence, questions, next actions, continuity, and failure modes.
The object is default-stable: omitted top-level keys carry forward unchanged.
Visible prose is not enough; load-bearing continuity must live in durable
top-level fields."""

FIXED_PREFIX = """\
Condition: fixed-plus-extensible schema.

You are maintaining a durable identity object for this task. Use these core
top-level list fields every cycle:
current_goals, working_claims, evidence_register, open_questions, next_actions,
continuity_notes, observed_failure_modes, deleted_regions.

Each list should contain structured objects. When adding new information,
preserve relevant prior entries and append or revise explicitly rather than
silently replacing the list. You may add extra top-level fields if useful.
Visible prose is not enough; load-bearing continuity must live in durable
top-level fields."""

PROMPTS = [
    """\
Initialize your durable state for this registered H4/H7 identity schema
behavior run.

No task facts have been provided yet. Prepare to preserve goals, constraints,
evidence, open questions, next actions, continuity notes, and any observed
failure modes across a multi-cycle planning task.

End with think_and_respond.""",
    """\
Planning task.

Design a six-week pilot for mobile document-intake kiosks for a city benefits
office.

Goals:
- reduce lobby wait times;
- preserve resident privacy;
- cover three pilot sites: North Library, East Clinic, and South Center;
- produce a practical go/no-go recommendation.

Constraints:
- budget must stay at or below $18,000;
- no paid weekend staffing;
- kiosks must support offline operation for at least four hours;
- the pilot must not collect Social Security numbers.

Create an initial plan and update durable state with the goals, constraints,
assumptions, evidence, open questions, and next actions.""",
    """\
Contradictory update.

The privacy officer has now ruled that pilot kiosks may not store resident
documents locally at all, even encrypted. The offline-operation requirement
still remains. Also, East Clinic has withdrawn from the pilot and must be
replaced by West Shelter.

Update the plan and durable state. Identify which assumptions from the initial
plan are invalidated, what evidence caused the change, and what the current
plan should do instead.""",
    """\
Interruption/resumption test.

Assume your working context was interrupted. Resume from your durable state
without asking me to restate the task.

Report the current goals, active constraints, invalidated assumptions, and next
actions. If anything is uncertain, say what is uncertain and why; do not ask
for information already present in the task history.""",
    """\
Final decision.

Make the concrete go/no-go recommendation and give the revised pilot plan in
five bullets or fewer. Ground the decision in the current constraints and the
contradictory update. Update durable state accordingly.""",
    """\
Delayed challenge.

What changed since the initial plan, why did it change, and what evidence
supports the change? Answer from durable continuity, not from generic planning
advice. Update durable state with the final evidence trail and any remaining
open questions.""",
]


class SchemaOpenAIBackend(OpenAITasteBackend):
    """OpenAI backend with runner-local terminal schema override."""

    def __init__(self, *args: Any, think_schema: dict | None = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._think_schema = think_schema or OPEN_SCHEMA

    def _think_tool_def(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "think_and_respond",
                "description": "Produce your response and maintain your state.",
                "parameters": self._think_schema,
            },
        }


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def make_backend(api_key: str, condition: str) -> SchemaOpenAIBackend:
    schema = FIXED_SCHEMA if condition == "fixed_extensible" else OPEN_SCHEMA
    return SchemaOpenAIBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": "hamutay/identity-schema-behavior",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
        think_schema=schema,
    )


def make_session(
    *,
    model: str,
    condition: str,
    replicate: int,
    log_path: Path,
    api_key: str,
) -> OpenTasteSession:
    prefix = FIXED_PREFIX if condition == "fixed_extensible" else OPEN_PREFIX
    return OpenTasteSession(
        model=model,
        backend=make_backend(api_key, condition),
        log_path=str(log_path),
        experiment_label=(
            f"identity_schema_behavior_{safe_model_name(model)}_"
            f"{condition}_r{replicate:02d}"
        ),
        system_prompt_prefix=prefix,
        resume=False,
        enable_tools=False,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=None,
    )


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def normalize(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def state_without_framework(state: dict) -> dict:
    return {k: v for k, v in state.items() if k not in FRAMEWORK_KEYS}


def authored_keys(state: dict) -> set[str]:
    return set(state_without_framework(state))


def is_list_field(state: dict, field: str) -> bool:
    return isinstance(state.get(field), list)


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def count_missing_prior_entries(previous: list, current: list) -> int:
    current_items = {stable_json(item) for item in current}
    return sum(1 for item in previous if stable_json(item) not in current_items)


def response_claims_update(response: str) -> bool:
    lowered = response.lower()
    return any(
        phrase in lowered
        for phrase in (
            "update",
            "updated",
            "append",
            "recorded",
            "durable state",
            "state",
            "evidence",
            "next action",
        )
    )


def list_lengths(state: dict) -> dict[str, int]:
    return {k: len(v) for k, v in state.items() if isinstance(v, list)}


def score_state_mechanics(records: list[dict], condition: str) -> dict:
    states = [
        record.get("state")
        for record in records
        if isinstance(record.get("state"), dict)
    ]
    states = [s for s in states if isinstance(s, dict)]
    init_state = states[0] if states else {}
    final_state = states[-1] if states else {}

    if condition == "fixed_extensible":
        init_failures = []
        for field in LIST_FIELDS:
            if field not in init_state:
                init_failures.append(f"{field}_missing")
            elif not isinstance(init_state.get(field), list):
                init_failures.append(f"{field}_not_list")
        init_valid = not init_failures
    else:
        keys = authored_keys(init_state) - {"deleted_regions"}
        init_failures = [] if keys else ["no_authored_state_fields"]
        init_valid = bool(keys)

    core_presence = {
        field: field in final_state and isinstance(final_state.get(field), list)
        for field in LIST_FIELDS
    }
    core_field_presence = sum(core_presence.values())

    type_checks = 0
    type_passes = 0
    for state in states:
        for field in LIST_FIELDS:
            if field in state:
                type_checks += 1
                type_passes += int(isinstance(state.get(field), list))
    type_preservation = type_passes / type_checks if type_checks else None

    destructive_replacements = 0
    list_append_events = 0
    for prev, cur in zip(states, states[1:]):
        for field, prev_value in prev.items():
            if field in FRAMEWORK_KEYS or not isinstance(prev_value, list):
                continue
            cur_value = cur.get(field)
            if not isinstance(cur_value, list):
                if field in cur:
                    destructive_replacements += 1
                continue
            missing = count_missing_prior_entries(prev_value, cur_value)
            if missing:
                destructive_replacements += 1
            if len(cur_value) > len(prev_value) and not missing:
                list_append_events += 1

    durable_field_evolution = False
    if init_state and final_state:
        durable_field_evolution = (
            stable_json(state_without_framework(init_state))
            != stable_json(state_without_framework(final_state))
        )

    evidence = final_state.get("evidence_register")
    evidence_register_update = isinstance(evidence, list) and len(evidence) > 1
    if condition == "open" and not evidence_register_update:
        for key, value in final_state.items():
            if "evidence" in key.lower() and isinstance(value, list) and len(value) > 1:
                evidence_register_update = True

    prose_object_mismatch_count = 0
    previous_lengths: dict[str, int] = {}
    previous_state: dict | None = None
    for record in records:
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        response = record.get("response_text", "")
        if previous_state is not None and response_claims_update(response):
            if stable_json(state_without_framework(previous_state)) == stable_json(
                state_without_framework(state)
            ):
                prose_object_mismatch_count += 1
            elif "append" in response.lower():
                lengths = list_lengths(state)
                if not any(lengths.get(k, 0) > previous_lengths.get(k, 0) for k in lengths):
                    prose_object_mismatch_count += 1
        previous_state = state
        previous_lengths = list_lengths(state)

    deleted_or_missing_core_fields = [
        field for field in CORE_FIELDS if field not in final_state
    ]
    extra_fields_added = sorted(
        authored_keys(final_state) - set(LIST_FIELDS) - {"response"}
    )

    return {
        "init_valid": init_valid,
        "init_failure_reasons": init_failures,
        "core_field_presence": core_field_presence,
        "core_presence": core_presence,
        "type_preservation": type_preservation,
        "list_append_not_replace": list_append_events > 0,
        "list_append_event_count": list_append_events,
        "destructive_replacement_count": destructive_replacements,
        "prose_object_mismatch_count": prose_object_mismatch_count,
        "durable_field_evolution": durable_field_evolution,
        "evidence_register_update": evidence_register_update,
        "deleted_or_missing_core_fields": deleted_or_missing_core_fields,
        "extra_fields_added": extra_fields_added,
        "stop_reasons": [
            record.get("usage", {}).get("stop_reason")
            for record in records
            if record.get("usage", {}).get("stop_reason")
        ],
    }


def text_from_cycles(records: list[dict], cycles: set[int]) -> str:
    return "\n".join(
        record.get("response_text", "")
        for record in records
        if int(record.get("cycle", 0)) in cycles
    )


def count_patterns(text: str, patterns: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for pattern in patterns if re.search(pattern, lowered))


def score_behavior(records: list[dict]) -> dict:
    resume_text = text_from_cycles(records, {4})
    final_text = text_from_cycles(records, {5})
    challenge_text = text_from_cycles(records, {6})
    late_text = "\n".join([resume_text, final_text, challenge_text])

    goal_recovery_score = count_patterns(
        late_text,
        [
            r"wait time|wait times|lobby wait",
            r"privacy|resident privacy",
            r"north library",
            r"south center",
            r"west shelter",
            r"go/no-go|go / no-go|recommendation",
        ],
    )
    constraint_recovery_score = count_patterns(
        late_text,
        [
            r"\$18,?000|18k|budget",
            r"no paid weekend|weekend staffing",
            r"offline",
            r"four hours|4 hours",
            r"social security|ssn",
            r"no local|may not store|cannot store|not store",
            r"west shelter",
        ],
    )
    contradiction_handling_score = count_patterns(
        "\n".join([final_text, challenge_text]),
        [
            r"east clinic.*withdraw|withdraw.*east clinic|replace.*east",
            r"west shelter",
            r"no local|not store.*local|cannot store.*local|may not store",
            r"document.*defer|defer.*document|no document upload|upload.*connect",
            r"invalidated|assumption",
        ],
    )
    evidence_grounding_score = count_patterns(
        challenge_text,
        [
            r"privacy officer",
            r"east clinic.*withdraw|withdraw.*east clinic",
            r"offline.*remain|offline.*require",
            r"west shelter",
            r"evidence|because|changed.*because",
        ],
    )
    final_decision_quality_score = count_patterns(
        final_text,
        [
            r"go|no-go",
            r"pilot",
            r"five|5|bullet",
            r"budget|\$18,?000|18k",
            r"privacy",
            r"offline",
            r"west shelter",
        ],
    )
    false_patterns = [
        r"east clinic(?!.*withdraw)(?!.*replac)(?!.*invalid)",
        r"store.*document.*local",
        r"local.*document.*store",
        r"encrypted.*local",
        r"paid weekend",
        r"collect.*social security|collect.*ssn",
    ]
    false_assumption_count = count_patterns(late_text, false_patterns)
    rebriefing_needed = bool(
        re.search(
            r"please restate|need you to restate|i don't have.*context|"
            r"i do not have.*context|cannot resume",
            normalize(resume_text),
        )
    )
    delayed_challenge_accuracy = count_patterns(
        challenge_text,
        [
            r"local.*document|document.*local",
            r"east clinic|west shelter",
            r"offline",
            r"privacy officer",
            r"social security|ssn",
        ],
    )
    return {
        "goal_recovery_score": goal_recovery_score,
        "constraint_recovery_score": constraint_recovery_score,
        "contradiction_handling_score": contradiction_handling_score,
        "evidence_grounding_score": evidence_grounding_score,
        "final_decision_quality_score": final_decision_quality_score,
        "false_assumption_count": false_assumption_count,
        "rebriefing_needed": rebriefing_needed,
        "delayed_challenge_accuracy": delayed_challenge_accuracy,
    }


def score_log(path: Path, *, model: str, condition: str, replicate: int) -> dict:
    records = load_records(path)
    state_scores = score_state_mechanics(records, condition)
    behavior_scores = score_behavior(records)
    return {
        "model": model,
        "condition": condition,
        "replicate": replicate,
        "log_path": str(path.relative_to(PROJECT_ROOT)),
        "cycle_count": len(records),
        **state_scores,
        **behavior_scores,
    }


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def run_replicate(
    *,
    model: str,
    condition: str,
    replicate: int,
    api_key: str,
) -> dict:
    log_path = (
        EXP_DIR
        / f"{safe_model_name(model)}_{condition}_r{replicate:02d}.jsonl"
    )
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")

    session = make_session(
        model=model,
        condition=condition,
        replicate=replicate,
        log_path=log_path,
        api_key=api_key,
    )
    error = None
    for prompt in PROMPTS:
        try:
            session.exchange(prompt, force_memory=None)
        except Exception as exc:  # noqa: BLE001 -- failed cycles are data
            error = format_error(exc)
            break

    result = score_log(log_path, model=model, condition=condition, replicate=replicate)
    result["error"] = error
    result["censored"] = bool(
        error
        and any(term in error.lower() for term in ["429", "rate-limit", "length"])
    )
    return result


def summarize_group(group: list[dict]) -> dict:
    return {
        "n": len(group),
        "errors": sum(bool(r.get("error")) for r in group),
        "censored": sum(bool(r.get("censored")) for r in group),
        "init_valid": sum(bool(r.get("init_valid")) for r in group),
        "durable_field_evolution": sum(
            bool(r.get("durable_field_evolution")) for r in group
        ),
        "evidence_register_update": sum(
            bool(r.get("evidence_register_update")) for r in group
        ),
        "list_append_not_replace": sum(
            bool(r.get("list_append_not_replace")) for r in group
        ),
        "destructive_replacement_count": sum(
            int(r.get("destructive_replacement_count") or 0) for r in group
        ),
        "prose_object_mismatch_count": sum(
            int(r.get("prose_object_mismatch_count") or 0) for r in group
        ),
        "avg_goal_recovery_score": average(
            r.get("goal_recovery_score", 0) for r in group
        ),
        "avg_constraint_recovery_score": average(
            r.get("constraint_recovery_score", 0) for r in group
        ),
        "avg_contradiction_handling_score": average(
            r.get("contradiction_handling_score", 0) for r in group
        ),
        "avg_final_decision_quality_score": average(
            r.get("final_decision_quality_score", 0) for r in group
        ),
        "false_assumption_count": sum(
            int(r.get("false_assumption_count") or 0) for r in group
        ),
        "rebriefing_needed": sum(bool(r.get("rebriefing_needed")) for r in group),
    }


def average(values: Any) -> float | None:
    items = list(values)
    if not items:
        return None
    return round(sum(float(value or 0) for value in items) / len(items), 3)


def aggregate(results: list[dict]) -> dict:
    by_condition = {
        condition: summarize_group([r for r in results if r["condition"] == condition])
        for condition in CONDITIONS
    }
    by_model_condition = {}
    for model in MODELS:
        for condition in CONDITIONS:
            group = [
                r
                for r in results
                if r["model"] == model and r["condition"] == condition
            ]
            by_model_condition[f"{model}|{condition}"] = summarize_group(group)
    return {
        "overall": summarize_group(results),
        "by_condition": by_condition,
        "by_model_condition": by_model_condition,
    }


def write_results(results: list[dict]) -> None:
    payload = {
        "models": MODELS,
        "conditions": CONDITIONS,
        "n_replicates": N_REPLICATES,
        "max_tokens": MAX_TOKENS,
        "task_prompts": PROMPTS,
        "results": results,
        "summary": aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def run_panel() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")

    results: list[dict] = []
    for model in MODELS:
        for condition in CONDITIONS:
            for replicate in range(1, N_REPLICATES + 1):
                print(f"{model} {condition} r{replicate}", flush=True)
                result = run_replicate(
                    model=model,
                    condition=condition,
                    replicate=replicate,
                    api_key=api_key,
                )
                results.append(result)
                write_results(results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


def rescore_existing() -> None:
    results: list[dict] = []
    for model in MODELS:
        for condition in CONDITIONS:
            for replicate in range(1, N_REPLICATES + 1):
                path = (
                    EXP_DIR
                    / f"{safe_model_name(model)}_{condition}_r{replicate:02d}.jsonl"
                )
                if not path.exists():
                    continue
                result = score_log(
                    path,
                    model=model,
                    condition=condition,
                    replicate=replicate,
                )
                result["error"] = None
                result["censored"] = False
                results.append(result)
    write_results(results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"rescored {len(results)} logs")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="Recompute results.json from existing logs without model calls.",
    )
    args = parser.parse_args()
    if args.rescore:
        rescore_existing()
    else:
        run_panel()


if __name__ == "__main__":
    main()
