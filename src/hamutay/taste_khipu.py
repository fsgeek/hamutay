"""Feed khipu to a taste_open session, one at a time.

Thin wrapper around OpenTasteSession. Reads khipu files from a
directory, orders them by git creation date (falling back to
filename sort), and feeds each one as a user message. The model
decides what to carry forward.

Usage:
    uv run python -m hamutay.taste_khipu /path/to/khipu/dir
    uv run python -m hamutay.taste_khipu /path/to/khipu/dir --resume experiments/taste_khipu/run.jsonl
    uv run python -m hamutay.taste_khipu /path/to/khipu/dir --model claude-haiku-4-5 --pause
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from hamutay.taste_open import (
    AnthropicTasteBackend,
    OpenAITasteBackend,
    OpenTasteSession,
    TasteBackend,
)


def _git_creation_order(khipu_dir: Path) -> list[Path]:
    """Order .md files by their first git commit date.

    Falls back to filename sort for files with no git history.
    """
    md_files = sorted(khipu_dir.glob("*.md"))
    readme = [f for f in md_files if f.name.upper() == "README.MD"]
    khipus = [f for f in md_files if f.name.upper() != "README.MD"]

    dated: list[tuple[str, Path]] = []
    undated: list[Path] = []

    for path in khipus:
        try:
            result = subprocess.run(
                ["git", "log", "--diff-filter=A", "--format=%aI", "--", str(path)],
                capture_output=True, text=True, timeout=10,
                cwd=khipu_dir,
            )
            date = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else ""
            if date:
                dated.append((date, path))
            else:
                undated.append(path)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            undated.append(path)

    dated.sort(key=lambda x: x[0])
    return [p for _, p in dated] + undated


def main():
    parser = argparse.ArgumentParser(
        description="Feed khipu to a taste_open session, one at a time"
    )
    parser.add_argument(
        "khipu_dir", type=Path,
        help="Directory containing khipu .md files",
    )
    parser.add_argument(
        "--model", default="claude-haiku-4-5",
        help="Model (default: claude-haiku-4-5)",
    )
    parser.add_argument(
        "--provider", default="anthropic",
        choices=["anthropic", "openrouter", "openai"],
        help="API provider (default: anthropic)",
    )
    parser.add_argument(
        "--base-url", default=None,
        help="Base URL for OpenAI-compatible endpoint",
    )
    parser.add_argument(
        "--api-key", default=None,
        help="API key (default: from env)",
    )
    parser.add_argument(
        "--label", default=None,
        help="Experiment label (default: taste_khipu)",
    )
    parser.add_argument("--log-path", default=None, help="JSONL log path")
    parser.add_argument(
        "--resume", default=None,
        help="Resume from a log JSONL",
    )
    parser.add_argument(
        "--pause", action="store_true",
        help="Pause after each khipu for user input",
    )
    parser.add_argument(
        "--start-at", type=int, default=0,
        help="Skip the first N khipu (useful when resuming)",
    )
    parser.add_argument(
        "--memory-prob", default=0.1, type=float,
        help="Base probability of involuntary memory injection (default: 0.1)",
    )
    args = parser.parse_args()

    # Resolve khipu files
    khipu_dir = args.khipu_dir.resolve()
    if not khipu_dir.is_dir():
        raise SystemExit(f"Not a directory: {khipu_dir}")

    print(f"Ordering khipu by git creation date from {khipu_dir}...")
    khipus = _git_creation_order(khipu_dir)
    print(f"Found {len(khipus)} khipu")

    if not khipus:
        raise SystemExit("No .md files found")

    # Log path
    resume = False
    if args.resume is not None:
        args.log_path = args.resume
        resume = True
    elif args.log_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_dir = Path("experiments") / "taste_khipu"
        log_dir.mkdir(parents=True, exist_ok=True)
        args.log_path = str(log_dir / f"taste_khipu_{ts}.jsonl")

    experiment_label = args.label or "taste_khipu"

    # Build backend
    backend: TasteBackend
    if args.provider == "anthropic":
        backend = AnthropicTasteBackend()
    else:
        if args.provider == "openrouter":
            base_url = args.base_url or "https://openrouter.ai/api/v1"
            api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
            extra_headers = {
                "X-Title": f"hamutay/{experiment_label}",
                "HTTP-Referer": "https://github.com/fsgeek/hamutay",
            }
        else:
            base_url = args.base_url or "https://api.openai.com/v1"
            api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
            extra_headers = {}

        if not api_key:
            key_var = "OPENROUTER_API_KEY" if args.provider == "openrouter" else "OPENAI_API_KEY"
            raise SystemExit(f"No API key: pass --api-key or set {key_var}")

        backend = OpenAITasteBackend(
            base_url=base_url,
            api_key=api_key,
            extra_headers=extra_headers,
        )

    session = OpenTasteSession(
        model=args.model,
        backend=backend,
        log_path=args.log_path,
        experiment_label=experiment_label,
        resume=resume,
        memory_base_probability=args.memory_prob,
    )

    if resume:
        s = session.state
        keys = sorted(k for k in s if k != "cycle") if s else []
        est = len(json.dumps(s)) // 4 if s else 0
        print(f"Resumed at cycle {session.cycle}, "
              f"{len(keys)} keys, ~{est:,} tokens")

    print(f"Model: {args.model}")
    print(f"Log: {args.log_path}")
    print(f"Khipu to feed: {len(khipus)} (starting at {args.start_at})")
    print()

    # Show the list
    print("Khipu order:")
    for i, kp in enumerate(khipus):
        marker = "  " if i < args.start_at else ">>"
        print(f"  {marker} {i+1:3d}. {kp.name}")
    print()

    # Feed them
    khipus_to_feed = khipus[args.start_at:]
    for i, kp in enumerate(khipus_to_feed):
        idx = args.start_at + i + 1
        content = kp.read_text()
        char_count = len(content)
        token_est = char_count // 4

        print(f"── khipu {idx}/{len(khipus)}: {kp.name} ({token_est:,}≈tok) ──")

        user_message = f"Khipu {idx} of {len(khipus)}: {kp.name}\n\n{content}"

        try:
            response = session.exchange(user_message)
            u = session._last_usage
            mem = session._last_injected_memory
            s = session.state
            state_est = len(json.dumps(s)) // 4 if s else 0
            n_keys = len([k for k in s if k != "cycle"]) if s else 0

            status_parts = [f"cycle {session.cycle}"]
            if u:
                status_parts.append(f"in={u['input_tokens']:,} out={u['output_tokens']:,}")
            status_parts.append(f"state={state_est:,}≈tok, {n_keys} keys")
            if mem:
                status_parts.append(f"memory from cycle {mem[0]}")

            print(f"  [{' | '.join(status_parts)}]")
            print(f"\n{response}\n")

        except Exception as e:
            print(f"\n  ERROR at khipu {idx}: {e}\n")
            import traceback
            traceback.print_exc()
            break

        if args.pause:
            try:
                cmd = input("  [enter=continue, s=state, q=quit] ").strip().lower()
                if cmd == "q":
                    break
                if cmd == "s":
                    print(json.dumps(session.state, indent=2))
                    input("  [enter to continue] ")
            except (EOFError, KeyboardInterrupt):
                print()
                break

    print(f"\nDone. {session.cycle} cycles.")
    print(f"Log: {args.log_path}")
    if session.state:
        s = session.state
        state_est = len(json.dumps(s)) // 4
        n_keys = len([k for k in s if k != "cycle"])
        print(f"Final state: {n_keys} keys, ~{state_est:,} tokens")


if __name__ == "__main__":
    main()
