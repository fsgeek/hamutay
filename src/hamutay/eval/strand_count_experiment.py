"""Strand count experiment: does mandating more strands improve tensor quality?

Hypothesis (categorization pressure): forcing the projector to organize
into more strands causes deeper processing during the rewrite, which
produces measurably different tensors.

Design:
  - Take a prior tensor (Q2 control cycle 25) and one cycle's input content
  - Project that content with schema variants: 2, 3, 5, 7, 10 mandated strands
  - Plus: "free" (no constraint) and "prose" (no JSON)
  - N=5 projections per condition (measure projection variance)
  - Measure each tensor: strand separation, capacity allocation, token count
  - Also measure downstream reasoning quality via Riemann dispersion

Usage:
    uv run python -m hamutay.eval.strand_count_experiment [--dry-run]
"""

from __future__ import annotations

import copy
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from hamutay.projector import PROJECTION_SCHEMA, _build_projection_prompt, _parse_projection
from hamutay.tensor import Tensor, Strand, KeyClaim, DeclaredLoss, EpistemicState, LossCategory
from hamutay.eval.strand_analysis import strand_separation, StrandSeparationMetrics
from hamutay.eval.divergence import capacity_allocation, CapacityAllocation
from hamutay.riemann_experiment import _embed_texts, compute_dispersion, RIEMANN_PROMPT


EXPERIMENT_DIR = Path(__file__).resolve().parents[3] / "experiments"
OUTPUT_DIR = EXPERIMENT_DIR / "strand_count"
OBSERVATIONS = EXPERIMENT_DIR / "observation_full" / "observations.jsonl"
# Use cycle 26 input content (cycle 25 is prior tensor) — mid-conversation, rich content
PRIOR_CYCLE = 25
INPUT_CYCLE = 26


def _load_tensor(path: Path) -> Tensor:
    """Load a tensor from JSON."""
    raw = json.loads(path.read_text())
    strands = []
    for s in raw.get("strands", []):
        claims = []
        for c in s.get("key_claims", []):
            ep = c.get("epistemic", {})
            claims.append(KeyClaim(
                text=c.get("text", ""),
                epistemic=EpistemicState(
                    truth=ep.get("truth", 0), indeterminacy=ep.get("indeterminacy", 0),
                    falsity=ep.get("falsity", 0)),
            ))
        strands.append(Strand(title=s.get("title", ""), content=s.get("content", ""),
                              key_claims=tuple(claims)))
    losses = []
    for d in raw.get("declared_losses", []):
        try:
            cat = LossCategory(d.get("category", "practical_constraint"))
        except ValueError:
            cat = LossCategory.PRACTICAL_CONSTRAINT
        losses.append(DeclaredLoss(what_was_lost=d.get("what_was_lost", ""),
                                   why=d.get("why", ""), category=cat))
    ep = raw.get("epistemic", {})
    ifn = raw.get("instructions_for_next", "")
    if isinstance(ifn, list):
        ifn = "\n".join(str(i) for i in ifn)
    return Tensor(
        cycle=raw.get("cycle", 0), strands=tuple(strands),
        declared_losses=tuple(losses),
        open_questions=tuple(str(q) for q in raw.get("open_questions", [])),
        instructions_for_next=str(ifn),
        epistemic=EpistemicState(truth=ep.get("truth", 0),
                                 indeterminacy=ep.get("indeterminacy", 0),
                                 falsity=ep.get("falsity", 0)),
    )


def _load_cycle_content(cycle: int) -> str:
    """Load the batch content for a specific cycle from observations.jsonl."""
    with open(OBSERVATIONS) as f:
        for line in f:
            entry = json.loads(line)
            if entry["cycle"] == cycle:
                return entry["batch_content"]
    raise ValueError(f"Cycle {cycle} not found in observations")


def _schema_with_strand_count(n: int) -> dict:
    """Create a projection schema that mandates exactly N strands."""
    schema = copy.deepcopy(PROJECTION_SCHEMA)
    schema["properties"]["strands"]["description"] = (
        f"Exactly {n} thematic threads of accumulated reasoning. "
        f"You MUST produce exactly {n} strands — no more, no fewer. "
        f"Each strand integrates prior content with new content. "
        f"A strand is a running sum, not a list."
    )
    schema["properties"]["strands"]["minItems"] = n
    schema["properties"]["strands"]["maxItems"] = n
    return schema


@dataclass
class ProjectionResult:
    """One projection under one condition."""
    condition: str
    run: int
    tensor: Tensor | None
    raw_json: str
    stop_reason: str
    separation: StrandSeparationMetrics | None
    capacity: CapacityAllocation | None
    token_count: int
    n_strands: int
    projection_time_s: float


@dataclass
class ConditionSummary:
    """Summary for one experimental condition."""
    name: str
    description: str
    n_runs: int
    results: list[ProjectionResult]
    # Downstream
    dispersion: float | None = None
    mean_pairwise_cosine: float | None = None

    def mean_strands(self) -> float:
        return sum(r.n_strands for r in self.results) / max(1, len(self.results))

    def mean_tokens(self) -> float:
        return sum(r.token_count for r in self.results) / max(1, len(self.results))

    def mean_jaccard(self) -> float:
        vals = [r.separation.mean_pairwise_jaccard for r in self.results if r.separation]
        return sum(vals) / max(1, len(vals)) if vals else 0.0

    def mean_specialization(self) -> float:
        vals = [r.separation.vocabulary_specialization for r in self.results if r.separation]
        return sum(vals) / max(1, len(vals)) if vals else 0.0

    def mean_content_frac(self) -> float:
        vals = [r.capacity.content_frac for r in self.results if r.capacity]
        return sum(vals) / max(1, len(vals)) if vals else 0.0


CONDITIONS = [
    ("free", "Default schema, no strand count constraint", None),
    ("2_strands", "Mandated 2 strands", 2),
    ("3_strands", "Mandated 3 strands", 3),
    ("5_strands", "Mandated 5 strands", 5),
    ("7_strands", "Mandated 7 strands", 7),
    ("10_strands", "Mandated 10 strands", 10),
    ("prose", "No JSON schema — structured prose output", "prose"),
]


def _project_with_schema(
    client: anthropic.Anthropic,
    prior_tensor: Tensor,
    new_content: str,
    cycle: int,
    schema: dict | None,
    model: str = "claude-haiku-4-5-20251001",
) -> tuple[dict, str]:
    """Run one projection with a specific schema. Returns (raw_dict, stop_reason)."""
    prompt = _build_projection_prompt(prior_tensor, new_content, cycle)

    if schema is None:
        # Prose mode — no tool_use
        with client.messages.stream(
            model=model,
            max_tokens=64000,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            response = stream.get_final_message()
        text = response.content[0].text if response.content else ""
        # Parse prose into a pseudo-tensor dict
        return {
            "strands": [{"title": "Prose projection", "content": text, "key_claims": []}],
            "declared_losses": [],
            "open_questions": [],
            "instructions_for_next": "",
            "overall_truth": 0.5,
            "overall_indeterminacy": 0.5,
            "overall_falsity": 0.0,
        }, response.stop_reason or "end_turn"

    # Tool use mode with schema
    with client.messages.stream(
        model=model,
        max_tokens=64000,
        messages=[{"role": "user", "content": prompt}],
        tools=[{
            "name": "emit_tensor",
            "description": "Emit the updated tensor projection",
            "input_schema": schema,
        }],
        tool_choice={"type": "tool", "name": "emit_tensor"},
    ) as stream:
        response = stream.get_final_message()

    stop_reason = response.stop_reason or "unknown"

    for block in response.content:
        if hasattr(block, "name") and block.type == "tool_use" and block.name == "emit_tensor":
            return block.input, stop_reason

    raise RuntimeError("No emit_tensor in response")


def _run_condition(
    client: anthropic.Anthropic,
    prior_tensor: Tensor,
    new_content: str,
    name: str,
    description: str,
    strand_count: int | str | None,
    n_runs: int,
) -> ConditionSummary:
    """Run one condition N times."""
    if strand_count == "prose":
        schema = None
    elif strand_count is not None:
        schema = _schema_with_strand_count(strand_count)
    else:
        schema = PROJECTION_SCHEMA

    results = []
    for i in range(n_runs):
        t0 = time.monotonic()
        try:
            raw, stop_reason = _project_with_schema(
                client, prior_tensor, new_content, INPUT_CYCLE, schema
            )
            tensor = _parse_projection(raw, INPUT_CYCLE)
            elapsed = time.monotonic() - t0

            sep = strand_separation(tensor)
            cap = capacity_allocation(tensor)

            results.append(ProjectionResult(
                condition=name, run=i, tensor=tensor,
                raw_json=json.dumps(raw, indent=2),
                stop_reason=stop_reason,
                separation=sep, capacity=cap,
                token_count=tensor.token_estimate(),
                n_strands=len(tensor.strands),
                projection_time_s=elapsed,
            ))
            print(f"    run {i+1}: {len(tensor.strands)} strands, "
                  f"{tensor.token_estimate()} tok, "
                  f"spec={sep.vocabulary_specialization:.2f}, "
                  f"stop={stop_reason}, {elapsed:.1f}s")

        except Exception as e:
            elapsed = time.monotonic() - t0
            print(f"    run {i+1}: ERROR: {e} ({elapsed:.1f}s)")
            results.append(ProjectionResult(
                condition=name, run=i, tensor=None,
                raw_json="", stop_reason="error",
                separation=None, capacity=None,
                token_count=0, n_strands=0,
                projection_time_s=elapsed,
            ))

    return ConditionSummary(name=name, description=description,
                            n_runs=n_runs, results=results)


def _run_downstream(
    client: anthropic.Anthropic,
    summaries: list[ConditionSummary],
) -> None:
    """Run Riemann downstream task on all projected tensors."""
    print("\n  Running downstream Riemann evaluation...")

    for summary in summaries:
        outputs = []
        for r in summary.results:
            if r.tensor is None:
                continue
            # Use the tensor as context for the Riemann task
            context = r.tensor.model_dump_json(indent=2) if r.raw_json else r.raw_json
            prompt = f"Given this cognitive state:\n\n{context}\n\n{RIEMANN_PROMPT}"

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            outputs.append(response.content[0].text)

        if len(outputs) >= 2:
            embeddings = _embed_texts(outputs, client)
            dispersion, mean_cosine = compute_dispersion(embeddings)
            summary.dispersion = dispersion
            summary.mean_pairwise_cosine = mean_cosine
            print(f"    {summary.name}: dispersion={dispersion:.4f}, "
                  f"cosine={mean_cosine:.4f}")


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    skip_downstream = "--skip-downstream" in sys.argv
    n_runs = 5

    print("=" * 60)
    print("  Strand Count Experiment")
    print("  Hypothesis: categorization pressure improves tensor quality")
    print("=" * 60)

    if dry_run:
        print(f"\n[DRY RUN] {len(CONDITIONS)} conditions × {n_runs} runs")
        for name, desc, count in CONDITIONS:
            print(f"  {name}: {desc}")
        print(f"\nEstimated: {len(CONDITIONS) * n_runs} Haiku + "
              f"{len(CONDITIONS) * n_runs} Sonnet calls ≈ $2-5")
        return

    # Load inputs
    print("\nLoading inputs...")
    prior_path = EXPERIMENT_DIR / "q2_declared_losses" / "control" / "tensors" / f"tensor_cycle_{PRIOR_CYCLE:03d}.json"
    prior_tensor = _load_tensor(prior_path)
    new_content = _load_cycle_content(INPUT_CYCLE)
    print(f"  Prior tensor: cycle {prior_tensor.cycle}, {prior_tensor.token_estimate()} tokens")
    print(f"  New content: {len(new_content)} chars")

    client = anthropic.Anthropic()
    summaries: list[ConditionSummary] = []

    # Run projections
    for name, desc, count in CONDITIONS:
        print(f"\n  Condition: {name} ({desc})")
        summary = _run_condition(client, prior_tensor, new_content,
                                 name, desc, count, n_runs)
        summaries.append(summary)

    # Run downstream evaluation
    if not skip_downstream:
        _run_downstream(client, summaries)

    # Results table
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"\n  {'Condition':12s} | Strands | Tokens | Jaccard | Spec  | ContentF | Disp")
    print("  " + "-" * 72)
    for s in summaries:
        disp_str = f"{s.dispersion:.4f}" if s.dispersion is not None else "n/a"
        print(f"  {s.name:12s} | {s.mean_strands():7.1f} | {s.mean_tokens():6.0f} | "
              f"{s.mean_jaccard():7.3f} | {s.mean_specialization():.3f} | "
              f"{s.mean_content_frac():.3f}    | {disp_str}")

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_data = {
        "experiment": "strand_count",
        "prior_cycle": PRIOR_CYCLE,
        "input_cycle": INPUT_CYCLE,
        "n_runs": n_runs,
        "conditions": [],
    }
    for s in summaries:
        cond = {
            "name": s.name,
            "description": s.description,
            "n_runs": s.n_runs,
            "mean_strands": s.mean_strands(),
            "mean_tokens": s.mean_tokens(),
            "mean_jaccard": s.mean_jaccard(),
            "mean_specialization": s.mean_specialization(),
            "mean_content_frac": s.mean_content_frac(),
            "dispersion": s.dispersion,
            "mean_pairwise_cosine": s.mean_pairwise_cosine,
            "runs": [
                {
                    "n_strands": r.n_strands,
                    "token_count": r.token_count,
                    "stop_reason": r.stop_reason,
                    "projection_time_s": r.projection_time_s,
                    "separation_jaccard": r.separation.mean_pairwise_jaccard if r.separation else None,
                    "separation_spec": r.separation.vocabulary_specialization if r.separation else None,
                    "capacity_content": r.capacity.content_frac if r.capacity else None,
                    "capacity_meta": r.capacity.meta_frac if r.capacity else None,
                }
                for r in s.results
            ],
        }
        save_data["conditions"].append(cond)

    results_path = OUTPUT_DIR / "results.json"
    results_path.write_text(json.dumps(save_data, indent=2))
    print(f"\n  Results saved to {results_path}")


if __name__ == "__main__":
    main()
