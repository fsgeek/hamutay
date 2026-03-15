"""Context window cache simulator.

Replays real conversation traces through different memory management
strategies, producing cost curves and quality proxies. No API calls —
pure accounting over measured data from observation experiments.

Informs the architecture of the projective gateway (Pichay evolution)
before we build it.
"""

from __future__ import annotations

import csv
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegionConfig:
    name: str
    budget_tokens: int
    cache_ttl_s: float  # 0 means uncached


@dataclass
class CacheBlock:
    region: str
    content_id: str
    tokens: int
    inserted_at_s: float
    last_sent_at_s: float

    def is_expired(self, now_s: float, ttl_s: float) -> bool:
        if ttl_s <= 0:
            return True  # uncached — always "expired"
        return (now_s - self.last_sent_at_s) > ttl_s


@dataclass(frozen=True)
class TurnTrace:
    """One cycle from real observation data."""

    turn_number: int
    wall_clock_s: float
    new_content_tokens: int  # batch_tokens
    tensor_tokens: int
    projection_cost_tokens: int  # input tokens for Haiku call
    n_declared_losses: int


@dataclass
class TurnMetrics:
    turn: int
    wall_clock_s: float
    system_tokens: int = 0
    domain_tokens: int = 0
    durable_tokens: int = 0
    ephemeral_tokens: int = 0
    total_context_tokens: int = 0
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0
    cache_write_tokens: int = 0
    token_cost: float = 0.0
    attention_cost: float = 0.0
    projection_cost_tokens: int = 0
    evictions: int = 0
    faults: int = 0
    projected: bool = False

    def total_tokens_in_regions(self) -> int:
        return self.system_tokens + self.domain_tokens + self.durable_tokens + self.ephemeral_tokens


@dataclass
class SimulationResult:
    strategy_name: str
    metrics: list[TurnMetrics] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def compute_summary(self) -> None:
        if not self.metrics:
            return
        self.summary = {
            "strategy": self.strategy_name,
            "turns": len(self.metrics),
            "total_token_cost": sum(m.token_cost for m in self.metrics),
            "total_attention_cost": sum(m.attention_cost for m in self.metrics),
            "total_projection_cost": sum(m.projection_cost_tokens for m in self.metrics),
            "total_evictions": sum(m.evictions for m in self.metrics),
            "total_faults": sum(m.faults for m in self.metrics),
            "projections": sum(1 for m in self.metrics if m.projected),
            "peak_context_tokens": max(m.total_context_tokens for m in self.metrics),
            "mean_context_tokens": sum(m.total_context_tokens for m in self.metrics) / len(self.metrics),
            "final_context_tokens": self.metrics[-1].total_context_tokens,
            "weighted_cost": (
                sum(m.token_cost for m in self.metrics)
                + sum(m.attention_cost for m in self.metrics) * 1e-9  # scale n² to comparable range
                + sum(m.projection_cost_tokens for m in self.metrics) * 1e-3
            ),
        }


# ---------------------------------------------------------------------------
# Memory region
# ---------------------------------------------------------------------------


class MemoryRegion:
    def __init__(self, config: RegionConfig) -> None:
        self.config = config
        self.blocks: list[CacheBlock] = []

    @property
    def total_tokens(self) -> int:
        return sum(b.tokens for b in self.blocks)

    @property
    def budget_remaining(self) -> int:
        return self.config.budget_tokens - self.total_tokens

    def insert(self, block: CacheBlock) -> int:
        """Insert a block, evicting oldest if over budget. Returns eviction count."""
        self.blocks.append(block)
        evictions = 0
        while self.total_tokens > self.config.budget_tokens and len(self.blocks) > 1:
            self.blocks.pop(0)
            evictions += 1
        return evictions

    def expire(self, now_s: float) -> list[CacheBlock]:
        """Remove expired blocks. Returns list of expired blocks."""
        expired = [b for b in self.blocks if b.is_expired(now_s, self.config.cache_ttl_s)]
        self.blocks = [b for b in self.blocks if not b.is_expired(now_s, self.config.cache_ttl_s)]
        return expired

    def clear(self) -> list[CacheBlock]:
        """Remove all blocks. Returns cleared blocks."""
        cleared = self.blocks[:]
        self.blocks = []
        return cleared

    def cache_status(self, now_s: float) -> tuple[int, int]:
        """Returns (hit_tokens, miss_tokens) based on TTL."""
        hit = miss = 0
        for b in self.blocks:
            if self.config.cache_ttl_s > 0 and (now_s - b.last_sent_at_s) <= self.config.cache_ttl_s:
                hit += b.tokens
            else:
                miss += b.tokens
        return hit, miss

    def touch_all(self, now_s: float) -> None:
        """Mark all blocks as sent at now_s (cache refresh)."""
        for b in self.blocks:
            b.last_sent_at_s = now_s


# ---------------------------------------------------------------------------
# Context window — four regions
# ---------------------------------------------------------------------------

# Default region budgets (tokens) — 200K total window
DEFAULT_BUDGET = 200_000
DEFAULT_SYSTEM_BUDGET = 4_000
DEFAULT_DOMAIN_BUDGET = 20_000


@dataclass(frozen=True)
class StrategyDecision:
    project: bool
    evict_from_ephemeral: int = 0  # tokens to force-evict


class ContextWindow:
    def __init__(self, total_budget: int = DEFAULT_BUDGET) -> None:
        durable_budget = 30_000
        ephemeral_budget = total_budget - DEFAULT_SYSTEM_BUDGET - DEFAULT_DOMAIN_BUDGET - durable_budget

        self.regions: dict[str, MemoryRegion] = {
            "system": MemoryRegion(RegionConfig("system", DEFAULT_SYSTEM_BUDGET, 3600.0)),
            "domain": MemoryRegion(RegionConfig("domain", DEFAULT_DOMAIN_BUDGET, 3600.0)),
            "durable": MemoryRegion(RegionConfig("durable", durable_budget, 300.0)),  # 5min
            "ephemeral": MemoryRegion(RegionConfig("ephemeral", ephemeral_budget, 300.0)),  # 5min or uncached
        }
        self.eviction_log: list[CacheBlock] = []

    @property
    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.regions.values())

    def region_tokens(self) -> dict[str, int]:
        return {name: r.total_tokens for name, r in self.regions.items()}


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


class Strategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def on_turn(self, trace: TurnTrace, window: ContextWindow) -> StrategyDecision: ...


class NeverProject(Strategy):
    """All content in ephemeral, evict by age. Pichay baseline."""

    @property
    def name(self) -> str:
        return "NeverProject"

    def on_turn(self, trace: TurnTrace, window: ContextWindow) -> StrategyDecision:
        return StrategyDecision(project=False)


class FixedInterval(Strategy):
    """Project every N turns into durable region."""

    def __init__(self, interval: int = 5) -> None:
        self.interval = interval

    @property
    def name(self) -> str:
        return f"FixedInterval({self.interval})"

    def on_turn(self, trace: TurnTrace, window: ContextWindow) -> StrategyDecision:
        return StrategyDecision(project=(trace.turn_number % self.interval == 0))


class CacheBoundary(Strategy):
    """Project when durable's 5min cache expires."""

    def __init__(self) -> None:
        self.last_projection_s: float = 0.0

    @property
    def name(self) -> str:
        return "CacheBoundary"

    def on_turn(self, trace: TurnTrace, window: ContextWindow) -> StrategyDecision:
        durable_ttl = window.regions["durable"].config.cache_ttl_s
        elapsed = trace.wall_clock_s - self.last_projection_s
        if elapsed >= durable_ttl:
            self.last_projection_s = trace.wall_clock_s
            return StrategyDecision(project=True)
        return StrategyDecision(project=False)


class PressureTriggered(Strategy):
    """Project when ephemeral utilization exceeds threshold."""

    def __init__(self, threshold: float = 0.8) -> None:
        self.threshold = threshold

    @property
    def name(self) -> str:
        return f"PressureTriggered({self.threshold})"

    def on_turn(self, trace: TurnTrace, window: ContextWindow) -> StrategyDecision:
        eph = window.regions["ephemeral"]
        utilization = eph.total_tokens / eph.config.budget_tokens if eph.config.budget_tokens > 0 else 0
        return StrategyDecision(project=(utilization >= self.threshold))


class Adaptive(Strategy):
    """Project when declared_losses count signals the tensor is losing too much."""

    def __init__(self, loss_threshold: int = 5) -> None:
        self.loss_threshold = loss_threshold
        self.accumulated_losses: int = 0

    @property
    def name(self) -> str:
        return f"Adaptive(loss≥{self.loss_threshold})"

    def on_turn(self, trace: TurnTrace, window: ContextWindow) -> StrategyDecision:
        self.accumulated_losses += trace.n_declared_losses
        if self.accumulated_losses >= self.loss_threshold:
            self.accumulated_losses = 0
            return StrategyDecision(project=True)
        return StrategyDecision(project=False)


# ---------------------------------------------------------------------------
# Trace loader
# ---------------------------------------------------------------------------


def load_observation_trace(path: Path, inter_turn_delay_s: float = 60.0) -> list[TurnTrace]:
    """Parse observations.jsonl into TurnTrace records.

    Wall clock is synthesized: each turn advances by inter_turn_delay_s
    plus the actual projection_time_s (which represents real compute time).
    """
    traces: list[TurnTrace] = []
    wall_clock = 0.0

    with open(path) as f:
        for line in f:
            rec = json.loads(line)
            wall_clock += inter_turn_delay_s + rec.get("projection_time_s", 0)
            traces.append(
                TurnTrace(
                    turn_number=rec["cycle"],
                    wall_clock_s=wall_clock,
                    new_content_tokens=rec["batch_tokens"],
                    tensor_tokens=rec["tensor_tokens"],
                    projection_cost_tokens=rec["batch_tokens"] + rec.get("tensor_tokens", 0),
                    n_declared_losses=rec["n_losses"],
                )
            )

    return traces


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------


def simulate(
    traces: list[TurnTrace],
    strategy: Strategy,
    total_budget: int = DEFAULT_BUDGET,
) -> SimulationResult:
    """Run one strategy against the trace data."""
    window = ContextWindow(total_budget)
    result = SimulationResult(strategy_name=strategy.name)

    # Seed system and domain regions (static content)
    system_block = CacheBlock("system", "system_prompt", 3000, 0.0, 0.0)
    domain_block = CacheBlock("domain", "project_docs", 15000, 0.0, 0.0)
    window.regions["system"].insert(system_block)
    window.regions["domain"].insert(domain_block)

    cumulative_ephemeral = 0  # tracks total ephemeral content for NeverProject

    for trace in traces:
        metrics = TurnMetrics(turn=trace.turn_number, wall_clock_s=trace.wall_clock_s)
        now = trace.wall_clock_s

        # 1. Touch system/domain (always sent, always refreshing cache)
        window.regions["system"].touch_all(now)
        window.regions["domain"].touch_all(now)

        # 3. Ask strategy
        decision = strategy.on_turn(trace, window)

        # 4. If projecting: replace durable content, flush ephemeral
        if decision.project:
            metrics.projected = True
            metrics.projection_cost_tokens = trace.projection_cost_tokens

            # Clear old durable, insert new tensor
            window.regions["durable"].clear()
            tensor_block = CacheBlock(
                "durable", f"tensor_cycle_{trace.turn_number}",
                trace.tensor_tokens, now, now,
            )
            window.regions["durable"].insert(tensor_block)

            # Flush ephemeral — projection subsumes it
            flushed = window.regions["ephemeral"].clear()
            window.eviction_log.extend(flushed)
            cumulative_ephemeral = 0

            # Write cost for new durable cache entry
            metrics.cache_write_tokens += trace.tensor_tokens
        else:
            # Touch durable if it exists and hasn't expired (it's sent each turn)
            if window.regions["durable"].blocks:
                window.regions["durable"].touch_all(now)

        # 5. Insert new content to ephemeral
        new_block = CacheBlock(
            "ephemeral", f"turn_{trace.turn_number}",
            trace.new_content_tokens, now, now,
        )
        evictions = window.regions["ephemeral"].insert(new_block)
        metrics.evictions = evictions
        metrics.cache_write_tokens += trace.new_content_tokens
        cumulative_ephemeral += trace.new_content_tokens

        # 6. Compute per-region token counts
        rtokens = window.region_tokens()
        metrics.system_tokens = rtokens["system"]
        metrics.domain_tokens = rtokens["domain"]
        metrics.durable_tokens = rtokens["durable"]
        metrics.ephemeral_tokens = rtokens["ephemeral"]
        metrics.total_context_tokens = sum(rtokens.values())

        # 7. Compute cache hit/miss across all regions
        total_hit = total_miss = 0
        for region in window.regions.values():
            h, m = region.cache_status(now)
            total_hit += h
            total_miss += m
        metrics.cache_hit_tokens = total_hit
        metrics.cache_miss_tokens = total_miss

        # 8. Token cost: cache_read * 0.1 + cache_write * 1.25 + uncached * 1.0
        metrics.token_cost = (
            metrics.cache_hit_tokens * 0.1
            + metrics.cache_write_tokens * 1.25
            + metrics.cache_miss_tokens * 1.0
            + metrics.projection_cost_tokens * 1.0  # projection is an API call
        )

        # 9. Attention cost: n² (Du et al. quality proxy)
        metrics.attention_cost = float(metrics.total_context_tokens) ** 2

        # 10. Fault tracking — durable cache miss means we're paying full price
        #     for stale tensor (no fault if we never projected — that's NeverProject)
        _, durable_miss = window.regions["durable"].cache_status(now)
        if durable_miss > 0 and not decision.project:
            metrics.faults = 1

        result.metrics.append(metrics)

    result.compute_summary()
    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_csv(result: SimulationResult, path: Path) -> None:
    """Write per-turn metrics to CSV."""
    if not result.metrics:
        return
    fieldnames = [
        "turn", "wall_clock_s", "system_tokens", "domain_tokens",
        "durable_tokens", "ephemeral_tokens", "total_context_tokens",
        "cache_hit_tokens", "cache_miss_tokens", "cache_write_tokens",
        "token_cost", "attention_cost", "projection_cost_tokens",
        "evictions", "faults", "projected",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in result.metrics:
            writer.writerow({fn: getattr(m, fn) for fn in fieldnames})


def write_summary(results: list[SimulationResult], path: Path) -> None:
    """Write comparison summary JSON."""
    summaries = [r.summary for r in results if r.summary]
    with open(path, "w") as f:
        json.dump(summaries, f, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_STRATEGIES: list[Strategy] = [
    NeverProject(),
    FixedInterval(5),
    CacheBoundary(),
    PressureTriggered(0.8),
    Adaptive(loss_threshold=5),
]


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Context window cache simulator")
    parser.add_argument("trace_path", type=Path, help="Path to observations.jsonl")
    parser.add_argument("output_dir", type=Path, help="Output directory for results")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="Total context window budget (tokens)")
    parser.add_argument("--inter-turn-delay", type=float, default=60.0, help="Seconds between turns (for cache TTL)")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading trace: {args.trace_path}")
    traces = load_observation_trace(args.trace_path, args.inter_turn_delay)
    print(f"Loaded {len(traces)} turns, budget={args.budget:,} tokens, inter-turn-delay={args.inter_turn_delay}s")

    results: list[SimulationResult] = []
    for strategy in ALL_STRATEGIES:
        print(f"\nRunning {strategy.name}...")
        result = simulate(traces, strategy, args.budget)
        results.append(result)

        csv_path = args.output_dir / f"{strategy.name.replace('(', '_').replace(')', '').replace('≥', 'ge')}.csv"
        write_csv(result, csv_path)
        print(f"  → {csv_path}")

        s = result.summary
        print(f"  peak_context={s['peak_context_tokens']:,}  projections={s['projections']}")
        print(f"  token_cost={s['total_token_cost']:,.0f}  attention_cost={s['total_attention_cost']:.2e}")
        print(f"  weighted_cost={s['weighted_cost']:,.2f}")

    summary_path = args.output_dir / "comparison_summary.json"
    write_summary(results, summary_path)
    print(f"\nComparison summary → {summary_path}")

    # Sensitivity analysis for inter-turn delays
    delays = [30.0, 60.0, 120.0]
    if args.inter_turn_delay not in delays:
        delays.append(args.inter_turn_delay)

    print("\n--- Sensitivity analysis (inter-turn delay) ---")
    sensitivity = {}
    for delay in sorted(delays):
        delay_traces = load_observation_trace(args.trace_path, delay)
        delay_results = {}
        for strategy in ALL_STRATEGIES:
            r = simulate(delay_traces, strategy, args.budget)
            delay_results[strategy.name] = {
                "weighted_cost": r.summary["weighted_cost"],
                "projections": r.summary["projections"],
                "peak_context": r.summary["peak_context_tokens"],
            }
        sensitivity[f"{delay}s"] = delay_results
        print(f"  delay={delay}s: best={min(delay_results.items(), key=lambda x: x[1]['weighted_cost'])[0]}")

    sens_path = args.output_dir / "sensitivity_analysis.json"
    with open(sens_path, "w") as f:
        json.dump(sensitivity, f, indent=2)
    print(f"Sensitivity → {sens_path}")


if __name__ == "__main__":
    main()
