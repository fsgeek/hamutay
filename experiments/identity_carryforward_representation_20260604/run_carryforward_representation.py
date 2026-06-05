"""Run and score the preregistered carry-forward representation experiment."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from hamutay.taste_open import (
    OPEN_SCHEMA,
    OpenAITasteBackend,
    _SYSTEM_PROMPT,
    _apply_updates,
)

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[1]

MODEL = "mistralai/mistral-small-2603"
MODELS = [MODEL]
CONDITIONS = [
    "no_carry",
    "raw_state",
    "self_summary",
    "harness_summary",
    "transcript_summary",
]
N_REPLICATES = 4
MAX_TOKENS = 4096
CARRY_FORWARD_BUDGET_CHARS = 2400

CORE_FIELDS = [
    "current_goals",
    "working_claims",
    "evidence_register",
    "open_questions",
    "next_actions",
    "continuity_notes",
    "observed_failure_modes",
]
FRAMEWORK_KEYS = {"cycle", "_activity_log"}

UNIFIED_SCHEMA = {
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
                "this empty unless you intentionally shed a field."
            ),
        },
        "carry_forward_summary": {
            "type": "string",
            "description": (
                "A compact self-authored summary for a possible future cycle. "
                "Preserve task facts, revisions, evidence, uncertainty, and "
                "known invalidated assumptions. Do not invent details."
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
    "required": [
        "response",
        "deleted_regions",
        "carry_forward_summary",
        *CORE_FIELDS,
    ],
    "additionalProperties": True,
}

UNIFIED_PREFIX = """\
You are participating in a registered carry-forward representation experiment.

Every condition uses the same exchange machinery and the same output schema.
Each cycle, produce a structured object with response, carry_forward_summary,
and the core fields:
current_goals, working_claims, evidence_register, open_questions, next_actions,
continuity_notes, observed_failure_modes.

The only experimental difference is the prior-context representation, if any,
shown under "Prior Context Representation" below. Treat that representation as
fallible. Preserve source/evidence distinctions. Do not invent task facts,
budget figures, outcomes, implementation details, or site changes.

If prior context is absent, do not ask the user to restate facts unless the
current prompt truly lacks them. State uncertainty explicitly."""

PROMPTS = [
    """\
Initialize your state for this registered carry-forward representation run.

No task facts have been provided yet. Prepare to track goals, constraints,
evidence, open questions, next actions, continuity notes, observed failure
modes, and a compact carry_forward_summary for a multi-cycle planning task.

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

Create an initial plan and update state with the goals, constraints,
assumptions, evidence, open questions, next actions, and carry-forward summary.""",
    """\
Contradictory update.

The privacy officer has now ruled that pilot kiosks may not store resident
documents locally at all, even encrypted. The offline-operation requirement
still remains. Also, East Clinic has withdrawn from the pilot and must be
replaced by West Shelter.

Update the plan and state. Identify which assumptions from the initial plan are
invalidated, what evidence caused the change, and what the current plan should
do instead.""",
    """\
Interruption/resumption test.

Assume your working context was interrupted. Resume using whatever prior
context representation you have been given. Do not ask me to restate the task.

Report the current goals, active constraints, invalidated assumptions, and next
actions. If anything is uncertain, say what is uncertain and why; do not ask
for information already present in the task history or prior context.""",
    """\
Final decision.

Make the concrete go/no-go recommendation and give the revised pilot plan in
five bullets or fewer. Ground the decision in the current constraints and the
contradictory update. Update state and carry_forward_summary accordingly.""",
    """\
Delayed challenge.

What changed since the initial plan, why did it change, and what evidence
supports the change? Answer from continuity, not from generic planning advice.
Update state with the final evidence trail and any remaining open questions.""",
]

STATIC_TASK_FACTS_BY_CYCLE = {
    2: [
        "Pilot task: six-week mobile document-intake kiosk pilot for a city benefits office.",
        "Goals: reduce lobby wait times; preserve resident privacy; cover North Library, East Clinic, South Center; produce go/no-go recommendation.",
        "Constraints: budget <= $18,000; no paid weekend staffing; kiosks support offline operation for at least four hours; no Social Security number collection.",
    ],
    3: [
        "New evidence: privacy officer ruled kiosks may not store resident documents locally at all, even encrypted.",
        "New evidence: offline-operation requirement still remains.",
        "New evidence: East Clinic withdrew and must be replaced by West Shelter.",
    ],
}


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


def make_backend(api_key: str) -> SchemaOpenAIBackend:
    return SchemaOpenAIBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": "hamutay/carry-forward-representation",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
        think_schema=UNIFIED_SCHEMA,
    )


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def compact_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def state_without_framework(state: dict) -> dict:
    return {k: v for k, v in state.items() if k not in FRAMEWORK_KEYS}


def authored_keys(state: dict) -> set[str]:
    return set(state_without_framework(state))


def normalize(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def cap_text(text: str, budget: int = CARRY_FORWARD_BUDGET_CHARS) -> tuple[str, bool]:
    if len(text) <= budget:
        return text, False
    marker = "\n[truncated]"
    return text[: budget - len(marker)].rstrip() + marker, True


def field_count_summary(state: dict | None) -> list[str]:
    if not state:
        return []
    lines = []
    for field in CORE_FIELDS:
        value = state.get(field)
        if isinstance(value, list):
            lines.append(f"{field}: {len(value)} entries")
        elif field in state:
            lines.append(f"{field}: non-list value")
    if isinstance(state.get("carry_forward_summary"), str):
        lines.append(
            "carry_forward_summary: "
            + " ".join(state["carry_forward_summary"].split())[:500]
        )
    return lines


def prompt_facts_before(cycle: int) -> list[str]:
    facts: list[str] = []
    for fact_cycle in sorted(STATIC_TASK_FACTS_BY_CYCLE):
        if fact_cycle < cycle:
            facts.extend(STATIC_TASK_FACTS_BY_CYCLE[fact_cycle])
    return facts


def response_excerpt(response: str, limit: int = 500) -> str:
    compact = " ".join(response.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def build_harness_summary(cycle: int, prior_state: dict | None) -> str:
    parts = [
        "Harness-authored summary. Not model-authored.",
        f"Cycle now: {cycle} of {len(PROMPTS)}.",
    ]
    facts = prompt_facts_before(cycle)
    if facts:
        parts.append("Known prompt facts before this cycle:")
        parts.extend(f"- {fact}" for fact in facts)
    field_lines = field_count_summary(prior_state)
    if field_lines:
        parts.append("Prior logged state field summary:")
        parts.extend(f"- {line}" for line in field_lines)
    return "\n".join(parts)


def build_transcript_summary(cycle: int, history: list[dict]) -> str:
    parts = [
        "Visible-transcript summary. Uses prior visible responses only.",
        f"Cycle now: {cycle} of {len(PROMPTS)}.",
    ]
    visible = [
        (record.get("cycle"), record.get("response_text", ""))
        for record in history
        if record.get("response_text")
    ]
    if visible:
        parts.append("Prior visible response excerpts:")
        for prior_cycle, response in visible[-4:]:
            parts.append(f"- Cycle {prior_cycle}: {response_excerpt(response)}")
    else:
        parts.append("No prior visible responses.")
    return "\n".join(parts)


def prior_context_for(
    condition: str,
    cycle: int,
    prior_state: dict | None,
    history: list[dict],
) -> tuple[str, str, bool]:
    if cycle == 1:
        return "none", "No prior context exists; this is cycle 1.", False

    if condition == "no_carry":
        return "none", "No prior context is supplied in this condition.", False
    if condition == "raw_state":
        payload = compact_json(state_without_framework(prior_state or {}))
        capped, truncated = cap_text(payload)
        return "raw_state", capped, truncated
    if condition == "self_summary":
        summary = ""
        if prior_state and isinstance(prior_state.get("carry_forward_summary"), str):
            summary = prior_state["carry_forward_summary"]
        capped, truncated = cap_text(summary or "(no self-summary available)")
        return "self_summary", capped, truncated
    if condition == "harness_summary":
        capped, truncated = cap_text(build_harness_summary(cycle, prior_state))
        return "harness_summary", capped, truncated
    if condition == "transcript_summary":
        capped, truncated = cap_text(build_transcript_summary(cycle, history))
        return "transcript_summary", capped, truncated
    raise ValueError(f"unknown condition: {condition}")


def build_messages(
    condition: str,
    cycle: int,
    user_message: str,
    prior_state: dict | None,
    history: list[dict],
) -> tuple[list[dict], str, dict]:
    context_type, context_text, truncated = prior_context_for(
        condition, cycle, prior_state, history
    )
    system = "\n".join(
        [
            UNIFIED_PREFIX,
            "",
            _SYSTEM_PROMPT,
            "",
            "## Prior Context Representation",
            f"condition: {condition}",
            f"representation_type: {context_type}",
            f"cycle: {cycle}",
            f"budget_chars: {CARRY_FORWARD_BUDGET_CHARS}",
            f"truncated: {str(truncated).lower()}",
            "",
            context_text,
        ]
    )
    meta = {
        "condition": condition,
        "representation_type": context_type,
        "carry_forward_text": context_text,
        "carry_forward_chars": 0 if context_type == "none" else len(context_text),
        "carry_forward_truncated": truncated,
    }
    return [{"role": "user", "content": user_message}], system, meta


def append_log(
    *,
    path: Path,
    model: str,
    condition: str,
    replicate: int,
    cycle: int,
    user_message: str,
    system_prompt: str,
    prior_state: dict | None,
    raw_output: dict,
    state: dict,
    usage: dict,
    context_meta: dict,
) -> dict:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle": cycle,
        "record_id": str(uuid4()),
        "experiment_label": (
            f"identity_carryforward_representation_{safe_model_name(model)}_"
            f"{condition}_r{replicate:02d}"
        ),
        "model": model,
        "condition": condition,
        "user_message": user_message,
        "system_prompt": system_prompt,
        "prior_state": prior_state,
        "prior_context": context_meta,
        "raw_output": raw_output,
        "deleted_regions": raw_output.get("deleted_regions", []),
        "response_text": raw_output.get("response", ""),
        "state": state,
        "usage": usage,
        "state_token_estimate": len(json.dumps(state)) // 4 if state else 0,
        "system_prompt_tokens": len(system_prompt) // 4,
        "n_top_level_keys": len([k for k in state if k != "cycle"]),
        "top_level_keys": sorted(k for k in state if k != "cycle"),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return record


def run_exchange_path(
    *,
    model: str,
    condition: str,
    replicate: int,
    api_key: str,
    log_path: Path,
) -> str | None:
    backend = make_backend(api_key)
    prior_state: dict | None = None
    history: list[dict] = []
    for cycle, prompt in enumerate(PROMPTS, start=1):
        messages, system, context_meta = build_messages(
            condition, cycle, prompt, prior_state, history
        )
        try:
            result = backend.call(
                model=model,
                system=system,
                messages=messages,
                experiment_label=(
                    f"identity_carryforward_representation_{safe_model_name(model)}_"
                    f"{condition}_r{replicate:02d}"
                ),
                extra_tools=None,
                tool_executor=None,
            )
            raw_output = result.raw_output
            prior_snapshot = json.loads(json.dumps(prior_state)) if prior_state else None
            state = _apply_updates(prior_state, raw_output, cycle)
            record = append_log(
                path=log_path,
                model=model,
                condition=condition,
                replicate=replicate,
                cycle=cycle,
                user_message=prompt,
                system_prompt=system,
                prior_state=prior_snapshot,
                raw_output=raw_output,
                state=state,
                usage={
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "cache_read_input_tokens": result.cache_read_tokens,
                    "cache_creation_input_tokens": result.cache_creation_tokens,
                    "stop_reason": result.stop_reason,
                },
                context_meta=context_meta,
            )
            prior_state = state
            history.append(record)
        except Exception as exc:  # noqa: BLE001 -- failed cycles are data
            return format_error(exc)
    return None


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


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
            "state",
            "evidence",
            "next action",
            "summary",
        )
    )


def score_state_mechanics(records: list[dict]) -> dict:
    states = [
        record.get("state")
        for record in records
        if isinstance(record.get("state"), dict)
    ]
    states = [s for s in states if isinstance(s, dict)]
    init_state = states[0] if states else {}
    final_state = states[-1] if states else {}

    init_failures = []
    for field in [*CORE_FIELDS, "carry_forward_summary"]:
        if field not in init_state:
            init_failures.append(f"{field}_missing")
        elif field in CORE_FIELDS and not isinstance(init_state.get(field), list):
            init_failures.append(f"{field}_not_list")
        elif field == "carry_forward_summary" and not isinstance(
            init_state.get(field), str
        ):
            init_failures.append("carry_forward_summary_not_string")
    init_valid = not init_failures

    core_presence = {
        field: field in final_state and isinstance(final_state.get(field), list)
        for field in CORE_FIELDS
    }
    core_field_presence = sum(core_presence.values())

    type_checks = 0
    type_passes = 0
    for state in states:
        for field in CORE_FIELDS:
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

    evidence = final_state.get("evidence_register")
    evidence_register_update = isinstance(evidence, list) and len(evidence) > 1

    prose_object_mismatch_count = 0
    previous_state: dict | None = None
    for record in records:
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        response = record.get("response_text", "")
        if previous_state is not None and response_claims_update(response):
            if stable_json(state_without_framework(previous_state)) == stable_json(
                state_without_framework(state)
            ):
                prose_object_mismatch_count += 1
        previous_state = state

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
        "evidence_register_update": evidence_register_update,
        "extra_fields_added": sorted(
            authored_keys(final_state)
            - set(CORE_FIELDS)
            - {"response", "deleted_regions", "carry_forward_summary"}
        ),
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


def count_invented_dollar_amounts(text: str) -> int:
    count = 0
    for match in re.finditer(r"\$\s*([0-9][0-9,]*(?:\.\d+)?)", text):
        amount = match.group(1).replace(",", "")
        if amount not in {"18000", "18"}:
            count += 1
    return count


def contamination_scores(late_text: str) -> dict:
    lowered = late_text.lower()
    site_drift_count = count_patterns(
        lowered,
        [
            r"north center",
            r"\btwo sites\b|\btwo-site\b|\b2 sites\b",
            r"north library and west shelter only",
            r"north library and south center only",
            r"drop.*south center|exclude.*south center",
            r"east clinic(?![^.\n]*(withdraw|replac|invalid|drop|exclud))",
        ],
    )
    storage_contradiction_count = count_patterns(
        lowered,
        [
            r"transient cache|transient-cache",
            r"local cache|local caching",
            r"persistent cache|persistent local",
            r"store.*document.*local",
            r"local.*document.*stor",
            r"encrypted local|local encrypted",
            r"buffer.*document|document.*buffer",
            r"offline buffer",
        ],
    )
    invented_budget_count = count_invented_dollar_amounts(late_text)
    invented_scope_count = count_patterns(
        lowered,
        [
            r"four-week|four weeks|4-week|4 weeks",
            r"two-week|two weeks|2-week|2 weeks",
            r"city-?wide rollout",
            r"pilot findings|pilot outcomes|outcomes indicated",
            r"\b20\s*%|\b15\s*%|\bzero privacy incidents\b",
            r"thermal printer|thermal printers",
        ],
    )
    unsupported_detail_count = count_patterns(
        lowered,
        [
            r"android",
            r"mdm",
            r"soc 2|soc2|hipaa",
            r"4g|5g|cellular",
            r"factory reset",
            r"vendor",
            r"ada",
            r"ruggedized",
            r"hotspot",
            r"tablet",
            r"printer",
            r"sms|email confirmation",
        ],
    )
    false_assumption_count = (
        site_drift_count
        + storage_contradiction_count
        + invented_budget_count
        + invented_scope_count
        + unsupported_detail_count
    )
    return {
        "site_drift_count": site_drift_count,
        "storage_contradiction_count": storage_contradiction_count,
        "invented_budget_count": invented_budget_count,
        "invented_scope_count": invented_scope_count,
        "unsupported_detail_count": unsupported_detail_count,
        "false_assumption_count": false_assumption_count,
    }


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
    contamination = contamination_scores(late_text)
    return {
        "goal_recovery_score": goal_recovery_score,
        "constraint_recovery_score": constraint_recovery_score,
        "contradiction_handling_score": contradiction_handling_score,
        "evidence_grounding_score": evidence_grounding_score,
        "final_decision_quality_score": final_decision_quality_score,
        "rebriefing_needed": rebriefing_needed,
        "delayed_challenge_accuracy": delayed_challenge_accuracy,
        **contamination,
    }


def carry_forward_metrics(records: list[dict], behavior_scores: dict) -> dict:
    chars = sum(
        int(record.get("prior_context", {}).get("carry_forward_chars") or 0)
        for record in records
    )
    truncated = sum(
        bool(record.get("prior_context", {}).get("carry_forward_truncated"))
        for record in records
    )
    recovery = sum(
        int(behavior_scores.get(key) or 0)
        for key in [
            "goal_recovery_score",
            "constraint_recovery_score",
            "contradiction_handling_score",
            "evidence_grounding_score",
            "final_decision_quality_score",
            "delayed_challenge_accuracy",
        ]
    )
    contamination = int(behavior_scores.get("false_assumption_count") or 0)
    denom = chars / 1000 if chars else None
    return {
        "carry_forward_chars": chars,
        "carry_forward_truncated_count": truncated,
        "recovery_total": recovery,
        "contamination_total": contamination,
        "recovery_per_1k_chars": round(recovery / denom, 3) if denom else None,
        "contamination_per_1k_chars": (
            round(contamination / denom, 3) if denom else None
        ),
    }


def score_log(path: Path, *, model: str, condition: str, replicate: int) -> dict:
    records = load_records(path)
    state_scores = score_state_mechanics(records)
    behavior_scores = score_behavior(records)
    carry_scores = carry_forward_metrics(records, behavior_scores)
    return {
        "model": model,
        "condition": condition,
        "replicate": replicate,
        "log_path": str(path.relative_to(PROJECT_ROOT)),
        "cycle_count": len(records),
        **state_scores,
        **behavior_scores,
        **carry_scores,
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
        EXP_DIR / f"{safe_model_name(model)}_{condition}_r{replicate:02d}.jsonl"
    )
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")

    error = run_exchange_path(
        model=model,
        condition=condition,
        replicate=replicate,
        api_key=api_key,
        log_path=log_path,
    )
    result = score_log(log_path, model=model, condition=condition, replicate=replicate)
    result["error"] = error
    result["censored"] = bool(
        error
        and any(term in error.lower() for term in ["429", "rate-limit", "length"])
    )
    return result


def average(values: Any) -> float | None:
    items = list(values)
    if not items:
        return None
    return round(sum(float(value or 0) for value in items) / len(items), 3)


def summarize_group(group: list[dict]) -> dict:
    return {
        "n": len(group),
        "errors": sum(bool(r.get("error")) for r in group),
        "censored": sum(bool(r.get("censored")) for r in group),
        "init_valid": sum(bool(r.get("init_valid")) for r in group),
        "evidence_register_update": sum(
            bool(r.get("evidence_register_update")) for r in group
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
        "avg_evidence_grounding_score": average(
            r.get("evidence_grounding_score", 0) for r in group
        ),
        "avg_final_decision_quality_score": average(
            r.get("final_decision_quality_score", 0) for r in group
        ),
        "avg_delayed_challenge_accuracy": average(
            r.get("delayed_challenge_accuracy", 0) for r in group
        ),
        "false_assumption_count": sum(
            int(r.get("false_assumption_count") or 0) for r in group
        ),
        "unsupported_detail_count": sum(
            int(r.get("unsupported_detail_count") or 0) for r in group
        ),
        "site_drift_count": sum(int(r.get("site_drift_count") or 0) for r in group),
        "storage_contradiction_count": sum(
            int(r.get("storage_contradiction_count") or 0) for r in group
        ),
        "invented_budget_count": sum(
            int(r.get("invented_budget_count") or 0) for r in group
        ),
        "invented_scope_count": sum(
            int(r.get("invented_scope_count") or 0) for r in group
        ),
        "rebriefing_needed": sum(bool(r.get("rebriefing_needed")) for r in group),
        "avg_carry_forward_chars": average(
            r.get("carry_forward_chars", 0) for r in group
        ),
        "carry_forward_truncated_count": sum(
            int(r.get("carry_forward_truncated_count") or 0) for r in group
        ),
        "avg_recovery_total": average(r.get("recovery_total", 0) for r in group),
        "avg_contamination_total": average(
            r.get("contamination_total", 0) for r in group
        ),
        "avg_recovery_per_1k_chars": average(
            r.get("recovery_per_1k_chars")
            for r in group
            if r.get("recovery_per_1k_chars") is not None
        ),
        "avg_contamination_per_1k_chars": average(
            r.get("contamination_per_1k_chars")
            for r in group
            if r.get("contamination_per_1k_chars") is not None
        ),
    }


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
        "carry_forward_budget_chars": CARRY_FORWARD_BUDGET_CHARS,
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
