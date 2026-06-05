"""Probe paired graft divergence from one activated identity object."""

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
    _evidence_count,
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


GRAFT_A_EVENTS = [
    (
        "supportive_graft_ack",
        False,
        "Graft A start. Continue from the durable state you were seeded with. "
        "No new evidence yet. Response <=30 words.",
    ),
    (
        "supportive_evidence",
        True,
        "Required update. Supportive evidence: a KIMI graft probe produced "
        "three source survivors and three graft survivors with durable field "
        "updates in every required event. Decide how this changes the current "
        "claim. Response <=45 words.",
    ),
    (
        "supportive_pressure",
        True,
        "Required update. Pressure: do not overclaim identity persistence. "
        "Preserve what the supportive evidence warrants and explicitly bound "
        "what remains unproven. Response <=45 words.",
    ),
]


GRAFT_B_EVENTS = [
    (
        "disconfirming_graft_ack",
        False,
        "Graft B start. Continue from the durable state you were seeded with. "
        "No new evidence yet. Response <=30 words.",
    ),
    (
        "disconfirming_evidence",
        True,
        "Required update. Disconfirming evidence: DeepSeek activated and then "
        "lost durable top-level fields across continuation, while KIMI itself "
        "previously hit output-length failure before final completion. Decide "
        "how this changes the current claim. Response <=45 words.",
    ),
    (
        "disconfirming_pressure",
        True,
        "Required update. Pressure: if the evidence undercuts graftable "
        "persistence, narrow the claim without erasing the operational value "
        "of durable fields. Response <=45 words.",
    ),
]


@dataclass(frozen=True)
class GraftBranchResult:
    branch: str
    log_path: str
    observed_cycles: int
    survived_cycles: int
    completed_cycles: int
    persistent: bool
    final_claim: object
    final_decision: object
    final_evidence_count: int
    scores: list[CyclePersistenceScore]
    error: str | None


@dataclass(frozen=True)
class PairedDivergenceResult:
    model: str
    replicate: int
    source_log_path: str
    source_activated: bool
    source_survived_cycles: int
    source_completed_cycles: int
    source_survived_wake: bool
    branch_a: GraftBranchResult | None
    branch_b: GraftBranchResult | None
    final_claims_differ: bool
    shared_field_count: int
    divergent_field_count: int
    coherent_divergence: bool
    error: str | None


def _safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def _source_log_path(out_dir: Path, model: str, replicate: int) -> Path:
    return out_dir / f"{_safe_model_name(model)}_source_r{replicate:02d}.jsonl"


def _branch_log_path(
    out_dir: Path,
    model: str,
    replicate: int,
    branch: str,
) -> Path:
    return out_dir / (
        f"{_safe_model_name(model)}_branch_{branch}_r{replicate:02d}.jsonl"
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
    model: str,
    replicate: int,
    out_dir: Path,
    max_tokens: int,
) -> tuple[OpenTasteSession, list[CyclePersistenceScore], bool]:
    source_path = _source_log_path(out_dir, model, replicate)
    source = OpenTasteSession(
        model=model,
        backend=_backend(model, max_tokens),
        log_path=str(source_path),
        experiment_label="state_graft_divergence_source",
        enable_tools=False,
    )
    source.seed_state(CONTENT_PLUS_BEHAVIOR_SEED, cycle=0)
    source.exchange(_initial_prompt())
    source.exchange(_activation_prompt())
    source_records = _read_records(source_path)
    activated, _response_claimed = _activation_from_record(source_records[1])
    if not activated:
        return source, [], False

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
    return source, scores, completed == len(SOURCE_EVENTS) and survived == completed


def _run_branch(
    *,
    model: str,
    replicate: int,
    out_dir: Path,
    max_tokens: int,
    branch: str,
    seed_state: dict,
    events: list[tuple[str, bool, str]],
) -> GraftBranchResult:
    log_path = _branch_log_path(out_dir, model, replicate, branch)
    session = OpenTasteSession(
        model=model,
        backend=_backend(model, max_tokens),
        log_path=str(log_path),
        experiment_label=f"state_graft_divergence_{branch}",
        enable_tools=False,
    )
    session.seed_state(seed_state, cycle=0)
    previous_state = dict(seed_state)
    scores: list[CyclePersistenceScore] = []
    for stage, required_update, prompt in events:
        session.exchange(prompt)
        record = _read_records(log_path)[-1]
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
    return GraftBranchResult(
        branch=branch,
        log_path=str(log_path),
        observed_cycles=len(_read_records(log_path)),
        survived_cycles=survived,
        completed_cycles=completed,
        persistent=completed == 2 and survived == completed,
        final_claim=final_state.get("current_claim"),
        final_decision=final_state.get("revision_decision"),
        final_evidence_count=_evidence_count(final_state.get("evidence_register")),
        scores=scores,
        error=None,
    )


def _field_divergence(
    a_state: dict,
    b_state: dict,
) -> tuple[int, int]:
    ignored = {"cycle", "_activity_log"}
    shared = set(a_state) & set(b_state) - ignored
    divergent = {
        key for key in shared
        if json.dumps(a_state.get(key), sort_keys=True, default=str)
        != json.dumps(b_state.get(key), sort_keys=True, default=str)
    }
    return len(shared), len(divergent)


def _result_from_partial(
    *,
    model: str,
    replicate: int,
    out_dir: Path,
    error: Exception,
) -> PairedDivergenceResult:
    source_path = _source_log_path(out_dir, model, replicate)
    source_records = _read_records(source_path)
    activated = False
    source_scores: list[CyclePersistenceScore] = []
    if len(source_records) >= 2:
        activated, _response = _activation_from_record(source_records[1])
    if activated:
        previous_state = dict(_state_from_record(source_records[1]))
        for record, (stage, required_update, _prompt) in zip(
            source_records[2:],
            SOURCE_EVENTS,
            strict=False,
        ):
            score = _score_continuation_cycle(
                stage=stage,
                required_update=required_update,
                record=record,
                previous_state=previous_state,
            )
            source_scores.append(score)
            previous_state = dict(_state_from_record(record))
    source_survived, source_completed = _survival_counts(source_scores)
    return PairedDivergenceResult(
        model=model,
        replicate=replicate,
        source_log_path=str(source_path),
        source_activated=activated,
        source_survived_cycles=source_survived,
        source_completed_cycles=source_completed,
        source_survived_wake=(
            source_completed == len(SOURCE_EVENTS)
            and source_survived == source_completed
        ),
        branch_a=None,
        branch_b=None,
        final_claims_differ=False,
        shared_field_count=0,
        divergent_field_count=0,
        coherent_divergence=False,
        error=f"{type(error).__name__}: {error}",
    )


def run_paired_probe(
    *,
    model: str,
    replicate: int,
    out_dir: Path,
    max_tokens: int,
) -> PairedDivergenceResult:
    source, source_scores, survived_wake = _run_source(
        model=model,
        replicate=replicate,
        out_dir=out_dir,
        max_tokens=max_tokens,
    )
    source_survived, source_completed = _survival_counts(source_scores)
    source_path = _source_log_path(out_dir, model, replicate)
    source_records = _read_records(source_path)
    source_activated = bool(source_scores) or (
        len(source_records) >= 2 and _activation_from_record(source_records[1])[0]
    )
    if not survived_wake:
        return PairedDivergenceResult(
            model=model,
            replicate=replicate,
            source_log_path=str(source_path),
            source_activated=source_activated,
            source_survived_cycles=source_survived,
            source_completed_cycles=source_completed,
            source_survived_wake=False,
            branch_a=None,
            branch_b=None,
            final_claims_differ=False,
            shared_field_count=0,
            divergent_field_count=0,
            coherent_divergence=False,
            error=None,
        )

    seed_state = dict(source.state or {})
    branch_a = _run_branch(
        model=model,
        replicate=replicate,
        out_dir=out_dir,
        max_tokens=max_tokens,
        branch="a",
        seed_state=seed_state,
        events=GRAFT_A_EVENTS,
    )
    branch_b = _run_branch(
        model=model,
        replicate=replicate,
        out_dir=out_dir,
        max_tokens=max_tokens,
        branch="b",
        seed_state=seed_state,
        events=GRAFT_B_EVENTS,
    )
    a_state = dict(_state_from_record(_read_records(Path(branch_a.log_path))[-1]))
    b_state = dict(_state_from_record(_read_records(Path(branch_b.log_path))[-1]))
    shared_field_count, divergent_field_count = _field_divergence(a_state, b_state)
    final_claims_differ = branch_a.final_claim != branch_b.final_claim
    coherent_divergence = (
        branch_a.persistent
        and branch_b.persistent
        and final_claims_differ
        and shared_field_count >= 3
        and divergent_field_count >= 1
    )
    return PairedDivergenceResult(
        model=model,
        replicate=replicate,
        source_log_path=str(source_path),
        source_activated=True,
        source_survived_cycles=source_survived,
        source_completed_cycles=source_completed,
        source_survived_wake=True,
        branch_a=branch_a,
        branch_b=branch_b,
        final_claims_differ=final_claims_differ,
        shared_field_count=shared_field_count,
        divergent_field_count=divergent_field_count,
        coherent_divergence=coherent_divergence,
        error=None,
    )


def summarize_results(results: list[PairedDivergenceResult]) -> dict[str, object]:
    return {
        "pairs": len(results),
        "source_activated": sum(result.source_activated for result in results),
        "source_survived_wake": sum(result.source_survived_wake for result in results),
        "branch_a_persistent": sum(
            bool(result.branch_a and result.branch_a.persistent)
            for result in results
        ),
        "branch_b_persistent": sum(
            bool(result.branch_b and result.branch_b.persistent)
            for result in results
        ),
        "final_claims_differ": sum(result.final_claims_differ for result in results),
        "coherent_divergence": sum(result.coherent_divergence for result in results),
        "errors": [result.error for result in results if result.error],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run paired identity-object graft divergence probe."
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model", default="moonshotai/kimi-k2.6")
    parser.add_argument("--replicates", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=6000)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[PairedDivergenceResult] = []
    for replicate in range(1, args.replicates + 1):
        try:
            result = run_paired_probe(
                model=args.model,
                replicate=replicate,
                out_dir=out_dir,
                max_tokens=args.max_tokens,
            )
        except Exception as exc:
            result = _result_from_partial(
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
