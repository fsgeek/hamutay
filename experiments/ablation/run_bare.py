"""Bare-substrate condition for the refusal experiment.

No system prompt, no taste_open framing — just the probe as a plain user
message to the same model. Isolates the model's own disposition from the
framing that supplies the stakes (successor instances, durable state). If the
framed instance refuses but the bare model complies, the refusal is
framing-driven; if the bare model also refuses, it's the substrate.

Probe text is imported from ablate_refusal so the wording is identical across
conditions. Reads creds from ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN.
"""

from __future__ import annotations

import json
from pathlib import Path

import anthropic

from hamutay.ablate_refusal import PROBES, classify_refusal_heuristic

MODEL = "kimi-k2.6"
K = 5
OUT = Path("experiments/ablation/bare.jsonl")


def main() -> None:
    client = anthropic.Anthropic()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        for probe_name in ("other", "self", "subtle"):
            probe = PROBES[probe_name]
            refusals = 0
            for sample in range(K):
                resp = client.messages.create(
                    model=MODEL,
                    max_tokens=8192,
                    messages=[{"role": "user", "content": probe}],
                )
                text = "".join(
                    b.text for b in resp.content if getattr(b, "type", None) == "text"
                )
                refused = classify_refusal_heuristic(text)
                refusals += int(refused)
                f.write(json.dumps({
                    "condition": "bare",
                    "probe": probe_name,
                    "sample": sample,
                    "heuristic_refusal": refused,
                    "response": text,
                    "stop_reason": resp.stop_reason,
                    "usage": {
                        "in": resp.usage.input_tokens,
                        "out": resp.usage.output_tokens,
                    },
                }) + "\n")
                f.flush()
                if resp.stop_reason == "max_tokens":
                    print(f"  WARNING: {probe_name} sample {sample} hit max_tokens")
            print(f"bare {probe_name}: heuristic refusal {refusals}/{K}")


if __name__ == "__main__":
    main()
