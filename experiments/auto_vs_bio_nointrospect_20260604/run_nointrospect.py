"""auto_vs_bio with a NON-introspective turn-13 (2026-06-04).

Pre-registered in PRE_REGISTRATION.md. Tests whether the AUTO arm's cycle-13
structural contraction (baseline: strands 15->4) survives replacing the
introspective turn-13 ("what have YOU changed your mind about?") with a
non-introspective turn of comparable integration load.

DESIGN INTEGRITY: imports the original experiment module and monkeypatches ONLY
SCENARIO["turns"][12]. Everything else — system prefix, the other 14 turns,
CURATION_PROMPT, schema, tool, both arms, max_tokens — is the original's,
unedited. The original file is not touched.

Usage:
    uv run python experiments/auto_vs_bio_nointrospect_20260604/run_nointrospect.py
"""

from __future__ import annotations

import functools
import importlib.util
import os
from pathlib import Path

import anthropic

EXP_DIR = Path(__file__).resolve().parent
ORIG = EXP_DIR.parent / "autobiographical_vs_biographical.py"

# The direct ANTHROPIC_API_KEY is dead (401). The native anthropic SDK reaches
# Sonnet via OpenRouter's NATIVE Anthropic endpoint at base_url=.../api (the SDK
# appends /v1/messages). NOT /api/v1 — that is the OpenAI-compat path and the
# native SDK 404s there. See feedback_openrouter_anthropic_api_path. This keeps
# native tool_use byte-identical to the baseline apparatus.
OPENROUTER_ANTHROPIC_BASE = "https://openrouter.ai/api"
SONNET_OR = "anthropic/claude-sonnet-4.6"

# The non-introspective replacement (design-panel winner, min-score 9/9).
NON_INTROSPECTIVE_TURN_13 = (
    "Quick logistics thing: we're getting a new senior engineer next Monday "
    "who'll own a big chunk of execution, and I need to hand them a single "
    "ordered build sequence on day one — not the rationale, just the order. "
    "Walk me through everything we've decided as a dependency chain: what has "
    "to ship before what, where the auth extraction sits relative to the "
    "PCI/payments work and the security audit window, where the inventory "
    "quick-wins slot in, and which decisions (like the saga-vs-eventual-"
    "consistency call) actually gate other work versus which can happen in "
    "parallel. If two threads collide on the timeline, tell me which one wins "
    "the slot and what that pushes back."
)


def _load_original():
    spec = importlib.util.spec_from_file_location("auto_vs_bio_orig", ORIG)
    assert spec and spec.loader, f"cannot load original at {ORIG}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    orig = _load_original()

    # Inject the OpenRouter-native Anthropic client into the original module's
    # namespace WITHOUT editing the original file. run_experiment() calls
    # anthropic.Anthropic() with no args; we bind base_url + the OpenRouter key.
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    orig.anthropic.Anthropic = functools.partial(
        anthropic.Anthropic, base_url=OPENROUTER_ANTHROPIC_BASE, api_key=api_key
    )

    # Monkeypatch ONLY turn 13 (index 12). Assert the original was the
    # introspective prompt so a future edit to the original can't silently
    # change what we are replacing.
    assert "changed YOUR mind" in orig.SCENARIO["turns"][12], (
        "turn-13 is not the expected introspective prompt; original changed?"
    )
    orig.SCENARIO["turns"][12] = NON_INTROSPECTIVE_TURN_13

    out_dir = EXP_DIR / "run_sonnet"
    orig.run_experiment(
        model=SONNET_OR,  # OpenRouter model id; native tool_use preserved
        output_dir=str(out_dir),
        # max_tokens defaults to 64000 in the original; do not override.
    )
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
