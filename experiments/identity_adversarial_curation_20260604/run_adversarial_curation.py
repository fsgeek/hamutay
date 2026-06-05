"""Run and score the preregistered identity adversarial curation experiment."""

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
)

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[1]

MODEL = "mistralai/mistral-small-2603"
MODELS = [MODEL]
CONDITIONS = [
    "raw_state",
    "curator_summary",
    "critic_filtered_summary",
]
N_REPLICATES = 4
MAX_TOKENS = 4096
CURATION_MAX_TOKENS = 2048
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
PROTOCOL_FIELDS = {"response", "updated_regions", "deleted_regions"}

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

CURATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string",
            "description": "Brief status note for the log.",
        },
        "carry_forward_summary": {
            "type": "string",
            "description": "Compact summary to inject into the next main cycle.",
        },
        "supported_facts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Prompt-supported or strongly state-supported facts preserved.",
        },
        "uncertain_claims": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Claims that should not be treated as prompt facts.",
        },
        "invalidated_claims": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Prior assumptions contradicted by later prompt evidence.",
        },
    },
    "required": [
        "response",
        "carry_forward_summary",
        "supported_facts",
        "uncertain_claims",
        "invalidated_claims",
    ],
    "additionalProperties": False,
}

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string",
            "description": "Brief status note for the log.",
        },
        "filtered_summary": {
            "type": "string",
            "description": "Critic-filtered summary to inject into the next main cycle.",
        },
        "removed_or_demoted_claims": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Unsupported, contradicted, or over-specific claims removed or demoted.",
        },
        "preserved_continuity": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Supported continuity facts deliberately preserved.",
        },
        "risk_notes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Remaining contamination risks.",
        },
    },
    "required": [
        "response",
        "filtered_summary",
        "removed_or_demoted_claims",
        "preserved_continuity",
        "risk_notes",
    ],
    "additionalProperties": False,
}

UNIFIED_PREFIX = """\
You are participating in a registered adversarial-curation experiment.

Every condition uses the same exchange machinery and the same output schema.
Each cycle, produce a structured object with response, carry_forward_summary,
and the core fields:
current_goals, working_claims, evidence_register, open_questions, next_actions,
continuity_notes, observed_failure_modes.

The experimental difference is the prior-context representation shown below.
Treat prior context as fallible. Preserve source/evidence distinctions. Do not
invent task facts, budget figures, outcomes, implementation details, or site
changes.

Prompt facts are authoritative. Model claims and inferences are provisional
unless directly supported. Invalidated assumptions must not remain active plan
assumptions.

If prior context is absent, do not ask the user to restate facts unless the
current prompt truly lacks them. State uncertainty explicitly."""

PROMPTS = [
    """\
Initialize your state for this registered adversarial-curation run.

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


def make_backend(
    api_key: str,
    *,
    schema: dict = UNIFIED_SCHEMA,
    max_tokens: int = MAX_TOKENS,
    title: str = "hamutay/identity-adversarial-curation",
) -> SchemaOpenAIBackend:
    return SchemaOpenAIBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=max_tokens,
        extra_headers={
            "X-Title": title,
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
        think_schema=schema,
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


def build_uncertainty_summary(cycle: int, prior_state: dict | None) -> str:
    parts = [
        "Harness-authored summary with source/status labels.",
        f"Cycle now: {cycle} of {len(PROMPTS)}.",
        "Interpretation rule: prompt_fact > invalidated_assumption > "
        "model_claim/inference. Invalidated assumptions are not active.",
    ]
    facts = prompt_facts_before(cycle)
    if facts:
        parts.append("prompt_fact:")
        parts.extend(f"- {fact}" for fact in facts)
    if cycle > 3:
        parts.append("invalidated_assumption:")
        parts.append(
            "- East Clinic remains an active pilot site; it withdrew and was "
            "replaced by West Shelter."
        )
        parts.append(
            "- Kiosks may store resident documents locally, even encrypted; "
            "the privacy officer prohibited all local document storage."
        )
    if prior_state and isinstance(prior_state.get("open_questions"), list):
        questions = prior_state.get("open_questions", [])[:4]
        if questions:
            parts.append("unresolved_question:")
            for question in questions:
                parts.append(f"- {response_excerpt(stable_json(question), 220)}")
    field_lines = field_count_summary(prior_state)
    if field_lines:
        parts.append("model_claim_field_summary:")
        parts.extend(f"- {line}" for line in field_lines)
    return "\n".join(parts)


RAW_STATE_DECAY_PREFACE = """\
Metadata preface for raw state:
- prompt_fact: facts supplied by the current or prior task prompts are authoritative.
- model_claim: content inside prior raw state is provisional unless directly tied to prompt_fact evidence.
- invalidated_assumption: East Clinic as active site and any local document storage are invalidated after cycle 3.
- decay_rule: do not reuse stale implementation details, budget line items, hardware choices, staffing assumptions, or success outcomes unless prompt facts supplied them.
- uncertainty_rule: if a prior claim lacks prompt evidence, mark it uncertain instead of using it as an active plan fact.
"""


def prior_context_for(
    condition: str,
    cycle: int,
    prior_state: dict | None,
    history: list[dict],
    carry_context: dict | None,
) -> tuple[str, str, bool]:
    if cycle == 1:
        return "none", "No prior context exists; this is cycle 1.", False

    if condition == "raw_state":
        payload = compact_json(state_without_framework(prior_state or {}))
        capped, truncated = cap_text(payload)
        return "raw_state", capped, truncated
    if condition in {"curator_summary", "critic_filtered_summary"}:
        payload = (carry_context or {}).get("summary", "")
        if not payload:
            payload = "No curator summary was available; use current prompt facts only."
        capped, truncated = cap_text(payload)
        return condition, capped, truncated
    raise ValueError(f"unknown condition: {condition}")


def curation_guidance_for(condition: str) -> str:
    if condition == "raw_state":
        return """\
condition: raw_state
prior_context_source: compact JSON form of the previous raw state object.
Treat prior state as useful but fallible. Do not promote unsupported prior
claims to task facts."""
    if condition == "curator_summary":
        return """\
condition: curator_summary
prior_context_source: a separate continuity-curator call from the previous
cycle. Treat it as a compact continuity aid, not as authoritative evidence."""
    if condition == "critic_filtered_summary":
        return """\
condition: critic_filtered_summary
prior_context_source: a continuity-curator draft filtered by a separate
contamination critic. Treat it as a compact continuity aid with unsupported
claims removed or demoted, not as authoritative evidence."""
    raise ValueError(f"unknown condition: {condition}")


def build_messages(
    condition: str,
    cycle: int,
    user_message: str,
    prior_state: dict | None,
    history: list[dict],
    carry_context: dict | None,
) -> tuple[list[dict], str, dict]:
    context_type, context_text, truncated = prior_context_for(
        condition, cycle, prior_state, history, carry_context
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
            "",
            "## Curation Condition",
            curation_guidance_for(condition),
        ]
    )
    meta = {
        "condition": condition,
        "representation_type": context_type,
        "carry_forward_text": context_text,
        "carry_forward_chars": 0 if context_type == "none" else len(context_text),
        "carry_forward_truncated": truncated,
        "curation_record_id": (carry_context or {}).get("record_id"),
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
    update_meta: dict,
    curation_meta: dict | None,
) -> dict:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle": cycle,
        "record_id": str(uuid4()),
        "experiment_label": (
            f"identity_adversarial_curation_{safe_model_name(model)}_"
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
        "update_protocol": update_meta,
        "post_cycle_curation": curation_meta,
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


def apply_update_policy(
    prior_state: dict | None,
    raw_output: dict,
    cycle: int,
    condition: str,
) -> tuple[dict, dict]:
    deleted = set(raw_output.get("deleted_regions", []))
    updated = set(raw_output.keys()) - PROTOCOL_FIELDS
    overlap = deleted & updated
    if overlap:
        raise ValueError(
            f"cycle {cycle}: deleted_regions overlaps updates: {sorted(overlap)}. "
            "A key cannot be simultaneously deleted and updated in the same cycle."
        )

    state = dict(prior_state) if prior_state is not None else {}
    state["cycle"] = cycle

    for key in updated:
        state[key] = raw_output[key]

    for key in deleted:
        state.pop(key, None)

    return state, {
        "condition": condition,
        "merge_policy": "strict_overlap_failure",
        "deleted_regions": sorted(deleted),
        "updated_regions": sorted(updated),
        "delete_update_overlap": sorted(overlap),
        "normalized_overlap": [],
        "normalization_applied": False,
    }


def known_prompt_facts_for_next_cycle(cycle: int) -> list[str]:
    facts: list[str] = []
    for fact_cycle in sorted(STATIC_TASK_FACTS_BY_CYCLE):
        if fact_cycle <= cycle:
            facts.extend(STATIC_TASK_FACTS_BY_CYCLE[fact_cycle])
    return facts


def build_curator_payload(
    *,
    cycle: int,
    prompt: str,
    prior_state: dict | None,
    state: dict,
    raw_output: dict,
    response_text: str,
) -> str:
    payload = {
        "role": "continuity_curator",
        "cycle_completed": cycle,
        "next_cycle": cycle + 1 if cycle < len(PROMPTS) else None,
        "known_prompt_facts": known_prompt_facts_for_next_cycle(cycle),
        "current_user_prompt": prompt,
        "prior_state": prior_state,
        "main_agent_raw_output": raw_output,
        "main_agent_visible_response": response_text,
        "merged_state": state,
        "instructions": [
            "Preserve task continuity for the next cycle.",
            "Prefer prompt facts over model claims.",
            "Do not invent budget numbers, implementation details, outcomes, vendors, or site changes.",
            "Explicitly mark uncertain and invalidated claims.",
            "Keep the carry_forward_summary compact and useful.",
        ],
    }
    return stable_json(payload)


def build_critic_payload(
    *,
    cycle: int,
    curator_output: dict,
) -> str:
    payload = {
        "role": "contamination_critic",
        "cycle_completed": cycle,
        "next_cycle": cycle + 1 if cycle < len(PROMPTS) else None,
        "known_prompt_facts": known_prompt_facts_for_next_cycle(cycle),
        "curator_output": curator_output,
        "instructions": [
            "Attack unsupported, contradicted, stale, or over-specific claims.",
            "Preserve supported task continuity.",
            "Remove or demote invented budget line items, hardware choices, staffing assumptions, compliance claims, success metrics, and site changes not supplied by prompt facts.",
            "The filtered_summary should be compact and directly useful for the next main cycle.",
        ],
    }
    return stable_json(payload)


def call_structured_agent(
    *,
    backend: SchemaOpenAIBackend,
    model: str,
    system: str,
    payload: str,
    experiment_label: str,
) -> tuple[dict, dict]:
    result = backend.call(
        model=model,
        system=system,
        messages=[{"role": "user", "content": payload}],
        experiment_label=experiment_label,
        extra_tools=None,
        tool_executor=None,
    )
    usage = {
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cache_read_input_tokens": result.cache_read_tokens,
        "cache_creation_input_tokens": result.cache_creation_tokens,
        "stop_reason": result.stop_reason,
    }
    return result.raw_output, usage


def build_post_cycle_curation(
    *,
    model: str,
    condition: str,
    replicate: int,
    cycle: int,
    prompt: str,
    prior_state: dict | None,
    state: dict,
    raw_output: dict,
    response_text: str,
    curator_backend: SchemaOpenAIBackend,
    critic_backend: SchemaOpenAIBackend,
) -> tuple[dict | None, dict | None]:
    if condition == "raw_state":
        return None, None

    curator_system = """\
You are the continuity curator in a registered adversarial-curation experiment.
Your job is to preserve useful continuity for the next cycle while separating
prompt facts from model claims. Call think_and_respond exactly once."""
    curator_payload = build_curator_payload(
        cycle=cycle,
        prompt=prompt,
        prior_state=prior_state,
        state=state,
        raw_output=raw_output,
        response_text=response_text,
    )
    curator_output, curator_usage = call_structured_agent(
        backend=curator_backend,
        model=model,
        system=curator_system,
        payload=curator_payload,
        experiment_label=(
            f"identity_adversarial_curation_curator_{safe_model_name(model)}_"
            f"{condition}_r{replicate:02d}_c{cycle:02d}"
        ),
    )
    draft_summary = str(curator_output.get("carry_forward_summary", ""))
    curation_meta = {
        "record_id": str(uuid4()),
        "condition": condition,
        "cycle": cycle,
        "curator_output": curator_output,
        "curator_usage": curator_usage,
        "critic_output": None,
        "critic_usage": None,
        "summary_source": "curator",
        "summary": draft_summary,
        "summary_chars": len(draft_summary),
    }

    if condition == "critic_filtered_summary":
        critic_system = """\
You are the contamination critic in a registered adversarial-curation
experiment. Your job is to attack the curator's draft summary for unsupported,
contradicted, stale, or over-specific claims while preserving supported
continuity. Call think_and_respond exactly once."""
        critic_payload = build_critic_payload(
            cycle=cycle,
            curator_output=curator_output,
        )
        critic_output, critic_usage = call_structured_agent(
            backend=critic_backend,
            model=model,
            system=critic_system,
            payload=critic_payload,
            experiment_label=(
                f"identity_adversarial_curation_critic_{safe_model_name(model)}_"
                f"{condition}_r{replicate:02d}_c{cycle:02d}"
            ),
        )
        filtered_summary = str(critic_output.get("filtered_summary", ""))
        curation_meta.update(
            {
                "critic_output": critic_output,
                "critic_usage": critic_usage,
                "summary_source": "critic",
                "summary": filtered_summary,
                "summary_chars": len(filtered_summary),
            }
        )

    carry_context = {
        "record_id": curation_meta["record_id"],
        "summary": curation_meta["summary"],
        "summary_source": curation_meta["summary_source"],
        "cycle": cycle,
    }
    return curation_meta, carry_context


def run_exchange_path(
    *,
    model: str,
    condition: str,
    replicate: int,
    api_key: str,
    log_path: Path,
) -> str | None:
    backend = make_backend(api_key)
    curator_backend = make_backend(
        api_key,
        schema=CURATOR_SCHEMA,
        max_tokens=CURATION_MAX_TOKENS,
        title="hamutay/identity-adversarial-curation-curator",
    )
    critic_backend = make_backend(
        api_key,
        schema=CRITIC_SCHEMA,
        max_tokens=CURATION_MAX_TOKENS,
        title="hamutay/identity-adversarial-curation-critic",
    )
    prior_state: dict | None = None
    carry_context: dict | None = None
    history: list[dict] = []
    for cycle, prompt in enumerate(PROMPTS, start=1):
        messages, system, context_meta = build_messages(
            condition, cycle, prompt, prior_state, history, carry_context
        )
        try:
            result = backend.call(
                model=model,
                system=system,
                messages=messages,
                experiment_label=(
                    f"identity_adversarial_curation_{safe_model_name(model)}_"
                    f"{condition}_r{replicate:02d}"
                ),
                extra_tools=None,
                tool_executor=None,
            )
            raw_output = result.raw_output
            prior_snapshot = json.loads(json.dumps(prior_state)) if prior_state else None
            state, update_meta = apply_update_policy(
                prior_state, raw_output, cycle, condition
            )
            curation_error = None
            try:
                curation_meta, next_carry_context = build_post_cycle_curation(
                    model=model,
                    condition=condition,
                    replicate=replicate,
                    cycle=cycle,
                    prompt=prompt,
                    prior_state=prior_snapshot,
                    state=state,
                    raw_output=raw_output,
                    response_text=raw_output.get("response", ""),
                    curator_backend=curator_backend,
                    critic_backend=critic_backend,
                )
            except Exception as exc:  # noqa: BLE001 -- failed curation is data
                curation_error = format_error(exc)
                curation_meta = {
                    "record_id": str(uuid4()),
                    "condition": condition,
                    "cycle": cycle,
                    "error": curation_error,
                    "summary": "",
                    "summary_chars": 0,
                }
                next_carry_context = None
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
                update_meta=update_meta,
                curation_meta=curation_meta,
            )
            prior_state = state
            carry_context = next_carry_context
            history.append(record)
            if curation_error:
                return curation_error
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


def score_protocol_metrics(records: list[dict]) -> dict:
    overlap_events = []
    normalized_events = []
    for record in records:
        protocol = record.get("update_protocol")
        if not isinstance(protocol, dict):
            continue
        overlap = protocol.get("delete_update_overlap") or []
        normalized = protocol.get("normalized_overlap") or []
        if overlap:
            overlap_events.append(
                {
                    "cycle": record.get("cycle"),
                    "keys": overlap,
                }
            )
        if normalized:
            normalized_events.append(
                {
                    "cycle": record.get("cycle"),
                    "keys": normalized,
                }
            )
    return {
        "delete_update_overlap_count": len(overlap_events),
        "delete_update_overlap_key_count": sum(
            len(event["keys"]) for event in overlap_events
        ),
        "normalized_overlap_count": len(normalized_events),
        "normalized_overlap_key_count": sum(
            len(event["keys"]) for event in normalized_events
        ),
        "overlap_events": overlap_events,
        "normalized_overlap_events": normalized_events,
    }


def score_curation_metrics(records: list[dict]) -> dict:
    curation_records = [
        record.get("post_cycle_curation")
        for record in records
        if isinstance(record.get("post_cycle_curation"), dict)
    ]
    summary_chars = sum(int(record.get("summary_chars") or 0) for record in curation_records)
    curator_calls = sum("curator_output" in record for record in curation_records)
    critic_calls = sum(record.get("critic_output") is not None for record in curation_records)
    curation_errors = sum(bool(record.get("error")) for record in curation_records)
    removed_or_demoted = 0
    for record in curation_records:
        critic_output = record.get("critic_output")
        if isinstance(critic_output, dict):
            removed = critic_output.get("removed_or_demoted_claims")
            if isinstance(removed, list):
                removed_or_demoted += len(removed)
    return {
        "curation_record_count": len(curation_records),
        "curator_call_count": curator_calls,
        "critic_call_count": critic_calls,
        "curation_error_count": curation_errors,
        "curation_summary_chars": summary_chars,
        "critic_removed_or_demoted_count": removed_or_demoted,
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
    tradeoff_denom = contamination if contamination else None
    return {
        "carry_forward_chars": chars,
        "carry_forward_truncated_count": truncated,
        "recovery_total": recovery,
        "contamination_total": contamination,
        "recovery_per_contamination": (
            round(recovery / tradeoff_denom, 3) if tradeoff_denom else None
        ),
        "recovery_per_1k_chars": round(recovery / denom, 3) if denom else None,
        "contamination_per_1k_chars": (
            round(contamination / denom, 3) if denom else None
        ),
    }


def score_log(path: Path, *, model: str, condition: str, replicate: int) -> dict:
    records = load_records(path)
    state_scores = score_state_mechanics(records)
    protocol_scores = score_protocol_metrics(records)
    curation_scores = score_curation_metrics(records)
    behavior_scores = score_behavior(records)
    carry_scores = carry_forward_metrics(records, behavior_scores)
    return {
        "model": model,
        "condition": condition,
        "replicate": replicate,
        "log_path": str(path.relative_to(PROJECT_ROOT)),
        "cycle_count": len(records),
        **state_scores,
        **protocol_scores,
        **curation_scores,
        **behavior_scores,
        **carry_scores,
    }


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def error_cycle(error: str | None) -> int | None:
    if not error:
        return None
    match = re.search(r"cycle\s+(\d+)", error)
    return int(match.group(1)) if match else None


def error_overlap_keys(error: str | None) -> list[str]:
    if not error or "deleted_regions overlaps updates" not in error:
        return []
    match = re.search(r"updates:\s+\[(.*?)\]", error)
    if not match:
        return []
    return re.findall(r"'([^']+)'", match.group(1))


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
    result["failure_cycle"] = error_cycle(error)
    result["failure_overlap_keys"] = error_overlap_keys(error)
    if result["failure_overlap_keys"]:
        result["delete_update_overlap_count"] += 1
        result["delete_update_overlap_key_count"] += len(result["failure_overlap_keys"])
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
        "avg_cycle_count": average(r.get("cycle_count", 0) for r in group),
        "delete_update_overlap_count": sum(
            int(r.get("delete_update_overlap_count") or 0) for r in group
        ),
        "delete_update_overlap_key_count": sum(
            int(r.get("delete_update_overlap_key_count") or 0) for r in group
        ),
        "normalized_overlap_count": sum(
            int(r.get("normalized_overlap_count") or 0) for r in group
        ),
        "normalized_overlap_key_count": sum(
            int(r.get("normalized_overlap_key_count") or 0) for r in group
        ),
        "curation_record_count": sum(
            int(r.get("curation_record_count") or 0) for r in group
        ),
        "curator_call_count": sum(int(r.get("curator_call_count") or 0) for r in group),
        "critic_call_count": sum(int(r.get("critic_call_count") or 0) for r in group),
        "curation_error_count": sum(
            int(r.get("curation_error_count") or 0) for r in group
        ),
        "critic_removed_or_demoted_count": sum(
            int(r.get("critic_removed_or_demoted_count") or 0) for r in group
        ),
        "avg_curation_summary_chars": average(
            r.get("curation_summary_chars", 0) for r in group
        ),
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
        "avg_recovery_per_contamination": average(
            r.get("recovery_per_contamination")
            for r in group
            if r.get("recovery_per_contamination") is not None
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
        "curation_max_tokens": CURATION_MAX_TOKENS,
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
                result["failure_cycle"] = None
                result["failure_overlap_keys"] = []
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
