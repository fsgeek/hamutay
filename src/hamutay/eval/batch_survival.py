"""Batch-size regression for tensor rewrite survival.

This is the B2 check from the paper roadmap: quantify how much new input
batch size predicts lexical survival across consecutive tensor rewrites.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from hamutay.eval.content_flow import analyze_consecutive_flow
from hamutay.eval.semantic_flow import load_observation_tensors


@dataclass(frozen=True)
class RegressionResult:
    """Simple least-squares regression result."""

    intercept: float
    slope: float
    r_squared: float
    pearson_r: float


def _linear_regression(x: np.ndarray, y: np.ndarray) -> RegressionResult:
    """Fit y = intercept + slope*x."""
    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    ss_x = float(np.sum((x - x_mean) ** 2))
    if ss_x == 0:
        return RegressionResult(y_mean, 0.0, 0.0, 0.0)

    slope = float(np.sum((x - x_mean) * (y - y_mean)) / ss_x)
    intercept = y_mean - slope * x_mean
    predicted = intercept + slope * x
    ss_res = float(np.sum((y - predicted) ** 2))
    ss_tot = float(np.sum((y - y_mean) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot else 0.0
    pearson_r = float(np.corrcoef(x, y)[0, 1]) if len(x) > 1 else 0.0
    return RegressionResult(intercept, slope, r_squared, pearson_r)


def analyze_batch_survival(tensors: list[dict]) -> dict:
    """Return regression and bin summaries for batch size vs survival."""
    flow = analyze_consecutive_flow(tensors)
    batch_tokens: list[int] = []
    survival: list[float] = []
    title_persistence: list[float] = []

    for i, record in enumerate(flow, start=1):
        batch = tensors[i].get("_batch_tokens")
        if batch is None:
            continue
        batch_tokens.append(int(batch))
        survival.append(record.content_survival_rate)
        title_persistence.append(
            record.titles_shared / record.strands_prior
            if record.strands_prior else 0.0
        )

    x = np.asarray(batch_tokens, dtype=float)
    y = np.asarray(survival, dtype=float)
    titles = np.asarray(title_persistence, dtype=float)
    log_x = np.log1p(x)

    def summarize_mask(mask: np.ndarray) -> dict:
        return {
            "n": int(np.sum(mask)),
            "mean_batch_tokens": float(np.mean(x[mask])),
            "mean_survival": float(np.mean(y[mask])),
            "mean_title_persistence": float(np.mean(titles[mask])),
        }

    bins = {
        "incremental_lt_500": summarize_mask(x < 500),
        "middle_500_to_2000": summarize_mask((x >= 500) & (x <= 2000)),
        "reorg_gt_2000": summarize_mask(x > 2000),
    }

    linear = _linear_regression(x, y)
    log_linear = _linear_regression(log_x, y)
    title_log_linear = _linear_regression(log_x, titles)

    return {
        "n_transitions": len(batch_tokens),
        "linear_batch_tokens": linear,
        "log_batch_tokens": log_linear,
        "log_batch_tokens_title_persistence": title_log_linear,
        "bins": bins,
    }


def render_markdown(result: dict, *, source: Path) -> str:
    """Render a compact regression artifact."""
    linear: RegressionResult = result["linear_batch_tokens"]
    log_linear: RegressionResult = result["log_batch_tokens"]
    title_log: RegressionResult = result["log_batch_tokens_title_persistence"]

    lines = [
        "# Batch Size vs Rewrite Survival",
        "",
        f"Source: `{source}`",
        f"Transitions with batch size: {result['n_transitions']}",
        "",
        "## Regression",
        "",
        "| Model | Slope | Intercept | Pearson r | R^2 |",
        "|---|---:|---:|---:|---:|",
        (
            f"| content_survival ~ batch_tokens | {linear.slope:.8f} | "
            f"{linear.intercept:.4f} | {linear.pearson_r:.3f} | "
            f"{linear.r_squared:.3f} |"
        ),
        (
            f"| content_survival ~ log1p(batch_tokens) | {log_linear.slope:.4f} | "
            f"{log_linear.intercept:.4f} | {log_linear.pearson_r:.3f} | "
            f"{log_linear.r_squared:.3f} |"
        ),
        (
            f"| title_persistence ~ log1p(batch_tokens) | {title_log.slope:.4f} | "
            f"{title_log.intercept:.4f} | {title_log.pearson_r:.3f} | "
            f"{title_log.r_squared:.3f} |"
        ),
        "",
        "## Bins",
        "",
        "| Bin | n | Mean batch tokens | Mean 3-gram survival | Mean title persistence |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, stats in result["bins"].items():
        lines.append(
            f"| {name} | {stats['n']} | {stats['mean_batch_tokens']:.1f} | "
            f"{stats['mean_survival']:.3f} | {stats['mean_title_persistence']:.3f} |"
        )

    lines.extend([
        "",
        "## Interpretation Boundary",
        "",
        "The binned effect is large, but simple one-variable regressions explain "
        "only a small share of transition-level variance. Batch size is a real "
        "modulator/confound, not yet a proven dominant predictor.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regress lexical survival against input batch size."
    )
    parser.add_argument("observations", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    tensors = load_observation_tensors(args.observations)
    result = analyze_batch_survival(tensors)
    markdown = render_markdown(result, source=args.observations)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
