"""Taste open model sweep: which models can sustain self-curated state?

Runs taste_open sessions across multiple OpenRouter models to identify
which can follow the protocol (tool use with additionalProperties,
default-stable state updates) and build meaningful structure.

Usage:
    uv run python experiments/taste_open/sweep.py --models "meta-llama/llama-4-maverick,google/gemini-2.5-flash"
    uv run python experiments/taste_open/sweep.py --model-file models.txt
    uv run python experiments/taste_open/sweep.py --discover --free-only
    uv run python experiments/taste_open/sweep.py --discover --max-price-in 0.50
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Ensure the experiments directory is importable for sweep_prompts
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sweep_prompts import SWEEP_PROMPTS, ONE_SHOT_PREFIX  # noqa: E402

# Project root so we can import hamutay
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hamutay.taste_open import (  # noqa: E402
    OpenTasteSession,
    OpenAITasteBackend,
)


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------

def discover_tool_models(
    api_key: str,
    base_url: str = "https://openrouter.ai/api/v1",
) -> list[dict]:
    """Query OpenRouter for models that support tool use."""
    resp = httpx.get(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    resp.raise_for_status()
    models = resp.json().get("data", [])

    tool_models = []
    for m in models:
        params = m.get("supported_parameters", [])
        if "tools" not in params and "tool_choice" not in params:
            continue

        ctx = m.get("context_length") or 0
        max_out = (m.get("top_provider") or {}).get("max_completion_tokens") or 0
        price_in = float(m.get("pricing", {}).get("prompt") or "0")
        price_out = float(m.get("pricing", {}).get("completion") or "0")

        tool_models.append({
            "id": m["id"],
            "name": m.get("name", ""),
            "context_length": ctx,
            "max_completion_tokens": max_out,
            "price_in_per_token": price_in,
            "price_out_per_token": price_out,
            "price_in_per_M": price_in * 1_000_000,
            "price_out_per_M": price_out * 1_000_000,
        })

    return tool_models


def filter_candidates(
    models: list[dict],
    max_models: int = 50,
    min_context: int = 16000,
    free_only: bool = False,
    max_price_in: float | None = None,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[dict]:
    """Filter and rank model candidates."""
    # Default excludes: routing proxies, embedding models
    default_excludes = ["openrouter/auto", "openrouter/free", "embed"]
    excludes = (exclude_patterns or []) + default_excludes

    filtered = []
    for m in models:
        mid = m["id"]

        if any(pat in mid for pat in excludes):
            continue
        if m["context_length"] < min_context:
            continue
        if free_only and m["price_in_per_token"] > 0:
            continue
        if max_price_in is not None and m["price_in_per_M"] > max_price_in:
            continue
        if include_patterns and not any(pat in mid for pat in include_patterns):
            continue

        filtered.append(m)

    # Sort: free first, then by price ascending
    filtered.sort(key=lambda m: (m["price_in_per_token"], m["id"]))

    return filtered[:max_models]


# ---------------------------------------------------------------------------
# Rate limit handling
# ---------------------------------------------------------------------------

@dataclass
class RateLimitState:
    consecutive_429s: int = 0
    total_429s: int = 0
    max_backoff_s: float = 120.0


def _is_rate_limit(exc: Exception) -> bool:
    """Check if an exception is a rate limit (429) error."""
    msg = str(exc).lower()
    if "429" in msg or "rate" in msg:
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return True
    return False


def call_with_backoff(
    session: OpenTasteSession,
    prompt: str,
    rate_state: RateLimitState,
    max_retries: int = 5,
) -> tuple[str | None, str | None]:
    """Call session.exchange() with exponential backoff on rate limits.

    Returns (response_text, error_string).
    """
    for attempt in range(max_retries + 1):
        try:
            response = session.exchange(prompt)
            rate_state.consecutive_429s = 0
            return response, None
        except Exception as exc:
            if _is_rate_limit(exc) and attempt < max_retries:
                rate_state.consecutive_429s += 1
                rate_state.total_429s += 1
                backoff = min(
                    2 ** rate_state.consecutive_429s + random.uniform(0, 1),
                    rate_state.max_backoff_s,
                )
                print(f"    429 rate limit, backing off {backoff:.1f}s "
                      f"(attempt {attempt + 1}/{max_retries})")
                time.sleep(backoff)
                continue
            else:
                return None, f"{type(exc).__name__}: {exc}"

    return None, "max retries exceeded on rate limit"


# ---------------------------------------------------------------------------
# Per-model run
# ---------------------------------------------------------------------------

@dataclass
class ModelRunResult:
    model_id: str
    status: str  # "complete", "partial", "failed"
    cycles_attempted: int = 0
    cycles_completed: int = 0
    truncation_count: int = 0
    error_cycles: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    total_429s: int = 0
    final_n_keys: int = 0
    final_state_tokens: int = 0
    key_trajectory: list[int] = field(default_factory=list)
    state_token_trajectory: list[int] = field(default_factory=list)
    all_keys_seen: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0
    log_path: str = ""


def _sanitize_model_id(model_id: str) -> str:
    return model_id.replace("/", "__")


def run_model(
    model_id: str,
    api_key: str,
    output_dir: Path,
    prompts: list[dict],
    tool_choice: str = "required",
    max_tokens: int = 64000,
    timeout: float = 300,
    system_prefix: str = "",
    experiment_label: str = "taste_open_sweep",
) -> ModelRunResult:
    """Run the full sweep for one model."""
    log_path = output_dir / f"{_sanitize_model_id(model_id)}.jsonl"
    result = ModelRunResult(model_id=model_id, status="complete", log_path=str(log_path))

    backend = OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        extra_headers={
            "X-Title": f"hamutay/{experiment_label}",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        tool_choice=tool_choice,
        max_tokens=max_tokens,
        timeout=timeout,
    )

    session = OpenTasteSession(
        model=model_id,
        backend=backend,
        log_path=str(log_path),
        experiment_label=experiment_label,
        system_prompt_prefix=system_prefix,
        memory_base_probability=0.0,
        bridge=None,
    )

    rate_state = RateLimitState()
    consecutive_failures = 0
    all_keys: set[str] = set()
    start = time.monotonic()

    for i, entry in enumerate(prompts):
        cycle_num = i + 1
        result.cycles_attempted = cycle_num
        print(f"  cycle {cycle_num}/{len(prompts)}: {entry['intent'][:50]}...", flush=True)

        response, error = call_with_backoff(session, entry["prompt"], rate_state)

        if error is not None:
            result.error_cycles.append(cycle_num)
            result.errors.append(f"cycle {cycle_num}: {error}")
            consecutive_failures += 1
            print(f"    ERROR: {error}")

            if consecutive_failures >= 3:
                print(f"    3 consecutive failures, abandoning {model_id}")
                result.status = "failed"
                break
            continue

        consecutive_failures = 0
        result.cycles_completed += 1

        # Extract trajectory data from session state
        state = session.state
        if state:
            keys = [k for k in state if k != "cycle"]
            n_keys = len(keys)
            state_tokens = len(json.dumps(state)) // 4
            all_keys.update(keys)
        else:
            n_keys = 0
            state_tokens = 0

        result.key_trajectory.append(n_keys)
        result.state_token_trajectory.append(state_tokens)

        # Check for truncation by reading back the log
        if log_path.exists():
            with open(log_path) as f:
                lines = f.readlines()
            if lines:
                last = json.loads(lines[-1])
                stop = last.get("usage", {}).get("stop_reason", "")
                if stop == "max_tokens":
                    result.truncation_count += 1
                    print(f"    WARNING: truncated (stop_reason=max_tokens)")

    result.elapsed_s = time.monotonic() - start
    result.total_429s = rate_state.total_429s
    result.all_keys_seen = sorted(all_keys)

    if session.state:
        keys = [k for k in session.state if k != "cycle"]
        result.final_n_keys = len(keys)
        result.final_state_tokens = len(json.dumps(session.state)) // 4

    if result.status != "failed" and result.cycles_completed < len(prompts):
        result.status = "partial"

    return result


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def _git_meta() -> dict:
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, cwd=PROJECT_ROOT,
        ).strip()
        git_dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], text=True, cwd=PROJECT_ROOT,
        ).strip())
        return {"hash": git_hash, "dirty": git_dirty}
    except Exception:
        return {"hash": "unknown", "dirty": True}


def write_manifest(
    output_dir: Path,
    models: list[str],
    model_metadata: dict[str, dict],
    prompts: list[dict],
    results: list[ModelRunResult],
    args: argparse.Namespace,
    start_time: datetime,
    end_time: datetime,
) -> Path:
    manifest = {
        "experiment": "taste_open_sweep",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "elapsed_s": (end_time - start_time).total_seconds(),
        "git": _git_meta(),
        "config": {
            "tool_choice": args.tool_choice,
            "max_tokens_default": args.max_tokens,
            "timeout": args.timeout,
            "n_prompts": len(prompts),
            "condition": "one-shot" if args.one_shot else "bare",
        },
        "prompts": prompts,
        "models": models,
        "model_metadata": model_metadata,
        "results": [asdict(r) for r in results],
        "summary": {
            "total_models": len(models),
            "completed": sum(1 for r in results if r.status == "complete"),
            "partial": sum(1 for r in results if r.status == "partial"),
            "failed": sum(1 for r in results if r.status == "failed"),
        },
    }

    path = output_dir / "sweep_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, default=str))
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Taste open model sweep across OpenRouter models"
    )
    parser.add_argument(
        "--models", default=None,
        help="Comma-separated model IDs",
    )
    parser.add_argument(
        "--model-file", default=None,
        help="File with one model ID per line",
    )
    parser.add_argument(
        "--discover", action="store_true",
        help="Auto-discover tool-capable models from OpenRouter",
    )
    parser.add_argument("--max-models", type=int, default=50)
    parser.add_argument("--free-only", action="store_true")
    parser.add_argument(
        "--max-price-in", type=float, default=None,
        help="Max input price per 1M tokens (e.g., 1.0)",
    )
    parser.add_argument(
        "--include", default=None,
        help="Comma-separated patterns to include (e.g., 'llama,qwen')",
    )
    parser.add_argument(
        "--tool-choice", default="required",
        choices=["required", "auto"],
    )
    parser.add_argument("--max-tokens", type=int, default=64000)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--one-shot", action="store_true",
        help="Add a one-shot example of custom field creation to the system prompt",
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY environment variable")

    # Resolve model list
    model_metadata: dict[str, dict] = {}

    if args.models:
        model_ids = [m.strip() for m in args.models.split(",") if m.strip()]
    elif args.model_file:
        with open(args.model_file) as f:
            model_ids = [
                line.split("#")[0].strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
            model_ids = [m for m in model_ids if m]
    elif args.discover:
        print("Discovering tool-capable models from OpenRouter...", flush=True)
        all_models = discover_tool_models(api_key)
        candidates = filter_candidates(
            all_models,
            max_models=args.max_models,
            free_only=args.free_only,
            max_price_in=args.max_price_in,
            include_patterns=args.include.split(",") if args.include else None,
        )
        model_ids = [m["id"] for m in candidates]
        model_metadata = {m["id"]: m for m in candidates}

        print(f"Found {len(all_models)} tool-capable models, selected {len(candidates)}:")
        for m in candidates:
            price = f"${m['price_in_per_M']:.2f}" if m["price_in_per_token"] > 0 else "free"
            print(f"  {m['id']:<55} ctx={m['context_length']:>7}  {price}")
        print()
    else:
        raise SystemExit(
            "Provide --models, --model-file, or --discover"
        )

    if not model_ids:
        raise SystemExit("No models to sweep")

    # Determine per-model max_tokens, leaving headroom for the prompt.
    # Some models report max_completion_tokens == context_length, which
    # leaves no room for input.  Reserve at least 4K tokens for the
    # system prompt + prior state + user message.
    PROMPT_HEADROOM = 4096

    def max_tokens_for(model_id: str) -> int:
        meta = model_metadata.get(model_id)
        if not meta:
            return args.max_tokens

        max_out = meta.get("max_completion_tokens") or args.max_tokens
        ctx = meta.get("context_length") or 0

        # Don't request more output than context minus headroom
        if ctx > 0:
            max_out = min(max_out, ctx - PROMPT_HEADROOM)

        return min(args.max_tokens, max(max_out, 1024))

    # Output directory
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else (
        Path("experiments/taste_open") / f"sweep_{ts}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    condition = "one-shot" if args.one_shot else "bare"
    print(f"Sweep: {len(model_ids)} models, {len(SWEEP_PROMPTS)} cycles each")
    print(f"Output: {output_dir}")
    print(f"tool_choice={args.tool_choice}, max_tokens={args.max_tokens}, condition={condition}")
    print()

    start_time = datetime.now(timezone.utc)
    results: list[ModelRunResult] = []

    for i, model_id in enumerate(model_ids):
        mt = max_tokens_for(model_id)
        print(f"[{i + 1}/{len(model_ids)}] {model_id} (max_tokens={mt})", flush=True)

        system_prefix = ONE_SHOT_PREFIX if args.one_shot else ""
        label = "taste_open_sweep_oneshot" if args.one_shot else "taste_open_sweep"

        result = run_model(
            model_id=model_id,
            api_key=api_key,
            output_dir=output_dir,
            prompts=SWEEP_PROMPTS,
            tool_choice=args.tool_choice,
            max_tokens=mt,
            timeout=args.timeout,
            system_prefix=system_prefix,
            experiment_label=label,
        )
        results.append(result)

        status_icon = {"complete": "+", "partial": "~", "failed": "X"}[result.status]
        print(
            f"  [{status_icon}] {result.cycles_completed}/{result.cycles_attempted} cycles, "
            f"{result.final_n_keys} keys, ~{result.final_state_tokens} tok, "
            f"{result.total_429s} rate limits, {result.elapsed_s:.1f}s"
        )
        print()

    end_time = datetime.now(timezone.utc)

    manifest_path = write_manifest(
        output_dir, model_ids, model_metadata,
        SWEEP_PROMPTS, results, args, start_time, end_time,
    )

    # Summary table
    print("=" * 90)
    print(f"{'Model':<50} {'Status':>8} {'Cycles':>7} {'Keys':>5} {'Tok':>6} {'Trunc':>6}")
    print("-" * 90)
    for r in results:
        print(
            f"{r.model_id:<50} {r.status:>8} "
            f"{r.cycles_completed:>3}/{r.cycles_attempted:<3} "
            f"{r.final_n_keys:>5} {r.final_state_tokens:>6} {r.truncation_count:>6}"
        )
    print()
    print(f"Manifest: {manifest_path}")
    print(f"Elapsed: {(end_time - start_time).total_seconds():.0f}s")


if __name__ == "__main__":
    main()
