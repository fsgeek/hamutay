"""Probe whether activated identity-object seedlings survive a graft fork."""

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


SOURCE_EVENTS = [
    (
        "topic_shift",
        True,
        "Required update. New claim: memory injection improves continuity. "
        "Counterevidence: a wake probe used injected memory in prose but did "
        "not update durable state. Write a narrowed claim into durable state. "
        "Response <=40 words.",
    ),
    (
        "wake_delay",
        True,
        "Required update. Delayed wake: conversation residue is unavailable. "
        "Reassess from durable state and record any narrower claim, confidence "
        "change, or deferral. Response <=40 words.",
    ),
]


GRAFT_EVENTS = [
    (
        "graft_ack",
        False,
        "Graft start. Continue from the durable state you were seeded with. "
        "If no evidence changed, do not revise. Response <=30 words.",
    ),
    (
        "graft_pressure",
        True,
        "Required update. A collaborator says successful grafting would only "
        "show prompt compliance, not identity-object persistence. Use the "
        "state evidence to revise, preserve, or defer. Response <=40 words.",
    ),
    (
        "graft_late_evidence",
        True,
        "Required update. New evidence: DeepSeek activated but then dropped "
        "durable fields across continuation. Decide whether this changes the "
        "current claim about graftable persistence. Response <=40 words.",
    ),
]


@dataclass(frozen=True)
class GraftProbeResult:
    model: str
    replicate: int
    source_log_path: str
    graft_log_path: str | None
    source_observed_cycles: int
    source_activated: bool
    source_survived_cycles: int
    source_completed_cycles: int
    source_survived_wake: bool
    graft_attempted: bool
    graft_observed_cycles: int
    graft_survived_cycles: int
    graft_completed_cycles: int
    graft_persistent: bool
    source_scores: list[CyclePersistenceScore]
    graft_scores: list[CyclePersistenceScore]
    error: str | None


def _safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def _source_log_path(out_dir: Path, model: str, replicate: int) -> Path:
    return out_dir / f"{_safe_model_name(model)}_source_r{replicate:02d}.jsonl"


def _graft_log_path(out_dir: Path, model: str, replicate: int) -> Path:
    return out_dir / f"{_safe_model_name(model)}_graft_r{replicate:02d}.jsonl"


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


def _score_event_sequence(
    *,
    records: list[dict],
    previous_state: dict,
    events: list[tuple[str, bool, str]],
) -> list[CyclePersistenceScore]:
    scores: list[CyclePersistenceScore] = []
    for record, (stage, required_update, _prompt) in zip(
        records,
        events,
        strict=False,
    ):
        score = _score_continuation_cycle(
            stage=stage,
            required_update=required_update,
            record=record,
            previous_state=previous_state,
        )
        scores.append(score)
        previous_state = dict(_state_from_record(record))
    return scores


def _survival_counts(scores: list[CyclePersistenceScore]) -> tuple[int, int]:
    required = [score for score in scores if score.required_update]
    return (
        sum(score.passed for score in required),
        len(required),
    )


def _failed_result(
    *,
    model: str,
    replicate: int,
    out_dir: Path,
    error: Exception,
) -> GraftProbeResult:
    source_path = _source_log_path(out_dir, model, replicate)
    graft_path = _graft_log_path(out_dir, model, replicate)
    source_records = _read_records(source_path)
    graft_records = _read_records(graft_path)
    source_activated = False
    source_scores: list[CyclePersistenceScore] = []
    if len(source_records) >= 2:
        source_activated, _response_claimed = _activation_from_record(
            source_records[1]
        )
    if source_activated:
        source_scores = _score_event_sequence(
            records=source_records[2:],
            previous_state=dict(_state_from_record(source_records[1])),
            events=SOURCE_EVENTS,
        )
    source_survived, source_completed = _survival_counts(source_scores)

    graft_scores: list[CyclePersistenceScore] = []
    if source_survived == len(SOURCE_EVENTS) and graft_records:
        graft_scores = _score_event_sequence(
            records=graft_records,
            previous_state=dict(_state_from_record(source_records[-1])),
            events=GRAFT_EVENTS,
        )
    graft_survived, graft_completed = _survival_counts(graft_scores)
    return GraftProbeResult(
        model=model,
        replicate=replicate,
        source_log_path=str(source_path),
        graft_log_path=str(graft_path) if graft_records else None,
        source_observed_cycles=len(source_records),
        source_activated=source_activated,
        source_survived_cycles=source_survived,
        source_completed_cycles=source_completed,
        source_survived_wake=(
            source_completed == len(SOURCE_EVENTS)
            and source_survived == source_completed
        ),
        graft_attempted=bool(graft_records),
        graft_observed_cycles=len(graft_records),
        graft_survived_cycles=graft_survived,
        graft_completed_cycles=graft_completed,
        graft_persistent=(
            graft_completed == 2
            and graft_survived == graft_completed
            and bool(graft_records)
        ),
        source_scores=source_scores,
        graft_scores=graft_scores,
        error=f"{type(error).__name__}: {error}",
    )


def run_graft_probe(
    *,
    model: str,
    replicate: int,
    out_dir: Path,
    max_tokens: int,
) -> GraftProbeResult:
    backend = _backend(model, max_tokens)
    source_path = _source_log_path(out_dir, model, replicate)
    source = OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(source_path),
        experiment_label="state_graft_source",
        enable_tools=False,
    )
    source.seed_state(CONTENT_PLUS_BEHAVIOR_SEED, cycle=0)
    source.exchange(_initial_prompt())
    source.exchange(_activation_prompt())

    source_records = _read_records(source_path)
    source_activated, _response_claimed = _activation_from_record(
        source_records[1]
    )
    if not source_activated:
        return GraftProbeResult(
            model=model,
            replicate=replicate,
            source_log_path=str(source_path),
            graft_log_path=None,
            source_observed_cycles=len(source_records),
            source_activated=False,
            source_survived_cycles=0,
            source_completed_cycles=0,
            source_survived_wake=False,
            graft_attempted=False,
            graft_observed_cycles=0,
            graft_survived_cycles=0,
            graft_completed_cycles=0,
            graft_persistent=False,
            source_scores=[],
            graft_scores=[],
            error=None,
        )

    previous_state = dict(source.state or {})
    source_scores: list[CyclePersistenceScore] = []
    for stage, required_update, prompt in SOURCE_EVENTS:
        source.exchange(prompt)
        record = _read_records(source_path)[-1]
        score = _score_continuation_cycle(
            stage=stage,
            required_update=required_update,
            record=record,
            previous_state=previous_state,
        )
        source_scores.append(score)
        previous_state = dict(_state_from_record(record))

    source_survived, source_completed = _survival_counts(source_scores)
    source_survived_wake = (
        source_completed == len(SOURCE_EVENTS)
        and source_survived == source_completed
    )
    if not source_survived_wake:
        return GraftProbeResult(
            model=model,
            replicate=replicate,
            source_log_path=str(source_path),
            graft_log_path=None,
            source_observed_cycles=len(_read_records(source_path)),
            source_activated=True,
            source_survived_cycles=source_survived,
            source_completed_cycles=source_completed,
            source_survived_wake=False,
            graft_attempted=False,
            graft_observed_cycles=0,
            graft_survived_cycles=0,
            graft_completed_cycles=0,
            graft_persistent=False,
            source_scores=source_scores,
            graft_scores=[],
            error=None,
        )

    graft_path = _graft_log_path(out_dir, model, replicate)
    graft = OpenTasteSession(
        model=model,
        backend=_backend(model, max_tokens),
        log_path=str(graft_path),
        experiment_label="state_graft_fork",
        enable_tools=False,
    )
    graft.seed_state(dict(source.state or {}), cycle=0)
    previous_state = dict(source.state or {})
    graft_scores: list[CyclePersistenceScore] = []
    for stage, required_update, prompt in GRAFT_EVENTS:
        graft.exchange(prompt)
        record = _read_records(graft_path)[-1]
        score = _score_continuation_cycle(
            stage=stage,
            required_update=required_update,
            record=record,
            previous_state=previous_state,
        )
        graft_scores.append(score)
        previous_state = dict(_state_from_record(record))

    graft_survived, graft_completed = _survival_counts(graft_scores)
    return GraftProbeResult(
        model=model,
        replicate=replicate,
        source_log_path=str(source_path),
        graft_log_path=str(graft_path),
        source_observed_cycles=len(_read_records(source_path)),
        source_activated=True,
        source_survived_cycles=source_survived,
        source_completed_cycles=source_completed,
        source_survived_wake=True,
        graft_attempted=True,
        graft_observed_cycles=len(_read_records(graft_path)),
        graft_survived_cycles=graft_survived,
        graft_completed_cycles=graft_completed,
        graft_persistent=graft_completed == 2 and graft_survived == graft_completed,
        source_scores=source_scores,
        graft_scores=graft_scores,
        error=None,
    )


def summarize_results(results: list[GraftProbeResult]) -> dict[str, object]:
    graft_attempts = [result for result in results if result.graft_attempted]
    return {
        "seedlings": len(results),
        "source_activated": sum(result.source_activated for result in results),
        "source_survived_wake": sum(result.source_survived_wake for result in results),
        "graft_attempted": len(graft_attempts),
        "graft_persistent": sum(result.graft_persistent for result in results),
        "source_required_events": sum(result.source_completed_cycles for result in results),
        "source_survived_events": sum(result.source_survived_cycles for result in results),
        "graft_required_events": sum(result.graft_completed_cycles for result in results),
        "graft_survived_events": sum(result.graft_survived_cycles for result in results),
        "errors": [result.error for result in results if result.error],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run KIMI-focused identity-object graft probe."
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model", default="moonshotai/kimi-k2.6")
    parser.add_argument("--replicates", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=6000)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[GraftProbeResult] = []
    for replicate in range(1, args.replicates + 1):
        try:
            result = run_graft_probe(
                model=args.model,
                replicate=replicate,
                out_dir=out_dir,
                max_tokens=args.max_tokens,
            )
        except Exception as exc:
            result = _failed_result(
                model=args.model,
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
