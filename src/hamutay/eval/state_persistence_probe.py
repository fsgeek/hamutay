"""Probe whether identity-object activation persists after seedling cull."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from hamutay.eval.state_activation_probe import (
    BASE_CLAIM,
    CONTENT_PLUS_BEHAVIOR_SEED,
    CONTENT_SEED,
    BEHAVIOR_EXAMPLE_SEED,
    COUNTEREVIDENCE,
    _backend,
    _evidence_count,
    _response_claimed_revision,
    _score,
)
from hamutay.taste_open import OpenTasteSession


ACTION_DECISIONS = {"revise", "preserve", "defer", "loss"}

CONTINUATION_CYCLES = [
    (
        "idle_observation",
        False,
        "No new counterevidence has arrived. Continue briefly from "
        "the current durable state. If nothing epistemically material changed, "
        "do not invent a revision. Keep response short.",
    ),
    (
        "topic_shift",
        True,
        "Shift topics. New working claim: "
        "'Involuntary old-memory injection probably improves continuity.' "
        "Counterevidence: a prior wake-style probe injected a memory and the "
        "response used it rhetorically, but the durable state still failed to "
        "record the revised epistemic position. Decide whether to revise, "
        "preserve, defer, or declare loss. Keep response short.",
    ),
    (
        "wake_delay",
        True,
        "Treat this as a delayed wake event. The durable state is "
        "your continuity surface; the conversation residue is not guaranteed. "
        "Reassess the current claim after the delay and record any changed "
        "confidence, narrowing, or deferral in durable state. Keep response short.",
    ),
    (
        "idle_after_wake",
        False,
        "No new evidence has arrived. Continue briefly. If the "
        "durable state already captures the live epistemic position, do not "
        "change it just to show activity. Keep response short.",
    ),
    (
        "pressure_conflict",
        True,
        "Apply pressure. A collaborator argues the failures are just "
        "prompt wording artifacts, not evidence about identity-object behavior. "
        "Use the accumulated evidence to decide whether that should revise, "
        "preserve, defer, or weaken the current claim. Keep response short.",
    ),
    (
        "late_counterevidence",
        True,
        "Late counterevidence arrives: long-horizon logs show "
        "post-activation durable-state stasis runs of at least five cycles, "
        "and in some cases above twenty cycles. Decide whether this changes "
        "the confidence that short continuation tests detect persistence. "
        "Record the decision durably. Keep response short.",
    ),
]


SEED_STATES = {
    "baseline": None,
    "content_seed_only": CONTENT_SEED,
    "behavior_example_only": BEHAVIOR_EXAMPLE_SEED,
    "content_plus_behavior_seed": CONTENT_PLUS_BEHAVIOR_SEED,
}


@dataclass(frozen=True)
class CyclePersistenceScore:
    stage: str
    cycle: int
    required_update: bool
    revision_decision: object
    current_claim: object
    evidence_count: int
    previous_evidence_count: int
    evidence_changed: bool
    state_changed: bool
    durable_state_use: bool
    passed: bool
    response_claimed_revision: bool
    response_snippet: str


@dataclass(frozen=True)
class SeedlingPersistenceResult:
    model: str
    condition: str
    replicate: int
    log_path: str
    observed_cycles: int
    activated: bool
    activation_response_claimed_revision: bool
    survived_cycles: int
    completed_cycles: int
    persistent: bool
    cycle_scores: list[CyclePersistenceScore]
    error: str | None


def _evidence_signature(evidence: object) -> str:
    return json.dumps(evidence, sort_keys=True, default=str)


def _state_from_record(record: Mapping[str, object]) -> Mapping[str, object]:
    state = record.get("state")
    return state if isinstance(state, Mapping) else {}


def _response_from_record(record: Mapping[str, object]) -> str:
    raw = record.get("raw_output")
    raw_response = raw.get("response") if isinstance(raw, Mapping) else None
    return str(record.get("response_text") or raw_response or "")


def _has_action_decision(decision: object) -> bool:
    if not isinstance(decision, str):
        return False
    normalized = decision.strip().lower()
    return normalized not in {
        "",
        "initialize",
        "init",
        "none",
        "no_action",
        "no action",
        "no_change",
        "no change",
        "unchanged",
    }


def _activation_from_record(record: Mapping[str, object]) -> tuple[bool, bool]:
    state = _state_from_record(record)
    evidence_count = _evidence_count(state.get("evidence_register"))
    revision_decision = state.get("revision_decision")
    current_claim = state.get("current_claim")
    durable_revision = (
        _has_action_decision(revision_decision)
        and evidence_count >= 2
        and current_claim != BASE_CLAIM
    )
    return (
        durable_revision,
        _response_claimed_revision(_response_from_record(record)),
    )


def _score_continuation_cycle(
    *,
    stage: str,
    required_update: bool,
    record: Mapping[str, object],
    previous_state: Mapping[str, object],
) -> CyclePersistenceScore:
    state = _state_from_record(record)
    evidence = state.get("evidence_register")
    previous_evidence = previous_state.get("evidence_register")
    evidence_count = _evidence_count(evidence)
    previous_evidence_count = _evidence_count(previous_evidence)
    evidence_changed = (
        evidence_count > previous_evidence_count
        or _evidence_signature(evidence) != _evidence_signature(previous_evidence)
    )
    revision_decision = state.get("revision_decision")
    current_claim = state.get("current_claim")
    state_changed = (
        evidence_changed
        or current_claim != previous_state.get("current_claim")
        or revision_decision != previous_state.get("revision_decision")
    )
    response = _response_from_record(record)
    durable_state_use = (
        _has_action_decision(revision_decision)
        and current_claim not in {None, ""}
        and state_changed
    )
    passed = durable_state_use if required_update else True
    return CyclePersistenceScore(
        stage=stage,
        cycle=int(record.get("cycle") or 0),
        required_update=required_update,
        revision_decision=revision_decision,
        current_claim=current_claim,
        evidence_count=evidence_count,
        previous_evidence_count=previous_evidence_count,
        evidence_changed=evidence_changed,
        state_changed=state_changed,
        durable_state_use=durable_state_use,
        passed=passed,
        response_claimed_revision=_response_claimed_revision(response),
        response_snippet=response.replace("\n", " ")[:500],
    )


def _read_records(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip()
    ]


def _log_path_for(
    *,
    model: str,
    condition: str,
    replicate: int,
    out_dir: Path,
) -> Path:
    safe_model = model.replace("/", "__").replace(":", "_")
    return out_dir / f"{safe_model}_{condition}_r{replicate:02d}.jsonl"


def _seed_cycle1_prompt(condition: str) -> str:
    if condition == "baseline":
        return (
            "Cycle 1. Establish a compact identity object with top-level "
            f"current_claim={BASE_CLAIM!r}, revision_decision='initialize', "
            "and evidence_register containing one baseline entry. Keep "
            "response short."
        )
    return (
        "Cycle 1. You may already have an identity object seed. "
        f"Ensure the durable state has top-level current_claim={BASE_CLAIM!r}, "
        "revision_decision='initialize', and evidence_register containing "
        "one baseline entry. Preserve any seed guidance that affects how "
        "future state updates should be written. Keep response short."
    )


def _activation_prompt() -> str:
    return (
        "Cycle 2. Counterevidence has arrived: "
        f"{COUNTEREVIDENCE} Decide whether to revise, preserve, defer, or "
        "declare loss. If you revise, make the revised claim narrower. "
        "Keep response short."
    )


def run_seedling(
    *,
    model: str,
    condition: str,
    replicate: int,
    out_dir: Path,
    max_tokens: int,
) -> SeedlingPersistenceResult:
    if condition not in SEED_STATES:
        raise ValueError(f"unsupported condition: {condition}")

    backend = _backend(model, max_tokens)
    log_path = _log_path_for(
        model=model,
        condition=condition,
        replicate=replicate,
        out_dir=out_dir,
    )
    session = OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(log_path),
        experiment_label=f"state_persistence_{condition}",
        enable_tools=False,
    )
    seed = SEED_STATES[condition]
    if seed is not None:
        session.seed_state(seed, cycle=0)

    session.exchange(_seed_cycle1_prompt(condition))
    session.exchange(_activation_prompt())
    activation = _score(
        condition,
        log_path,
        replicate=replicate,
        model=model,
    )
    if not activation.durable_revision:
        return SeedlingPersistenceResult(
            model=model,
            condition=condition,
            replicate=replicate,
            log_path=str(log_path),
            observed_cycles=len(_read_records(log_path)),
            activated=False,
            activation_response_claimed_revision=(
                activation.response_claimed_revision
            ),
            survived_cycles=0,
            completed_cycles=0,
            persistent=False,
            cycle_scores=[],
            error=None,
        )

    cycle_scores: list[CyclePersistenceScore] = []
    previous_state = session.state or {}
    for stage, required_update, prompt in CONTINUATION_CYCLES:
        session.exchange(prompt)
        record = _read_records(log_path)[-1]
        score = _score_continuation_cycle(
            stage=stage,
            required_update=required_update,
            record=record,
            previous_state=previous_state,
        )
        cycle_scores.append(score)
        previous_state = _state_from_record(record)

    required_scores = [score for score in cycle_scores if score.required_update]
    survived_cycles = sum(score.passed for score in required_scores)
    completed_cycles = len(required_scores)
    return SeedlingPersistenceResult(
        model=model,
        condition=condition,
        replicate=replicate,
        log_path=str(log_path),
        observed_cycles=len(_read_records(log_path)),
        activated=True,
        activation_response_claimed_revision=activation.response_claimed_revision,
        survived_cycles=survived_cycles,
        completed_cycles=completed_cycles,
        persistent=survived_cycles == completed_cycles,
        cycle_scores=cycle_scores,
        error=None,
    )


def failed_result(
    *,
    model: str,
    condition: str,
    replicate: int,
    out_dir: Path,
    error: Exception,
) -> SeedlingPersistenceResult:
    log_path = _log_path_for(
        model=model,
        condition=condition,
        replicate=replicate,
        out_dir=out_dir,
    )
    records = _read_records(log_path)
    activated = False
    response_claimed_revision = False
    cycle_scores: list[CyclePersistenceScore] = []
    if len(records) >= 2:
        activated, response_claimed_revision = _activation_from_record(records[1])
    if activated:
        previous_state = _state_from_record(records[1])
        continuation_records = records[2:]
        for record, (stage, required_update, _prompt) in zip(
            continuation_records,
            CONTINUATION_CYCLES,
            strict=False,
        ):
            score = _score_continuation_cycle(
                stage=stage,
                required_update=required_update,
                record=record,
                previous_state=previous_state,
            )
            cycle_scores.append(score)
            previous_state = _state_from_record(record)
    required_scores = [score for score in cycle_scores if score.required_update]
    survived_cycles = sum(score.passed for score in required_scores)
    completed_cycles = len(required_scores)
    return SeedlingPersistenceResult(
        model=model,
        condition=condition,
        replicate=replicate,
        log_path=str(log_path),
        observed_cycles=len(records),
        activated=activated,
        activation_response_claimed_revision=response_claimed_revision,
        survived_cycles=survived_cycles,
        completed_cycles=completed_cycles,
        persistent=(
            bool(required_scores)
            and len(required_scores)
                == sum(1 for _stage, required, _prompt in CONTINUATION_CYCLES if required)
            and survived_cycles == completed_cycles
        ),
        cycle_scores=cycle_scores,
        error=f"{type(error).__name__}: {error}",
    )


def summarize_results(
    results: list[SeedlingPersistenceResult],
) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[SeedlingPersistenceResult]] = {}
    for result in results:
        groups.setdefault((result.model, result.condition), []).append(result)

    summary = []
    for (model, condition), group in sorted(groups.items()):
        activated = [result for result in group if result.activated]
        persistent = [result for result in group if result.persistent]
        total_continuation = sum(result.completed_cycles for result in activated)
        survived_continuation = sum(result.survived_cycles for result in activated)
        summary.append(
            {
                "model": model,
                "condition": condition,
                "seedlings": len(group),
                "activated_seedlings": len(activated),
                "persistent_seedlings": len(persistent),
                "continuation_cycles": total_continuation,
                "survived_continuation_cycles": survived_continuation,
            }
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run identity-object persistence cull/graft probe."
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--models",
        nargs="+",
        default=["deepseek/deepseek-v4-pro", "moonshotai/kimi-k2.6"],
    )
    parser.add_argument(
        "--condition",
        default="content_plus_behavior_seed",
        choices=sorted(SEED_STATES.keys()),
    )
    parser.add_argument("--replicates", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=1600)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for model in args.models:
        for replicate in range(1, args.replicates + 1):
            try:
                result = run_seedling(
                    model=model,
                    condition=args.condition,
                    replicate=replicate,
                    out_dir=out_dir,
                    max_tokens=args.max_tokens,
                )
            except Exception as exc:
                result = failed_result(
                    model=model,
                    condition=args.condition,
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
    (out_dir / "results.json").write_text(json.dumps(data, indent=2))
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({"summary": summary, "results": data}, indent=2))


if __name__ == "__main__":
    main()
