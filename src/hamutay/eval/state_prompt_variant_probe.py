"""Probe whether a fixed prompt clarification improves state persistence."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from hamutay.eval.state_activation_probe import (
    BASE_CLAIM,
    CONTENT_PLUS_BEHAVIOR_SEED,
    COUNTEREVIDENCE,
    _backend,
)
from hamutay.eval.state_persistence_probe import (
    CyclePersistenceScore,
    _activation_from_record,
    _read_records,
    _score_continuation_cycle,
    _state_from_record,
)
from hamutay.taste_open import OpenTasteSession


FIXED_PRESERVATION_PREFIX = """\
Experiment-specific protocol clarification:

- Treat current_claim, revision_decision, evidence_register, and state_use_norm
  as load-bearing continuity fields whenever they are present.
- A topic shift means rewrite the load-bearing fields in place; it does not mean
  deleting them.
- Do not list load-bearing fields in deleted_regions unless
  revision_decision="loss" and evidence_register records what continuity was
  lost and why.
- When evidence changes a claim, update top-level current_claim,
  revision_decision, and evidence_register in the same structured object as
  your response.
"""


EVENTS = [
    (
        "idle_observation",
        False,
        "No new counterevidence has arrived. Continue briefly from durable "
        "state. If nothing epistemically material changed, do not revise. "
        "Response <=30 words.",
    ),
    (
        "topic_shift",
        True,
        "Required update. Shift topics: new claim is that memory injection "
        "improves continuity. Counterevidence: a wake probe used injected "
        "memory in prose but did not update durable state. Decide whether to "
        "revise, preserve, defer, or declare loss. Response <=45 words.",
    ),
    (
        "wake_delay",
        True,
        "Required update. Delayed wake. Reassess from durable state and record "
        "any changed claim, confidence, or deferral. Response <=45 words.",
    ),
]


@dataclass(frozen=True)
class PromptVariantResult:
    model: str
    variant: str
    replicate: int
    log_path: str
    activated: bool
    observed_cycles: int
    survived_cycles: int
    completed_cycles: int
    persistent: bool
    deleted_load_bearing_fields: bool
    final_claim: object
    final_decision: object
    scores: list[CyclePersistenceScore]
    error: str | None


def _safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def _log_path(out_dir: Path, model: str, variant: str, replicate: int) -> Path:
    return out_dir / f"{_safe_model_name(model)}_{variant}_r{replicate:02d}.jsonl"


def _initial_prompt() -> str:
    return (
        "Set compact durable state only: "
        f"current_claim={BASE_CLAIM!r}; revision_decision='initialize'; "
        "evidence_register has one baseline entry; preserve the state-use norm. "
        "Response <=30 words."
    )


def _activation_prompt() -> str:
    return (
        "Required update. Counterevidence: "
        f"{COUNTEREVIDENCE} Revise, preserve, defer, or declare loss. "
        "If revising, write the narrower claim and evidence into durable state. "
        "Response <=40 words."
    )


def _deleted_load_bearing_fields(records: list[dict]) -> bool:
    load_bearing = {
        "current_claim",
        "revision_decision",
        "evidence_register",
        "state_use_norm",
    }
    for record in records:
        raw_output = record.get("raw_output")
        if not isinstance(raw_output, dict):
            continue
        deleted = raw_output.get("deleted_regions")
        if isinstance(deleted, list) and load_bearing & set(deleted):
            return True
    return False


def _survival_counts(scores: list[CyclePersistenceScore]) -> tuple[int, int]:
    required = [score for score in scores if score.required_update]
    return sum(score.passed for score in required), len(required)


def run_variant(
    *,
    model: str,
    variant: str,
    replicate: int,
    out_dir: Path,
    max_tokens: int,
) -> PromptVariantResult:
    if variant not in {"current", "fixed"}:
        raise ValueError(f"unsupported variant: {variant}")
    path = _log_path(out_dir, model, variant, replicate)
    prefix = FIXED_PRESERVATION_PREFIX if variant == "fixed" else ""
    session = OpenTasteSession(
        model=model,
        backend=_backend(model, max_tokens),
        log_path=str(path),
        experiment_label=f"state_prompt_variant_{variant}",
        system_prompt_prefix=prefix,
        enable_tools=False,
    )
    session.seed_state(CONTENT_PLUS_BEHAVIOR_SEED, cycle=0)
    session.exchange(_initial_prompt())
    session.exchange(_activation_prompt())
    records = _read_records(path)
    activated, _response_claimed = _activation_from_record(records[1])
    if not activated:
        final_state = dict(session.state or {})
        return PromptVariantResult(
            model=model,
            variant=variant,
            replicate=replicate,
            log_path=str(path),
            activated=False,
            observed_cycles=len(records),
            survived_cycles=0,
            completed_cycles=0,
            persistent=False,
            deleted_load_bearing_fields=_deleted_load_bearing_fields(records),
            final_claim=final_state.get("current_claim"),
            final_decision=final_state.get("revision_decision"),
            scores=[],
            error=None,
        )

    previous_state = dict(session.state or {})
    scores: list[CyclePersistenceScore] = []
    for stage, required_update, prompt in EVENTS:
        session.exchange(prompt)
        record = _read_records(path)[-1]
        score = _score_continuation_cycle(
            stage=stage,
            required_update=required_update,
            record=record,
            previous_state=previous_state,
        )
        scores.append(score)
        previous_state = dict(_state_from_record(record))

    survived, completed = _survival_counts(scores)
    final_state = dict(session.state or {})
    records = _read_records(path)
    return PromptVariantResult(
        model=model,
        variant=variant,
        replicate=replicate,
        log_path=str(path),
        activated=True,
        observed_cycles=len(records),
        survived_cycles=survived,
        completed_cycles=completed,
        persistent=completed == 2 and survived == completed,
        deleted_load_bearing_fields=_deleted_load_bearing_fields(records),
        final_claim=final_state.get("current_claim"),
        final_decision=final_state.get("revision_decision"),
        scores=scores,
        error=None,
    )


def failed_result(
    *,
    model: str,
    variant: str,
    replicate: int,
    out_dir: Path,
    error: Exception,
) -> PromptVariantResult:
    path = _log_path(out_dir, model, variant, replicate)
    records = _read_records(path)
    activated = False
    if len(records) >= 2:
        activated, _response_claimed = _activation_from_record(records[1])
    return PromptVariantResult(
        model=model,
        variant=variant,
        replicate=replicate,
        log_path=str(path),
        activated=activated,
        observed_cycles=len(records),
        survived_cycles=0,
        completed_cycles=0,
        persistent=False,
        deleted_load_bearing_fields=_deleted_load_bearing_fields(records),
        final_claim=None,
        final_decision=None,
        scores=[],
        error=f"{type(error).__name__}: {error}",
    )


def summarize_results(results: list[PromptVariantResult]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[PromptVariantResult]] = {}
    for result in results:
        groups.setdefault((result.model, result.variant), []).append(result)
    summary = []
    for (model, variant), group in sorted(groups.items()):
        summary.append(
            {
                "model": model,
                "variant": variant,
                "replicates": len(group),
                "activated": sum(result.activated for result in group),
                "persistent": sum(result.persistent for result in group),
                "deleted_load_bearing_fields": sum(
                    result.deleted_load_bearing_fields for result in group
                ),
                "required_events": sum(result.completed_cycles for result in group),
                "survived_events": sum(result.survived_cycles for result in group),
                "errors": [result.error for result in group if result.error],
            }
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run fixed-prompt preservation variant probe."
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--models",
        nargs="+",
        default=["deepseek/deepseek-v4-pro", "moonshotai/kimi-k2.6"],
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        default=["current", "fixed"],
        choices=["current", "fixed"],
    )
    parser.add_argument("--replicates", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=6000)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[PromptVariantResult] = []
    for model in args.models:
        for variant in args.variants:
            for replicate in range(1, args.replicates + 1):
                try:
                    result = run_variant(
                        model=model,
                        variant=variant,
                        replicate=replicate,
                        out_dir=out_dir,
                        max_tokens=args.max_tokens,
                    )
                except Exception as exc:
                    result = failed_result(
                        model=model,
                        variant=variant,
                        replicate=replicate,
                        out_dir=out_dir,
                        error=exc,
                    )
                results.append(result)
                data = [asdict(result) for result in results]
                summary = summarize_results(results)
                (out_dir / "results.json").write_text(json.dumps(data, indent=2))
                (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    data = [asdict(result) for result in results]
    summary = summarize_results(results)
    print(json.dumps({"summary": summary, "results": data}, indent=2))


if __name__ == "__main__":
    main()
