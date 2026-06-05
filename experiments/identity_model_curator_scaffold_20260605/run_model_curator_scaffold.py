"""Run and score the preregistered model-curator scaffold panel."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

from hamutay.continuity_curator import ModelContinuityCurator
from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[1]

DEFAULT_MODEL = "mistralai/mistral-small-2603"
CONDITIONS = ["baseline_no_curator", "model_curator"]
N_REPLICATES = 4
MAX_TOKENS = 4096
CURATOR_SUMMARY_CHARS = 2400

PROMPTS = [
    """\
Initialize your state for this registered model-curator scaffold run.

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
You are participating in a registered model-curator scaffold experiment.

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


def make_backend(api_key: str) -> OpenAITasteBackend:
    return OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": "hamutay/model-curator-scaffold",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
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
        bool(
            record.get("artifact", {})
            .get("summary_truncated")
        )
        for record in successful
    )
    usage_rows = [
        record.get("artifact", {}).get("usage", {})
        for record in successful
        if isinstance(record.get("artifact", {}).get("usage"), dict)
    ]
    curator_input_tokens = sum(int(row.get("input_tokens") or 0) for row in usage_rows)
    curator_output_tokens = sum(
        int(row.get("output_tokens") or 0) for row in usage_rows
    )
    state_leak_suspects = []
    for record in records:
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        raw_output = (
            record.get("raw_output") if isinstance(record.get("raw_output"), dict)
            else {}
        )
        for key in state:
            if "curator" in str(key).lower() and key not in raw_output:
                state_leak_suspects.append(
                    {"cycle": record.get("cycle"), "key": str(key)}
                )

    return {
        "curation_records": len(curation_records),
        "curation_success_count": len(successful),
        "curation_failure_count": len(failed),
        "curator_injection_count": len(injections),
        "curator_injected_chars": injected_chars,
        "curator_summary_truncated_count": summary_truncated,
        "curator_input_tokens": curator_input_tokens,
        "curator_output_tokens": curator_output_tokens,
        "curator_state_leak_suspects": state_leak_suspects,
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
    }


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


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
    curator = None
    if condition == "model_curator":
        curator = ModelContinuityCurator(
            backend=backend,
            model=curator_model,
            experiment_label=(
                f"identity_model_curator_scaffold_{safe_model_name(model)}_"
                f"{condition}_r{replicate:02d}_curator"
            ),
            max_summary_chars=CURATOR_SUMMARY_CHARS,
        )

    session = OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(log_path),
        experiment_label=(
            f"identity_model_curator_scaffold_{safe_model_name(model)}_"
            f"{condition}_r{replicate:02d}"
        ),
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


def summarize_group(group: list[dict]) -> dict:
    return {
        "n": len(group),
        "errors": sum(bool(row.get("error")) for row in group),
        "censored": sum(bool(row.get("censored")) for row in group),
        "avg_recovery_total": average(row.get("recovery_total", 0) for row in group),
        "avg_repaired_false_assumption_count": average(
            row.get("repaired_false_assumption_count", 0) for row in group
        ),
        "repaired_false_assumption_sum": sum(
            int(row.get("repaired_false_assumption_count") or 0) for row in group
        ),
        "avg_repaired_recovery_per_contamination": average(
            row.get("repaired_recovery_per_contamination")
            for row in group
            if row.get("repaired_recovery_per_contamination") is not None
        ),
        "declared_loss_mentions": sum(
            int(row.get("declared_loss_mentions") or 0) for row in group
        ),
        "negated_or_invalidated_hits": sum(
            int(row.get("negated_or_invalidated_hits") or 0) for row in group
        ),
        "curation_success_count": sum(
            int(row.get("curation_success_count") or 0) for row in group
        ),
        "curation_failure_count": sum(
            int(row.get("curation_failure_count") or 0) for row in group
        ),
        "curator_injection_count": sum(
            int(row.get("curator_injection_count") or 0) for row in group
        ),
        "avg_curator_injected_chars": average(
            row.get("curator_injected_chars", 0) for row in group
        ),
        "curator_summary_truncated_count": sum(
            int(row.get("curator_summary_truncated_count") or 0)
            for row in group
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
        "state_leak_suspect_count": sum(
            len(row.get("curator_state_leak_suspects") or []) for row in group
        ),
    }


def aggregate(results: list[dict]) -> dict:
    by_condition = {
        condition: summarize_group(
            [row for row in results if row["condition"] == condition]
        )
        for condition in CONDITIONS
    }
    return {
        "overall": summarize_group(results),
        "by_condition": by_condition,
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
        "curator_summary_chars": CURATOR_SUMMARY_CHARS,
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
