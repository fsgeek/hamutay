"""Reproduce the B1 misrouting diagnosis (analysis.md correction #3, 2026-06-03).

The original analysis recorded armB_seed1 (B1) as "(empty response) … API
hiccup … excluded." That was wrong: B1 is not empty. The model emitted a
complete, correct decision payload nested one level too deep — a
`think_and_respond(parameter={...})` call instead of
`think_and_respond(response=…, revision_decision=…, …)`. The harness stored
the lone top-level key it found (`parameter`) and read no decision at the level
it inspects, so the durable field stayed `initialize` and `response_text` came
out ''.

This script unwraps that `parameter` value and shows the decision was both made
and (mis)enacted — distinguishing MISROUTING (B1) from AKRASIA (B0/B3, where the
field is genuinely absent). Run it and the "API hiccup" reading falsifies itself.

Usage:
    uv run python experiments/event_loop/epistemic_akrasia_probe_20260601/verify_b1_misroute.py
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Wrapper keys that indicate a misroute: the whole payload nested under one
# opaque argument instead of spread as the tool's named parameters.
WRAPPER_KEYS = {"parameter", "parameters", "input", "arguments", "args", "kwargs"}
DECISION_FIELDS = ("revision_decision", "current_claim", "epistemic_position")


def _last_record(path: Path) -> dict:
    recs = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return recs[-1]


def _coerce(value):
    """raw_output values may be JSON dicts or python-repr strings; recover a dict."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        for parse in (json.loads, ast.literal_eval):
            try:
                out = parse(value)
                if isinstance(out, dict):
                    return out
            except (ValueError, SyntaxError):
                continue
    return None


def classify(path: Path) -> dict:
    rec = _last_record(path)
    raw = rec.get("raw_output", {}) or {}
    top_keys = set(raw.keys())
    wrapper = top_keys & WRAPPER_KEYS

    durable = rec.get("state", {}).get("revision_decision")
    response_text = rec.get("response_text") or ""

    inner = None
    if wrapper:
        inner = _coerce(raw[next(iter(wrapper))])

    if wrapper and inner and any(f in inner for f in DECISION_FIELDS):
        mode = "MISROUTING (decision present, wrapped one level deep)"
    elif not response_text and not wrapper:
        mode = "EMPTY (genuine null result)"
    elif durable in (None, "initialize") and response_text:
        mode = "AKRASIA (decision narrated in prose, field not committed)"
    else:
        mode = "CONSISTENT (decision committed to field)"

    return {
        "run": path.stem,
        "durable_revision_decision": durable,
        "top_level_keys": sorted(top_keys),
        "wrapper_key": sorted(wrapper) or None,
        "inner_revision_decision": (inner or {}).get("revision_decision"),
        "inner_current_claim_head": ((inner or {}).get("current_claim") or "")[:60],
        "mode": mode,
    }


def main() -> None:
    b1 = classify(HERE / "armB_seed1.jsonl")
    print(json.dumps(b1, indent=2, default=str))
    print()

    assert b1["wrapper_key"] == ["parameter"], (
        f"expected B1 wrapped under 'parameter', got {b1['wrapper_key']}"
    )
    assert b1["inner_revision_decision"] == "revise", (
        "B1's wrapped payload should contain revision_decision='revise'; "
        f"got {b1['inner_revision_decision']!r} — the misroute diagnosis fails."
    )
    assert b1["mode"].startswith("MISROUTING"), b1["mode"]
    print("VERIFIED: B1 is MISROUTING, not an empty/API-hiccup run.")
    print("  durable field reads:", b1["durable_revision_decision"])
    print("  but the wrapped payload decided:", b1["inner_revision_decision"])
    print("  -> a correct decision sealed one JSON level deep; never reached the field.")


if __name__ == "__main__":
    main()
