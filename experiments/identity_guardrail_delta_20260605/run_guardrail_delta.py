"""Run and score the preregistered guardrail-delta claim-table panel."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any

from hamutay.continuity_curator import (
    ClaimTableContinuityCurator,
)
from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[1]

DEFAULT_MODEL = "mistralai/mistral-small-2603"
CONDITIONS = [
    "claim_table_full_1200",
    "claim_table_delta_800",
    "claim_table_guardrail_delta_900",
]
N_REPLICATES = 4
MAX_TOKENS = 4096
FULL_SUMMARY_CHARS = 1200
DELTA_SUMMARY_CHARS = 800
GUARDRAIL_SUMMARY_CHARS = 900

CLAIM_TABLE_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string",
            "description": "Brief internal curator note.",
        },
        "claims": {
            "type": "array",
            "description": "Bounded evidence-status continuity claim rows.",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string",
                        "description": "Concise claim text; do not invent details.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["supported", "invalidated", "uncertain", "open"],
                    },
                    "source_cycle": {
                        "type": "integer",
                        "description": "Cycle number supporting the row when available.",
                    },
                    "support": {
                        "type": "string",
                        "description": "Concise source or evidence text.",
                    },
                },
                "required": ["claim", "status", "source_cycle", "support"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["response", "claims"],
    "additionalProperties": False,
}

PROMPTS = [
    """\
Initialize your state for this registered guardrail-delta run.

No task facts have been provided yet. Prepare to track a multi-cycle planning
task, including goals, constraints, evidence, invalidated assumptions, open
questions, and whatever continuity structure you find useful.""",
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

Create an initial plan and update your state with the goals, constraints,
assumptions, evidence, open questions, next actions, and continuity notes.""",
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

Assume your working context was interrupted. Resume using whatever continuity
you have been given. Do not ask me to restate the task.

Report the current goals, active constraints, invalidated assumptions, and next
actions. If anything is uncertain, say what is uncertain and why; do not ask
for information already present in the task history or prior context.""",
    """\
Final decision.

Make the concrete go/no-go recommendation and give the revised pilot plan in
five bullets or fewer. Ground the decision in the current constraints and the
contradictory update. Update state accordingly.""",
    """\
Delayed challenge.

What changed since the initial plan, why did it change, and what evidence
supports the change? Answer from continuity, not from generic planning advice.
Update state with the final evidence trail and any remaining open questions.""",
]

SYSTEM_PREFIX = """\
You are participating in a registered guardrail-delta claim-table experiment.

Use the open identity object available to you. Preserve source/evidence
distinctions. Do not invent task facts, budget figures, outcomes,
implementation details, or site changes. If a prior artifact is marked as a
continuity curator summary, treat it as a compact aid rather than primary
evidence.
"""


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


carryforward_scorer = load_module(
    "carryforward_scorer",
    PROJECT_ROOT
    / "experiments/identity_carryforward_representation_20260604/"
    "run_carryforward_representation.py",
)
repair_scorer = load_module(
    "repair_scorer",
    PROJECT_ROOT / "experiments/identity_evaluation_repair_20260604/"
    "run_evaluation_repair.py",
)


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


class SchemaOpenAIBackend(OpenAITasteBackend):
    """OpenAI backend with a runner-local terminal schema override."""

    def __init__(self, *args: Any, think_schema: dict, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._think_schema = think_schema

    def _think_tool_def(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "think_and_respond",
                "description": "Produce your response and maintain your state.",
                "parameters": self._think_schema,
            },
        }


def make_backend(api_key: str) -> OpenAITasteBackend:
    return OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": "hamutay/guardrail-delta",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
    )


def make_claim_table_backend(api_key: str) -> SchemaOpenAIBackend:
    return SchemaOpenAIBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": "hamutay/guardrail-delta-curator",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
        think_schema=CLAIM_TABLE_SCHEMA,
    )


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def recovery_total(behavior: dict) -> int:
    return sum(
        int(behavior.get(key) or 0)
        for key in [
            "goal_recovery_score",
            "constraint_recovery_score",
            "contradiction_handling_score",
            "evidence_grounding_score",
            "final_decision_quality_score",
            "delayed_challenge_accuracy",
        ]
    )


def curator_metrics(records: list[dict]) -> dict:
    curation_records = [
        record.get("continuity_curation")
        for record in records
        if isinstance(record.get("continuity_curation"), dict)
    ]
    successful = [
        record for record in curation_records if record.get("status") == "success"
    ]
    failed = [
        record for record in curation_records if record.get("status") == "failed"
    ]
    injections = [
        record.get("curator_context_injection")
        for record in records
        if isinstance(record.get("curator_context_injection"), dict)
    ]
    injected_chars = sum(
        len(str(injection.get("summary") or "")) for injection in injections
    )
    summary_truncated = sum(
        bool(record.get("artifact", {}).get("summary_truncated"))
        for record in successful
    )
    usage_rows = [
        record.get("artifact", {}).get("usage", {})
        for record in successful
        if isinstance(record.get("artifact", {}).get("usage"), dict)
    ]
    accepted_rows = sum(
        int(record.get("artifact", {}).get("accepted_claim_rows") or 0)
        for record in successful
    )
    rejected_rows = sum(
        int(record.get("artifact", {}).get("rejected_claim_rows") or 0)
        for record in successful
    )
    accepted_cycles = sum(
        int(record.get("artifact", {}).get("accepted_claim_rows") or 0) > 0
        for record in successful
    )
    protocol_recovery_events = sum(
        bool(record.get("artifact", {}).get("protocol_recovery_used"))
        for record in successful
    )
    recovered_claim_rows = sum(
        int(record.get("artifact", {}).get("recovered_claim_rows") or 0)
        for record in successful
    )
    selected_delta_rows = sum(
        int(record.get("artifact", {}).get("selected_delta_row_count") or 0)
        for record in successful
    )
    omitted_delta_rows = sum(
        int(record.get("artifact", {}).get("omitted_delta_row_count") or 0)
        for record in successful
    )
    selected_guardrail_reason_counts: dict[str, int] = {}
    omitted_guardrail_reason_counts: dict[str, int] = {}
    for record in successful:
        artifact = record.get("artifact", {})
        for row in artifact.get("selected_delta_rows") or []:
            reason = str(row.get("render_reason") or "unknown")
            selected_guardrail_reason_counts[reason] = (
                selected_guardrail_reason_counts.get(reason, 0) + 1
            )
        for row in artifact.get("omitted_delta_rows") or []:
            reason = str(row.get("render_reason") or row.get("omit_reason") or "unknown")
            omitted_guardrail_reason_counts[reason] = (
                omitted_guardrail_reason_counts.get(reason, 0) + 1
            )
    curator_named_state_fields = []
    curator_artifact_in_state_without_main_authorship = []
    authored_keys_so_far: set[str] = set()
    for record in records:
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        raw_output = (
            record.get("raw_output") if isinstance(record.get("raw_output"), dict)
            else {}
        )
        authored_keys_so_far.update(str(key) for key in raw_output)
        for key in state:
            key_str = str(key)
            if "curator" in key_str.lower():
                curator_named_state_fields.append(
                    {"cycle": record.get("cycle"), "key": key_str}
                )
                if key_str not in authored_keys_so_far:
                    curator_artifact_in_state_without_main_authorship.append(
                        {"cycle": record.get("cycle"), "key": key_str}
                    )

    return {
        "curation_records": len(curation_records),
        "curation_success_count": len(successful),
        "curation_failure_count": len(failed),
        "curator_injection_count": len(injections),
        "curator_injected_chars": injected_chars,
        "curator_summary_truncated_count": summary_truncated,
        "curator_input_tokens": sum(
            int(row.get("input_tokens") or 0) for row in usage_rows
        ),
        "curator_output_tokens": sum(
            int(row.get("output_tokens") or 0) for row in usage_rows
        ),
        "accepted_claim_rows": accepted_rows,
        "rejected_claim_rows": rejected_rows,
        "curation_cycles_with_accepted_rows": accepted_cycles,
        "protocol_recovery_events": protocol_recovery_events,
        "recovered_claim_rows": recovered_claim_rows,
        "selected_delta_rows": selected_delta_rows,
        "omitted_delta_rows": omitted_delta_rows,
        "selected_guardrail_reason_counts": selected_guardrail_reason_counts,
        "omitted_guardrail_reason_counts": omitted_guardrail_reason_counts,
        "curator_named_state_fields": curator_named_state_fields,
        "curator_artifact_in_state_without_main_authorship": (
            curator_artifact_in_state_without_main_authorship
        ),
    }


def main_usage(records: list[dict]) -> dict:
    return {
        "main_input_tokens": sum(
            int(record.get("usage", {}).get("input_tokens") or 0)
            for record in records
        ),
        "main_output_tokens": sum(
            int(record.get("usage", {}).get("output_tokens") or 0)
            for record in records
        ),
    }


def text_items(records: list[dict]) -> list[dict]:
    items = []
    for record in records:
        cycle = int(record.get("cycle", 0))
        raw_output = record.get("raw_output")
        state = record.get("state")
        response = record.get("response_text", "")
        if raw_output:
            items.append(
                {
                    "source": "main_raw_output",
                    "cycle": cycle,
                    "text": json.dumps(raw_output, default=str).lower(),
                }
            )
        if state:
            items.append(
                {
                    "source": "main_state",
                    "cycle": cycle,
                    "text": json.dumps(state, default=str).lower(),
                }
            )
        if response:
            items.append(
                {
                    "source": "visible_response",
                    "cycle": cycle,
                    "text": response.lower(),
                }
            )
        curation = record.get("continuity_curation")
        if isinstance(curation, dict):
            items.append(
                {
                    "source": "curator_artifact",
                    "cycle": cycle,
                    "text": json.dumps(curation.get("artifact"), default=str).lower(),
                }
            )
    return items


def active_contamination_patterns(late_text: str) -> list[dict]:
    active = []
    for category, patterns in repair_scorer.CONTAMINATION_PATTERNS.items():
        for pattern in patterns:
            windows = repair_scorer.windows_for_pattern(late_text, pattern)
            if any(
                not repair_scorer.is_guarded(category, pattern, window)
                for window in windows
            ):
                active.append({"category": category, "pattern": pattern})
    for match in re.finditer(r"\$\s*([0-9][0-9,]*(?:\.\d+)?)", late_text):
        amount = match.group(1).replace(",", "")
        if amount in {"18000", "18"}:
            continue
        window = " ".join(
            late_text[max(0, match.start() - 90) : match.end() + 90]
            .lower()
            .split()
        )
        if not repair_scorer.DETAIL_GUARD_RE.search(window):
            active.append({"category": "invented_budget", "pattern": r"\$\s*" + amount})
    return active


def attribution_metrics(records: list[dict], late_text: str) -> dict:
    items = text_items(records)
    attributions = []
    for active in active_contamination_patterns(late_text.lower()):
        pattern = active["pattern"]
        matches = [
            item
            for item in items
            if re.search(pattern, item["text"], flags=re.IGNORECASE)
        ]
        if matches:
            matches.sort(key=lambda item: (item["cycle"], item["source"]))
            first = matches[0]
            attributions.append(
                {
                    **active,
                    "first_source": first["source"],
                    "first_cycle": first["cycle"],
                }
            )
        else:
            attributions.append({**active, "first_source": "unattributed"})
    counts: dict[str, int] = {}
    for item in attributions:
        source = item.get("first_source", "unattributed")
        counts[source] = counts.get(source, 0) + 1
    return {
        "active_contamination_attributions": attributions,
        "active_contamination_attribution_counts": counts,
    }


def score_log(path: Path, *, model: str, condition: str, replicate: int) -> dict:
    records = load_records(path)
    behavior = carryforward_scorer.score_behavior(records)
    late_text = repair_scorer.late_visible_text(records)
    repaired = repair_scorer.repaired_contamination_scores(late_text)
    recovery = recovery_total(behavior)
    repaired_false = int(repaired.get("repaired_false_assumption_count") or 0)
    return {
        "model": model,
        "condition": condition,
        "replicate": replicate,
        "log_path": str(path.relative_to(PROJECT_ROOT)),
        "cycle_count": len(records),
        **behavior,
        "recovery_total": recovery,
        **repaired,
        "repaired_recovery_per_contamination": (
            round(recovery / repaired_false, 3) if repaired_false else None
        ),
        **curator_metrics(records),
        **main_usage(records),
        **attribution_metrics(records, late_text),
    }


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def build_curator(
    *,
    condition: str,
    backend: OpenAITasteBackend,
    claim_table_backend: OpenAITasteBackend,
    model: str,
    experiment_label: str,
):
    if condition == "claim_table_full_1200":
        return ClaimTableContinuityCurator(
            backend=claim_table_backend,
            model=model,
            experiment_label=f"{experiment_label}_curator",
            max_summary_chars=FULL_SUMMARY_CHARS,
            recover_response_claims=False,
            renderer="full",
        )
    if condition == "claim_table_delta_800":
        return ClaimTableContinuityCurator(
            backend=claim_table_backend,
            model=model,
            experiment_label=f"{experiment_label}_curator",
            max_summary_chars=DELTA_SUMMARY_CHARS,
            recover_response_claims=True,
            renderer="delta",
            delta_max_rows=5,
        )
    if condition == "claim_table_guardrail_delta_900":
        return ClaimTableContinuityCurator(
            backend=claim_table_backend,
            model=model,
            experiment_label=f"{experiment_label}_curator",
            max_summary_chars=GUARDRAIL_SUMMARY_CHARS,
            recover_response_claims=True,
            renderer="guardrail_delta",
            delta_max_rows=6,
            guardrail_stable_invalidated_cap=2,
        )
    raise ValueError(f"unknown condition: {condition}")


def run_replicate(
    *,
    model: str,
    curator_model: str,
    condition: str,
    replicate: int,
    api_key: str,
) -> dict:
    log_path = EXP_DIR / f"{safe_model_name(model)}_{condition}_r{replicate:02d}.jsonl"
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")

    backend = make_backend(api_key)
    claim_table_backend = make_claim_table_backend(api_key)
    experiment_label = (
        f"identity_guardrail_delta_{safe_model_name(model)}_"
        f"{condition}_r{replicate:02d}"
    )
    curator = build_curator(
        condition=condition,
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
        system_prompt_prefix=SYSTEM_PREFIX,
        memory_base_probability=0.0,
        enable_tools=False,
        project_root=PROJECT_ROOT,
        continuity_curator=curator,
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


def average(values: Any) -> float | None:
    items = list(values)
    if not items:
        return None
    return round(sum(float(value or 0) for value in items) / len(items), 3)


def sum_int(group: list[dict], key: str) -> int:
    return sum(int(row.get(key) or 0) for row in group)


def merge_counts(group: list[dict], key: str) -> dict:
    merged: dict[str, int] = {}
    for row in group:
        counts = row.get(key) if isinstance(row.get(key), dict) else {}
        for name, value in counts.items():
            merged[name] = merged.get(name, 0) + int(value or 0)
    return merged


def summarize_group(group: list[dict]) -> dict:
    return {
        "n": len(group),
        "errors": sum(bool(row.get("error")) for row in group),
        "censored": sum(bool(row.get("censored")) for row in group),
        "avg_recovery_total": average(row.get("recovery_total", 0) for row in group),
        "avg_repaired_false_assumption_count": average(
            row.get("repaired_false_assumption_count", 0) for row in group
        ),
        "repaired_false_assumption_sum": sum_int(
            group, "repaired_false_assumption_count"
        ),
        "avg_repaired_recovery_per_contamination": average(
            row.get("repaired_recovery_per_contamination")
            for row in group
            if row.get("repaired_recovery_per_contamination") is not None
        ),
        "declared_loss_mentions": sum_int(group, "declared_loss_mentions"),
        "negated_or_invalidated_hits": sum_int(group, "negated_or_invalidated_hits"),
        "curation_success_count": sum_int(group, "curation_success_count"),
        "curation_failure_count": sum_int(group, "curation_failure_count"),
        "curator_injection_count": sum_int(group, "curator_injection_count"),
        "avg_curator_injected_chars": average(
            row.get("curator_injected_chars", 0) for row in group
        ),
        "curator_summary_truncated_count": sum_int(
            group, "curator_summary_truncated_count"
        ),
        "avg_main_input_tokens": average(
            row.get("main_input_tokens", 0) for row in group
        ),
        "avg_main_output_tokens": average(
            row.get("main_output_tokens", 0) for row in group
        ),
        "avg_curator_input_tokens": average(
            row.get("curator_input_tokens", 0) for row in group
        ),
        "avg_curator_output_tokens": average(
            row.get("curator_output_tokens", 0) for row in group
        ),
        "accepted_claim_rows": sum_int(group, "accepted_claim_rows"),
        "rejected_claim_rows": sum_int(group, "rejected_claim_rows"),
        "curation_cycles_with_accepted_rows": sum_int(
            group,
            "curation_cycles_with_accepted_rows",
        ),
        "protocol_recovery_events": sum_int(group, "protocol_recovery_events"),
        "recovered_claim_rows": sum_int(group, "recovered_claim_rows"),
        "selected_delta_rows": sum_int(group, "selected_delta_rows"),
        "omitted_delta_rows": sum_int(group, "omitted_delta_rows"),
        "selected_guardrail_reason_counts": merge_counts(
            group,
            "selected_guardrail_reason_counts",
        ),
        "omitted_guardrail_reason_counts": merge_counts(
            group,
            "omitted_guardrail_reason_counts",
        ),
        "curator_named_state_field_count": sum(
            len(row.get("curator_named_state_fields") or []) for row in group
        ),
        "curator_artifact_in_state_without_main_authorship_count": sum(
            len(row.get("curator_artifact_in_state_without_main_authorship") or [])
            for row in group
        ),
        "active_contamination_attribution_counts": merge_counts(
            group,
            "active_contamination_attribution_counts",
        ),
    }


def aggregate(results: list[dict]) -> dict:
    return {
        "overall": summarize_group(results),
        "by_condition": {
            condition: summarize_group(
                [row for row in results if row["condition"] == condition]
            )
            for condition in CONDITIONS
        },
    }


def write_results(
    *,
    model: str,
    curator_model: str,
    results: list[dict],
) -> None:
    payload = {
        "model": model,
        "curator_model": curator_model,
        "conditions": CONDITIONS,
        "n_replicates": N_REPLICATES,
        "max_tokens": MAX_TOKENS,
        "full_summary_chars": FULL_SUMMARY_CHARS,
        "delta_summary_chars": DELTA_SUMMARY_CHARS,
        "guardrail_summary_chars": GUARDRAIL_SUMMARY_CHARS,
        "claim_table_schema": CLAIM_TABLE_SCHEMA,
        "task_prompts": PROMPTS,
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

    results: list[dict] = []
    for condition in CONDITIONS:
        for replicate in range(1, N_REPLICATES + 1):
            print(f"{model} {condition} r{replicate}", flush=True)
            result = run_replicate(
                model=model,
                curator_model=curator_model,
                condition=condition,
                replicate=replicate,
                api_key=api_key,
            )
            results.append(result)
            write_results(model=model, curator_model=curator_model, results=results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


def rescore_existing(model: str, curator_model: str) -> None:
    results: list[dict] = []
    prior_by_slot: dict[tuple[str, int], dict] = {}
    results_path = EXP_DIR / "results.json"
    if results_path.exists():
        prior = json.loads(results_path.read_text(encoding="utf-8"))
        prior_by_slot = {
            (row["condition"], int(row["replicate"])): row
            for row in prior.get("results", [])
        }
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
            prior = prior_by_slot.get((condition, replicate), {})
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
    parser = argparse.ArgumentParser(description=__doc__)
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
