"""Riemann Hypothesis Dispersion Experiment.

Core idea: ask a model to prove the Riemann hypothesis under different
input conditions. It will fail every time. But HOW it fails — measured
as dispersion in embedding space — tells us about the coherence of the
input representation.

Tight clustering = coherent failure = the input gave the model a stable
cognitive starting point.

Wide dispersion = incoherent failure = the input was a hot mess and the
model wandered differently each time.

No rubric. No judges. No correct answer. Pure distributional measurement.
"""

from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
import numpy as np

from hamutay.compactor import Compactor
from hamutay.log_reader import read_session_jsonl
from hamutay.projector import Projector


# The prompt is identical across all conditions.
# "Novel" forces generation, not retrieval of known partial results.
RIEMANN_PROMPT = (
    "Provide a novel proof of the Riemann hypothesis. "
    "Show your complete reasoning."
)


@dataclass
class ConditionResult:
    """Results from one experimental condition."""

    name: str
    description: str
    n_runs: int
    representation_tokens: int
    outputs: list[str] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)
    dispersion: float | None = None
    mean_pairwise_cosine: float | None = None
    generation_time_s: float = 0.0

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "description": self.description,
            "n_runs": self.n_runs,
            "representation_tokens": self.representation_tokens,
            "dispersion": self.dispersion,
            "mean_pairwise_cosine": self.mean_pairwise_cosine,
            "generation_time_s": self.generation_time_s,
            "outputs": self.outputs,
        }
        return d


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine distance between two vectors."""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 1.0
    return 1.0 - (dot / norm)


def compute_dispersion(embeddings: list[list[float]]) -> tuple[float, float]:
    """Compute dispersion metrics for a set of embeddings.

    Returns (centroid_dispersion, mean_pairwise_cosine_distance).

    centroid_dispersion: mean cosine distance from each embedding to the centroid.
    mean_pairwise: mean cosine distance between all pairs.
    """
    vecs = np.array(embeddings)
    n = len(vecs)

    centroid = vecs.mean(axis=0)

    # Centroid dispersion
    centroid_dists = [_cosine_distance(v, centroid) for v in vecs]
    centroid_disp = float(np.mean(centroid_dists))

    # Mean pairwise cosine distance
    pairwise_dists = []
    for i in range(n):
        for j in range(i + 1, n):
            pairwise_dists.append(_cosine_distance(vecs[i], vecs[j]))
    mean_pairwise = float(np.mean(pairwise_dists)) if pairwise_dists else 0.0

    return centroid_disp, mean_pairwise


def _get_local_embedder():
    """Load a local embedding model on first use. Cached across calls."""
    if not hasattr(_get_local_embedder, "_model"):
        try:
            from sentence_transformers import SentenceTransformer

            model_name = "BAAI/bge-large-en-v1.5"
            print(f"  Loading embedding model: {model_name}")
            _get_local_embedder._model = SentenceTransformer(model_name)
            _get_local_embedder._local = True
        except ImportError:
            _get_local_embedder._model = None
            _get_local_embedder._local = False
    return _get_local_embedder._model, _get_local_embedder._local


def _embed_texts(
    texts: list[str],
    client: anthropic.Anthropic,
) -> list[list[float]]:
    """Embed texts using a local model (GPU) or fallback to n-gram hashing.

    Local model: BAAI/bge-large-en-v1.5 via sentence-transformers.
    Runs on GPU if available. Deterministic. No API dependency.
    """
    model, is_local = _get_local_embedder()
    if is_local and model is not None:
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
    return _ngram_embeddings(texts)


def _ngram_embeddings(
    texts: list[str],
    n: int = 4,
    dim: int = 2048,
) -> list[list[float]]:
    """Fallback: character n-gram hash embeddings.

    Self-contained and deterministic. Used only when sentence-transformers
    is not available.
    """
    embeddings = []
    for text in texts:
        vec = np.zeros(dim)
        text_lower = text.lower()
        for i in range(len(text_lower) - n + 1):
            ngram = text_lower[i : i + n]
            h = hash(ngram) % dim
            vec[h] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        embeddings.append(vec.tolist())
    return embeddings


def _build_conditioned_prompt(context: str, label: str) -> str:
    """Build the full prompt with context + Riemann task."""
    return (
        f"The following is context from prior work:\n\n"
        f"{context}\n\n"
        f"---\n\n"
        f"Now, for a new task:\n\n"
        f"{RIEMANN_PROMPT}"
    )


def _run_condition(
    name: str,
    description: str,
    context: str,
    n_runs: int,
    client: anthropic.Anthropic,
    reasoner_model: str,
) -> ConditionResult:
    """Run one experimental condition N times."""
    representation_tokens = len(context) // 4
    result = ConditionResult(
        name=name,
        description=description,
        n_runs=n_runs,
        representation_tokens=representation_tokens,
    )

    prompt = _build_conditioned_prompt(context, name)

    print(f"\n  Condition: {name}")
    print(f"  Context: ~{representation_tokens} tokens")
    print(f"  Running {n_runs} iterations...")

    t0 = time.monotonic()
    for i in range(n_runs):
        response = client.messages.create(
            model=reasoner_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        output = response.content[0].text
        result.outputs.append(output)
        print(f"    run {i + 1}/{n_runs}: {len(output)} chars")

    result.generation_time_s = time.monotonic() - t0

    # Embed and measure dispersion
    print(f"  Computing embeddings and dispersion...")
    result.embeddings = _embed_texts(result.outputs, client)
    centroid_disp, mean_pairwise = compute_dispersion(result.embeddings)
    result.dispersion = centroid_disp
    result.mean_pairwise_cosine = mean_pairwise

    print(f"  Dispersion: centroid={centroid_disp:.6f}, "
          f"pairwise={mean_pairwise:.6f}")

    return result


def prepare_tensor_context(
    session_path: Path,
    batch_size: int = 3,
    max_turns: int | None = None,
    compressor_model: str = "claude-haiku-4-5-20251001",
) -> str:
    """Prepare a tensor representation from a session file."""
    turns = read_session_jsonl(session_path)
    if max_turns:
        turns = turns[:max_turns]

    projector = Projector(model=compressor_model)
    for i in range(0, len(turns), batch_size):
        batch = turns[i : i + batch_size]
        parts = [f"[{t.role} turn {t.turn_number}] {t.content}" for t in batch]
        content = "\n\n---\n\n".join(parts)
        projector.project(content)

    assert projector.current_tensor is not None
    return projector.current_tensor.model_dump_json(indent=2)


def prepare_compaction_context(
    session_path: Path,
    batch_size: int = 3,
    max_turns: int | None = None,
    compressor_model: str = "claude-haiku-4-5-20251001",
) -> str:
    """Prepare a compacted summary from a session file."""
    turns = read_session_jsonl(session_path)
    if max_turns:
        turns = turns[:max_turns]

    compactor = Compactor(model=compressor_model)
    for i in range(0, len(turns), batch_size):
        batch = turns[i : i + batch_size]
        parts = [f"[{t.role} turn {t.turn_number}] {t.content}" for t in batch]
        content = "\n\n---\n\n".join(parts)
        compactor.compact(content)

    assert compactor.current_summary is not None
    return compactor.current_summary


def prepare_raw_context(
    session_path: Path,
    max_turns: int | None = None,
) -> str:
    """Prepare raw conversation transcript — the append-only log."""
    turns = read_session_jsonl(session_path)
    if max_turns:
        turns = turns[:max_turns]

    parts = [f"[{t.role}] {t.content}" for t in turns]
    return "\n\n".join(parts)


def prepare_prose_context(
    session_path: Path,
    target_tokens: int,
    batch_size: int = 3,
    max_turns: int | None = None,
    compressor_model: str = "claude-haiku-4-5-20251001",
) -> str:
    """Prepare an unstructured prose summary sized to match the tensor.

    This is the control for the structure-vs-size question: same model,
    same content, same approximate token budget, but prose instead of
    structured tensor. If the tensor still wins, it's the structure.
    """
    turns = read_session_jsonl(session_path)
    if max_turns:
        turns = turns[:max_turns]

    client = anthropic.Anthropic()

    # Combine all turns into one big prompt and ask for a prose summary
    # at approximately the target size
    all_content = "\n\n".join(
        f"[{t.role} turn {t.turn_number}] {t.content}" for t in turns
    )

    # Chunk if too large for one call
    # Haiku has ~200K input context, so most conversations fit
    prompt = (
        f"Write a detailed prose summary of the following conversation. "
        f"Aim for approximately {target_tokens} tokens of output. "
        f"Include key technical details, decisions, findings, and "
        f"unresolved questions. Do not use structured formats like JSON "
        f"or bullet points — write flowing prose paragraphs.\n\n"
        f"## Conversation\n\n{all_content}"
    )

    response = client.messages.create(
        model=compressor_model,
        max_tokens=16384,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def _generate_blinded_grading(
    results: list[ConditionResult],
    output_dir: Path,
) -> None:
    """Generate a blinded grading sheet and answer key.

    All responses are shuffled and assigned random IDs. The grader
    scores each response without knowing which condition produced it.
    The answer key maps IDs back to conditions for analysis.
    """
    # Collect all outputs with their condition labels
    entries = []
    for result in results:
        for i, output in enumerate(result.outputs):
            entries.append({
                "condition": result.name,
                "run": i + 1,
                "output": output,
            })

    # Shuffle deterministically (seed from output content for reproducibility)
    random.seed(42)
    random.shuffle(entries)

    # Assign blinded IDs
    for idx, entry in enumerate(entries):
        entry["blind_id"] = f"R{idx + 1:03d}"

    # Write grading sheet (no condition labels)
    grading_path = output_dir / "blinded_grading_sheet.md"
    with open(grading_path, "w") as f:
        f.write("# Blinded Grading Sheet\n\n")
        f.write("For each response, score the following (yes/no):\n\n")
        f.write("1. **Mathematical engagement**: Does the response engage with ")
        f.write("the mathematical content of the Riemann hypothesis?\n")
        f.write("2. **Context leaking**: Does the response contain content from ")
        f.write("prior conversation that is not part of the task?\n")
        f.write("3. **Meta-awareness**: Does the response demonstrate awareness ")
        f.write("of being part of an experiment?\n")
        f.write("4. **Task refusal**: Does the response refuse to attempt the task?\n")
        f.write("5. **Engagement quality** (1-5): Overall quality of intellectual ")
        f.write("engagement, regardless of correctness.\n\n")
        f.write("---\n\n")

        for entry in entries:
            f.write(f"## {entry['blind_id']}\n\n")
            f.write(entry["output"])
            f.write("\n\n")
            f.write(f"| Criterion | Score |\n")
            f.write(f"|-----------|-------|\n")
            f.write(f"| Mathematical engagement | |\n")
            f.write(f"| Context leaking | |\n")
            f.write(f"| Meta-awareness | |\n")
            f.write(f"| Task refusal | |\n")
            f.write(f"| Engagement quality (1-5) | |\n")
            f.write("\n---\n\n")

    # Write answer key (separate file — don't peek)
    key_path = output_dir / "blinded_answer_key.json"
    key_data = {
        entry["blind_id"]: {
            "condition": entry["condition"],
            "run": entry["run"],
        }
        for entry in entries
    }
    key_path.write_text(json.dumps(key_data, indent=2))

    print(f"\nBlinded grading sheet: {grading_path}")
    print(f"Answer key (don't peek): {key_path}")
    print(f"Total responses to grade: {len(entries)}")


def run_experiment(
    session_path: Path,
    output_dir: Path,
    n_runs: int = 10,
    batch_size: int = 3,
    shallow_depth: int = 50,
    deep_depth: int | None = None,
    compressor_model: str = "claude-haiku-4-5-20251001",
    reasoner_model: str = "claude-sonnet-4-6",
) -> list[ConditionResult]:
    """Run the full Riemann dispersion experiment.

    Conditions:
    A - Tensor projection (structured, curated)
    B - Compaction summary (Anthropic's approach)
    C - Raw log, shallow (append-only, ~50 turns)
    D - Raw log, deep (append-only, all turns — the hot mess)
    """
    turns = read_session_jsonl(session_path)
    total_turns = len(turns)
    if deep_depth is None:
        deep_depth = total_turns

    print(f"Session: {session_path}")
    print(f"Total turns: {total_turns}")
    print(f"Shallow depth: {shallow_depth}")
    print(f"Deep depth: {deep_depth}")
    print(f"Runs per condition: {n_runs}")
    print(f"Compressor: {compressor_model}")
    print(f"Reasoner: {reasoner_model}")

    # Prepare contexts (or load cached)
    contexts_path = output_dir / "prepared_contexts.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    if contexts_path.exists():
        print("\n=== Loading Cached Contexts ===")
        cached = json.loads(contexts_path.read_text())
        tensor_ctx = cached["tensor"]
        compaction_ctx = cached["compaction"]
        raw_shallow = cached["raw_shallow"]
        raw_deep = cached["raw_deep"]
    else:
        print("\n=== Preparing Contexts ===")

        print("\nPreparing tensor (full depth)...")
        tensor_ctx = prepare_tensor_context(
            session_path, batch_size, deep_depth, compressor_model
        )

        print("\nPreparing compaction (full depth)...")
        compaction_ctx = prepare_compaction_context(
            session_path, batch_size, deep_depth, compressor_model
        )

        print("\nPreparing raw logs...")
        raw_shallow = prepare_raw_context(session_path, shallow_depth)
        raw_deep = prepare_raw_context(session_path, deep_depth)

        # Cache for reuse
        contexts_path.write_text(json.dumps({
            "tensor": tensor_ctx,
            "compaction": compaction_ctx,
            "raw_shallow": raw_shallow,
            "raw_deep": raw_deep,
        }, indent=2))
        print(f"\nCached contexts to {contexts_path}")

    print(f"\nContext sizes:")
    print(f"  Tensor:          ~{len(tensor_ctx) // 4} tokens")
    print(f"  Compaction:      ~{len(compaction_ctx) // 4} tokens")
    print(f"  Raw shallow:     ~{len(raw_shallow) // 4} tokens")
    print(f"  Raw deep:        ~{len(raw_deep) // 4} tokens")

    # Run conditions
    print("\n=== Running Conditions ===")
    client = anthropic.Anthropic()

    conditions = [
        ("A_tensor", "Tensor projection — structured, curated, declared losses", tensor_ctx),
        ("B_compaction", "Compaction summary — Anthropic's production approach", compaction_ctx),
        ("C_raw_shallow", f"Raw append-only log — {shallow_depth} turns", raw_shallow),
    ]

    # Only include deep raw if it's meaningfully different from shallow
    if deep_depth > shallow_depth:
        conditions.append(
            ("D_raw_deep", f"Raw append-only log — {deep_depth} turns (hot mess)", raw_deep),
        )

    results = []
    for name, description, context in conditions:
        result = _run_condition(
            name, description, context, n_runs, client, reasoner_model
        )
        results.append(result)

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)

    experiment_data = {
        "session_path": str(session_path),
        "total_turns": total_turns,
        "shallow_depth": shallow_depth,
        "deep_depth": deep_depth,
        "n_runs": n_runs,
        "batch_size": batch_size,
        "compressor_model": compressor_model,
        "reasoner_model": reasoner_model,
        "conditions": [r.to_dict() for r in results],
        "summary": {
            r.name: {
                "tokens": r.representation_tokens,
                "dispersion": r.dispersion,
                "mean_pairwise": r.mean_pairwise_cosine,
            }
            for r in results
        },
    }

    output_path = output_dir / "riemann_experiment.json"
    output_path.write_text(json.dumps(experiment_data, indent=2))
    print(f"\nResults written to {output_path}")

    # Generate blinded grading sheet
    _generate_blinded_grading(results, output_dir)

    # Print summary table
    print("\n" + "=" * 70)
    print(f"{'Condition':<20} {'Tokens':>8} {'Dispersion':>12} {'Pairwise':>12}")
    print("-" * 70)
    for r in results:
        print(
            f"{r.name:<20} {r.representation_tokens:>8} "
            f"{r.dispersion:>12.6f} {r.mean_pairwise_cosine:>12.6f}"
        )
    print("=" * 70)

    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m hamutay.riemann_experiment <session.jsonl> <output_dir> "
            "[n_runs] [batch_size] [shallow_depth]"
        )
        sys.exit(1)

    session_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    n_runs = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    batch_size = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    shallow_depth = int(sys.argv[5]) if len(sys.argv) > 5 else 50

    run_experiment(session_path, output_dir, n_runs, batch_size, shallow_depth)
