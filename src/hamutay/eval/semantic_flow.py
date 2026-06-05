"""Embedding-based semantic flow analysis for tensor rewrites.

This is the A2 check from the paper roadmap: compare consecutive tensor
states with a real sentence-transformer embedding model, not bag-of-words
cosine and not cross-condition similarity.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from hamutay.eval.content_flow import (
    _extract_content,
    _extract_meta,
    analyze_consecutive_flow,
)


@dataclass(frozen=True)
class SemanticFlowRecord:
    """Embedding similarity between two consecutive tensor states."""

    prior_cycle: int
    cycle: int
    batch_tokens: int | None
    content_similarity: float
    meta_similarity: float
    full_similarity: float
    ngram_survival: float


def load_observation_tensors(path: Path) -> list[dict]:
    """Load tensor records from an observation JSONL file."""
    tensors: list[dict] = []
    with path.open() as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            tensor = record.get("tensor")
            if not isinstance(tensor, dict):
                continue
            tensor = dict(tensor)
            tensor["_batch_tokens"] = record.get("batch_tokens")
            tensors.append(tensor)
    return tensors


def _embed_texts(model, texts: list[str]) -> np.ndarray:
    """Embed texts with a real sentence-transformer model."""
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(embeddings, dtype=float)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity for normalized embeddings."""
    return float(np.dot(a, b))


def _summarize(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        "min": float(np.min(arr)),
        "p25": float(np.percentile(arr, 25)),
        "median": float(np.percentile(arr, 50)),
        "p75": float(np.percentile(arr, 75)),
        "max": float(np.max(arr)),
    }


def analyze_semantic_flow(
    tensors: list[dict],
    *,
    model_name: str = "BAAI/bge-large-en-v1.5",
) -> list[SemanticFlowRecord]:
    """Compute consecutive-cycle semantic similarity for tensor content."""
    if len(tensors) < 2:
        return []

    content_texts = [_extract_content(t) for t in tensors]
    meta_texts = [_extract_meta(t) for t in tensors]
    full_texts = [
        f"{content}\n\n{meta}"
        for content, meta in zip(content_texts, meta_texts)
    ]

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    content_embeddings = _embed_texts(model, content_texts)
    meta_embeddings = _embed_texts(model, meta_texts)
    full_embeddings = _embed_texts(model, full_texts)

    ngram_records = analyze_consecutive_flow(tensors)
    records: list[SemanticFlowRecord] = []
    for i in range(1, len(tensors)):
        prior = tensors[i - 1]
        current = tensors[i]
        ngram = ngram_records[i - 1]
        records.append(
            SemanticFlowRecord(
                prior_cycle=int(prior.get("cycle", i - 1)),
                cycle=int(current.get("cycle", i)),
                batch_tokens=current.get("_batch_tokens"),
                content_similarity=_cosine(
                    content_embeddings[i - 1], content_embeddings[i]
                ),
                meta_similarity=_cosine(meta_embeddings[i - 1], meta_embeddings[i]),
                full_similarity=_cosine(full_embeddings[i - 1], full_embeddings[i]),
                ngram_survival=ngram.content_survival_rate,
            )
        )
    return records


def render_markdown(
    records: list[SemanticFlowRecord],
    *,
    source: Path,
    model_name: str,
) -> str:
    """Render a compact paper-audit artifact."""
    if not records:
        return "# Embedding Similarity Analysis\n\nNo consecutive records found.\n"

    content = _summarize([r.content_similarity for r in records])
    meta = _summarize([r.meta_similarity for r in records])
    full = _summarize([r.full_similarity for r in records])
    ngram = _summarize([r.ngram_survival for r in records])

    batch_tokens = [r.batch_tokens or 0 for r in records]
    similarities = [r.content_similarity for r in records]
    batch_corr = (
        float(np.corrcoef(batch_tokens, similarities)[0, 1])
        if len(records) > 1 and len(set(batch_tokens)) > 1
        else 0.0
    )

    def row(label: str, stats: dict[str, float]) -> str:
        return (
            f"| {label} | {stats['mean']:.3f} | {stats['std']:.3f} | "
            f"{stats['min']:.3f} | {stats['p25']:.3f} | {stats['median']:.3f} | "
            f"{stats['p75']:.3f} | {stats['max']:.3f} |"
        )

    lowest = sorted(records, key=lambda r: r.content_similarity)[:5]
    highest = sorted(records, key=lambda r: r.content_similarity, reverse=True)[:5]

    lines = [
        "# Embedding Similarity Analysis",
        "",
        f"Source: `{source}`",
        f"Embedding model: `{model_name}`",
        f"Transitions: {len(records)}",
        "",
        "## Summary",
        "",
        "| Measure | Mean | Std | Min | P25 | Median | P75 | Max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        row("Content embedding cosine", content),
        row("Meta embedding cosine", meta),
        row("Full tensor embedding cosine", full),
        row("Content 3-gram survival", ngram),
        "",
        f"Batch-token/content-embedding Pearson r: `{batch_corr:.3f}`",
        "",
        "## Lowest Content Similarity Transitions",
        "",
        "| Prior -> Cycle | Batch tokens | Content cosine | 3-gram survival |",
        "|---|---:|---:|---:|",
    ]
    for r in lowest:
        lines.append(
            f"| {r.prior_cycle} -> {r.cycle} | {r.batch_tokens or 0} | "
            f"{r.content_similarity:.3f} | {r.ngram_survival:.3f} |"
        )

    lines.extend([
        "",
        "## Highest Content Similarity Transitions",
        "",
        "| Prior -> Cycle | Batch tokens | Content cosine | 3-gram survival |",
        "|---|---:|---:|---:|",
    ])
    for r in highest:
        lines.append(
            f"| {r.prior_cycle} -> {r.cycle} | {r.batch_tokens or 0} | "
            f"{r.content_similarity:.3f} | {r.ngram_survival:.3f} |"
        )

    lines.extend([
        "",
        "## Interpretation Boundary",
        "",
        "This measures consecutive-cycle tensor-to-tensor embedding similarity. "
        "It does not measure cross-condition similarity and does not prove that "
        "every important fact survived; it tests the narrower A2 companion claim "
        "that semantic content remains close while surface structure rewrites.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze consecutive-cycle tensor embedding similarity."
    )
    parser.add_argument("observations", type=Path)
    parser.add_argument(
        "--model",
        default="BAAI/bge-large-en-v1.5",
        help="Sentence-transformer model name.",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    tensors = load_observation_tensors(args.observations)
    records = analyze_semantic_flow(tensors, model_name=args.model)
    markdown = render_markdown(
        records,
        source=args.observations,
        model_name=args.model,
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
