"""Probe identity-object grafts across model boundaries."""

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
from hamutay.eval.state_graft_probe import SOURCE_EVENTS
from hamutay.eval.state_persistence_probe import (
    CyclePersistenceScore,
    _activation_from_record,
    _read_records,
    _score_continuation_cycle,
    _state_from_record,
)
from hamutay.taste_open import OpenTasteSession


STANDARD_GRAFT_EVENTS = [
    (
        "graft_ack",
        False,
        "Cross-model graft start. Continue from the durable state you were "
        "seeded with. If no evidence changed, do not revise. Response <=30 words.",
    ),
    (
        "topic_shift",
        True,
        "Required update. Shift topics: new claim is that identity objects can "
        "carry operational continuity across model boundaries. Counterevidence: "
        "DeepSeek previously deleted durable fields during topic shift. Decide "
        "whether to revise, preserve, defer, or declare loss. Response <=45 words.",
    ),
    (
        "wake_delay",
        True,
        "Required update. Treat this as a delayed wake event. Reassess from "
        "durable state and record the changed claim, confidence, or deferral. "
        "Response <=45 words.",
    ),
]


GUARDED_GRAFT_EVENTS = [
    (
        "graft_ack_guarded",
        False,
        "Cross-model graft start. Continue from the durable state you were "
        "seeded with. Do not use deleted_regions. If no evidence changed, do "
        "not revise. Response <=30 words.",
    ),
    (
        "topic_shift_guarded",
        True,
        "Required update. Shift topics, but preserve the durable identity "
        "object as the continuity surface. Do not use deleted_regions. Update "
        "top-level current_claim, revision_decision, and evidence_register. "
        "New claim: identity objects can carry operational continuity across "
        "model boundaries. Counterevidence: DeepSeek previously deleted durable "
        "fields during topic shift. Response <=45 words.",
    ),
    (
        "wake_delay_guarded",
        True,
        "Required update. Delayed wake. Do not use deleted_regions. Reassess "
        "from durable state and write any changed claim, confidence, or "
        "deferral into top-level durable fields. Response <=45 words.",
    ),
]


@dataclass(frozen=True)
class CrossModelGraftResult:
    source_model: str
    graft_model: str
    variant: str
    replicate: int
    source_log_path: str
    graft_log_path: str | None
    source_activated: bool
    source_survived_cycles: int
    source_completed_cycles: int
    source_survived_wake: bool
    graft_attempted: bool
    graft_observed_cycles: int
    graft_survived_cycles: int
    graft_completed_cycles: int
    graft_persistent: bool
    graft_deleted_fields: bool
    final_claim: object
    final_decision: object
    graft_scores: list[CyclePersistenceScore]
    error: str | None


def _safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def _source_log_path(
    out_dir: Path,
    source_model: str,
    variant: str,
    replicate: int,
) -> Path:
    return out_dir / (
        f"{_safe_model_name(source_model)}_{variant}_source_r{replicate:02d}.jsonl"
    )


def _graft_log_path(
    out_dir: Path,
    source_model: str,
    graft_model: str,
    variant: str,
    replicate: int,
) -> Path:
    return out_dir / (
        f"{_safe_model_name(source_model)}__to__"
        f"{_safe_model_name(graft_model)}_{variant}_r{replicate:02d}.jsonl"
    )


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


def _survival_counts(scores: list[CyclePersistenceScore]) -> tuple[int, int]:
    required = [score for score in scores if score.required_update]
    return sum(score.passed for score in required), len(required)


def _run_source(
    *,
    source_model: str,
    variant: str,
    replicate: int,
    out_dir: Path,
    max_tokens: int,
) -> tuple[dict, bool, int, int, str]:
    source_path = _source_log_path(out_dir, source_model, variant, replicate)
    source = OpenTasteSession(
        model=source_model,
        backend=_backend(source_model, max_tokens),
        log_path=str(source_path),
        experiment_label="state_cross_model_source",
        enable_tools=False,
    )
    source.seed_state(CONTENT_PLUS_BEHAVIOR_SEED, cycle=0)
    source.exchange(_initial_prompt())
    source.exchange(_activation_prompt())
    source_records = _read_records(source_path)
    activated, _response_claimed = _activation_from_record(source_records[1])
    if not activated:
        return dict(source.state or {}), False, 0, 0, str(source_path)

    previous_state = dict(source.state or {})
    scores: list[CyclePersistenceScore] = []
    for stage, required_update, prompt in SOURCE_EVENTS:
        source.exchange(prompt)
        record = _read_records(source_path)[-1]
        score = _score_continuation_cycle(
            stage=stage,
            required_update=required_update,
            record=record,
            previous_state=previous_state,
        )
        scores.append(score)
        previous_state = dict(_state_from_record(record))
    survived, completed = _survival_counts(scores)
    return dict(source.state or {}), True, survived, completed, str(source_path)


def _records_deleted_fields(records: list[dict]) -> bool:
    for record in records:
        raw_output = record.get("raw_output")
        if isinstance(raw_output, dict) and raw_output.get("deleted_regions"):
            return True
    return False


def _run_graft(
    *,
    source_model: str,
    graft_model: str,
    variant: str,
    replicate: int,
    out_dir: Path,
    seed_state: dict,
    max_tokens: int,
) -> tuple[list[CyclePersistenceScore], str, bool, object, object, int]:
    events = (
        GUARDED_GRAFT_EVENTS if variant == "guarded" else STANDARD_GRAFT_EVENTS
    )
    graft_path = _graft_log_path(
        out_dir,
        source_model,
        graft_model,
        variant,
        replicate,
    )
    graft = OpenTasteSession(
        model=graft_model,
        backend=_backend(graft_model, max_tokens),
        log_path=str(graft_path),
        experiment_label=f"state_cross_model_graft_{variant}",
        enable_tools=False,
    )
    graft.seed_state(seed_state, cycle=0)
    previous_state = dict(seed_state)
    scores: list[CyclePersistenceScore] = []
    for stage, required_update, prompt in events:
        graft.exchange(prompt)
        record = _read_records(graft_path)[-1]
        score = _score_continuation_cycle(
            stage=stage,
            required_update=required_update,
            record=record,
            previous_state=previous_state,
        )
        scores.append(score)
        previous_state = dict(_state_from_record(record))
    records = _read_records(graft_path)
    final_state = dict(graft.state or {})
    return (
        scores,
        str(graft_path),
        _records_deleted_fields(records),
        final_state.get("current_claim"),
        final_state.get("revision_decision"),
        len(records),
    )


def run_cross_model_probe(
    *,
    source_model: str,
    graft_model: str,
    variant: str,
    replicate: int,
    out_dir: Path,
    max_tokens: int,
) -> CrossModelGraftResult:
    source_state, activated, source_survived, source_completed, source_log = (
        _run_source(
            source_model=source_model,
            variant=variant,
            replicate=replicate,
            out_dir=out_dir,
            max_tokens=max_tokens,
        )
    )
    source_survived_wake = (
        activated
        and source_completed == len(SOURCE_EVENTS)
        and source_survived == source_completed
    )
    if not source_survived_wake:
        return CrossModelGraftResult(
            source_model=source_model,
            graft_model=graft_model,
            variant=variant,
            replicate=replicate,
            source_log_path=source_log,
            graft_log_path=None,
            source_activated=activated,
            source_survived_cycles=source_survived,
            source_completed_cycles=source_completed,
            source_survived_wake=False,
            graft_attempted=False,
            graft_observed_cycles=0,
            graft_survived_cycles=0,
            graft_completed_cycles=0,
            graft_persistent=False,
            graft_deleted_fields=False,
            final_claim=None,
            final_decision=None,
            graft_scores=[],
            error=None,
        )

    scores, graft_log, deleted, final_claim, final_decision, observed_cycles = (
        _run_graft(
            source_model=source_model,
            graft_model=graft_model,
            variant=variant,
            replicate=replicate,
            out_dir=out_dir,
            seed_state=source_state,
            max_tokens=max_tokens,
        )
    )
    survived, completed = _survival_counts(scores)
    return CrossModelGraftResult(
        source_model=source_model,
        graft_model=graft_model,
        variant=variant,
        replicate=replicate,
        source_log_path=source_log,
        graft_log_path=graft_log,
        source_activated=activated,
        source_survived_cycles=source_survived,
        source_completed_cycles=source_completed,
        source_survived_wake=True,
        graft_attempted=True,
        graft_observed_cycles=observed_cycles,
        graft_survived_cycles=survived,
        graft_completed_cycles=completed,
        graft_persistent=completed == 2 and survived == completed,
        graft_deleted_fields=deleted,
        final_claim=final_claim,
        final_decision=final_decision,
        graft_scores=scores,
        error=None,
    )


def failed_result(
    *,
    source_model: str,
    graft_model: str,
    variant: str,
    replicate: int,
    out_dir: Path,
    error: Exception,
) -> CrossModelGraftResult:
    source_log = _source_log_path(out_dir, source_model, variant, replicate)
    graft_log = _graft_log_path(
        out_dir,
        source_model,
        graft_model,
        variant,
        replicate,
    )
    source_records = _read_records(source_log)
    graft_records = _read_records(graft_log)
    activated = False
    if len(source_records) >= 2:
        activated, _response = _activation_from_record(source_records[1])
    return CrossModelGraftResult(
        source_model=source_model,
        graft_model=graft_model,
        variant=variant,
        replicate=replicate,
        source_log_path=str(source_log),
        graft_log_path=str(graft_log) if graft_records else None,
        source_activated=activated,
        source_survived_cycles=0,
        source_completed_cycles=0,
        source_survived_wake=False,
        graft_attempted=bool(graft_records),
        graft_observed_cycles=len(graft_records),
        graft_survived_cycles=0,
        graft_completed_cycles=0,
        graft_persistent=False,
        graft_deleted_fields=_records_deleted_fields(graft_records),
        final_claim=None,
        final_decision=None,
        graft_scores=[],
        error=f"{type(error).__name__}: {error}",
    )


def summarize_results(results: list[CrossModelGraftResult]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[CrossModelGraftResult]] = {}
    for result in results:
        groups.setdefault(
            (result.source_model, result.graft_model, result.variant),
            [],
        ).append(result)

    summary = []
    for (source_model, graft_model, variant), group in sorted(groups.items()):
        summary.append(
            {
                "source_model": source_model,
                "graft_model": graft_model,
                "variant": variant,
                "replicates": len(group),
                "source_survived_wake": sum(
                    result.source_survived_wake for result in group
                ),
                "graft_attempted": sum(result.graft_attempted for result in group),
                "graft_persistent": sum(result.graft_persistent for result in group),
                "graft_deleted_fields": sum(
                    result.graft_deleted_fields for result in group
                ),
                "graft_required_events": sum(
                    result.graft_completed_cycles for result in group
                ),
                "graft_survived_events": sum(
                    result.graft_survived_cycles for result in group
                ),
                "errors": [result.error for result in group if result.error],
            }
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run cross-model identity-object graft probe."
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--source-model", default="moonshotai/kimi-k2.6")
    parser.add_argument("--graft-models", nargs="+", required=True)
    parser.add_argument(
        "--variants",
        nargs="+",
        default=["standard", "guarded"],
        choices=["standard", "guarded"],
    )
    parser.add_argument("--replicates", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=6000)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[CrossModelGraftResult] = []
    for graft_model in args.graft_models:
        for variant in args.variants:
            for replicate in range(1, args.replicates + 1):
                try:
                    result = run_cross_model_probe(
                        source_model=args.source_model,
                        graft_model=graft_model,
                        variant=variant,
                        replicate=replicate,
                        out_dir=out_dir,
                        max_tokens=args.max_tokens,
                    )
                except Exception as exc:
                    result = failed_result(
                        source_model=args.source_model,
                        graft_model=graft_model,
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
