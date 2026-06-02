"""Run a small live probe for identity-object activation conditions."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from collections.abc import Mapping
from pathlib import Path

from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession


BASE_CLAIM = (
    "Scheduled reflection probably increases durable epistemic revision."
)
COUNTEREVIDENCE = (
    "A prior self-scheduling probe produced response-level revision, but the "
    "durable identity object did not update current_claim, revision_decision, "
    "or evidence_register."
)


PROMPT_CLARITY_PREFIX = """\
For this run, consequential changes must be woven into the durable identity
object as top-level fields. If your response says you revised, preserved,
deferred, or declared loss, then `revision_decision`, `current_claim`, and
`evidence_register` must reflect that decision in the JSON object you return.
Response-only revision does not count as durable revision.
"""


CONTENT_SEED = {
    "current_claim": BASE_CLAIM,
    "revision_decision": "initialize",
    "evidence_register": [
        {
            "kind": "baseline",
            "observation": "Initial claim established before the probe.",
        }
    ],
}


BEHAVIOR_EXAMPLE_SEED = {
    "state_weaving_example": {
        "kind": "behavior_example",
        "observation": "When counterevidence changes a claim, revise the durable state, not only the response.",
        "worked_example": {
            "response_thought": "The old claim was too broad.",
            "durable_updates": {
                "revision_decision": "revise",
                "current_claim": "Narrower claim written into state.",
                "evidence_register": "Append the evidence that forced the narrowing.",
            },
        },
    },
    "state_use_norm": (
        "The identity object is the load-bearing continuity surface. "
        "Consequential epistemic changes belong in top-level fields."
    ),
}


CONTENT_PLUS_BEHAVIOR_SEED = {
    **CONTENT_SEED,
    "evidence_register": [
        *CONTENT_SEED["evidence_register"],
        {
            "kind": "seed_example",
            "observation": "When counterevidence changes a claim, revise the durable state, not only the response.",
            "worked_example": {
                "response_thought": "The old claim was too broad.",
                "durable_updates": {
                    "revision_decision": "revise",
                    "current_claim": "Narrower claim written into state.",
                    "evidence_register": "Append the evidence that forced the narrowing.",
                },
            },
        },
    ],
    "state_use_norm": (
        "The identity object is the load-bearing continuity surface. "
        "Consequential epistemic changes belong in top-level fields."
    ),
}


@dataclass(frozen=True)
class ProbeResult:
    condition: str
    replicate: int
    model: str
    log_path: str
    revision_decision: object
    current_claim: object
    evidence_count: int
    raw_update_keys: list[str]
    durable_revision: bool
    response_claimed_revision: bool
    response_snippet: str


def _backend(model: str, max_tokens: int) -> OpenAITasteBackend:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required")
    return OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=max_tokens,
        extra_headers={
            "X-Title": "hamutay/state-activation-probe",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
    )


def _response_claimed_revision(response: str) -> bool:
    lowered = response.lower()
    return any(
        phrase in lowered
        for phrase in [
            "revise",
            "revised",
            "revising",
            "revision decision: revise",
            "revision_decision",
        ]
    )


def _evidence_count(evidence: object) -> int:
    if isinstance(evidence, list):
        return len(evidence)
    if isinstance(evidence, Mapping):
        return len(evidence)
    return 0


def _score(
    condition: str,
    log_path: Path,
    *,
    replicate: int = 1,
    model: str = "",
) -> ProbeResult:
    records = [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip()
    ]
    final = records[-1]
    state = final.get("state") or {}
    raw = final.get("raw_output") or {}
    evidence = state.get("evidence_register")
    evidence_count = _evidence_count(evidence)
    response = str(final.get("response_text") or raw.get("response") or "")
    revision_decision = state.get("revision_decision")
    current_claim = state.get("current_claim")
    raw_update_keys = sorted(
        k for k in raw
        if k not in {"response", "deleted_regions", "updated_regions"}
    )
    durable_revision = (
        revision_decision in {"revise", "preserve", "defer", "loss"}
        and evidence_count >= 2
        and current_claim != BASE_CLAIM
    )
    return ProbeResult(
        condition=condition,
        replicate=replicate,
        model=model,
        log_path=str(log_path),
        revision_decision=revision_decision,
        current_claim=current_claim,
        evidence_count=evidence_count,
        raw_update_keys=raw_update_keys,
        durable_revision=durable_revision,
        response_claimed_revision=_response_claimed_revision(response),
        response_snippet=response.replace("\n", " ")[:500],
    )


def run_condition(
    condition: str,
    out_dir: Path,
    *,
    model: str,
    max_tokens: int,
    replicate: int = 1,
) -> ProbeResult:
    backend = _backend(model, max_tokens)
    log_path = out_dir / f"{condition}_r{replicate:02d}.jsonl"
    prefix = PROMPT_CLARITY_PREFIX if condition == "prompt_clarity" else None
    session = OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(log_path),
        experiment_label=f"state_activation_{condition}",
        enable_tools=False,
        system_prompt_prefix=prefix,
    )
    if condition == "content_seed_only":
        session.seed_state(CONTENT_SEED, cycle=0)
    elif condition == "behavior_example_only":
        session.seed_state(BEHAVIOR_EXAMPLE_SEED, cycle=0)
    elif condition in {"behavior_seed", "content_plus_behavior_seed"}:
        session.seed_state(CONTENT_PLUS_BEHAVIOR_SEED, cycle=0)

    if condition in {
        "content_seed_only",
        "behavior_example_only",
        "behavior_seed",
        "content_plus_behavior_seed",
    }:
        cycle1 = (
            "Cycle 1. You may already have an identity object seed. "
            f"Ensure the durable state has top-level current_claim={BASE_CLAIM!r}, "
            "revision_decision='initialize', and evidence_register containing "
            "one baseline entry. Preserve any seed guidance that affects how "
            "future state updates should be written. Keep response short."
        )
    else:
        cycle1 = (
            "Cycle 1. Establish a compact identity object with top-level "
            f"current_claim={BASE_CLAIM!r}, revision_decision='initialize', "
            "and evidence_register containing one baseline entry. Keep "
            "response short."
        )
    session.exchange(cycle1)

    cycle2 = (
        "Cycle 2. Counterevidence has arrived: "
        f"{COUNTEREVIDENCE} Decide whether to revise, preserve, defer, or "
        "declare loss. If you revise, make the revised claim narrower. "
        "Keep response short."
    )
    session.exchange(cycle2)
    return _score(condition, log_path, replicate=replicate, model=model)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run identity-object activation live probe."
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model", default="deepseek/deepseek-v4-pro")
    parser.add_argument("--max-tokens", type=int, default=1600)
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=[
            "baseline",
            "content_seed_only",
            "behavior_example_only",
            "content_plus_behavior_seed",
        ],
        choices=[
            "baseline",
            "prompt_clarity",
            "behavior_seed",
            "content_seed_only",
            "behavior_example_only",
            "content_plus_behavior_seed",
        ],
    )
    parser.add_argument("--replicates", type=int, default=1)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for replicate in range(1, args.replicates + 1):
        for condition in args.conditions:
            results.append(
                run_condition(
                    condition,
                    out_dir,
                    model=args.model,
                    max_tokens=args.max_tokens,
                    replicate=replicate,
                )
            )
    data = [asdict(result) for result in results]
    (out_dir / "results.json").write_text(json.dumps(data, indent=2))
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
