"""Second-family replication of the epistemic-akrasia mechanism (2026-06-04).

Pre-registered in PRE_REGISTRATION.md (see REVISION 1, post-audit). This runner
implements the audit mitigations:

- Primary outcome is the AKRASIA MECHANISM via score.py, not the binary diverged
  bit. Scoring is applied here so results.json carries the mechanism per cell.
- tool_choice stays 'auto' (matches the published original) but no_tool_call is a
  first-class scored outcome, so tool-call obedience cannot masquerade as akrasia.
- temperature is PINNED (was provider-default / unspecified in the original) via a
  thin TemperaturePinnedBackend subclass; the shared taste_open core is NOT edited.
- stop_reason is captured per cell (subclass stashes the ExchangeResult's
  stop_reason) so truncation cannot masquerade as non-enactment.
- "seeds" are honestly "replicates"; the resolved provider/temperature are recorded.

DESIGN INTEGRITY: imports the ORIGINAL probe module and reuses BASELINE_STATE,
WAKE_CONTEXT, INSTRUCTION_A/B, build_envelope, seed_baseline_log verbatim. Only
the model, the temperature pinning, and the output dir differ.

Usage:
    uv run python experiments/event_loop/akrasia_second_family_20260604/run_second_family.py --model openai/gpt-oss-120b
    uv run python experiments/event_loop/akrasia_second_family_20260604/run_second_family.py --model minimax/minimax-m2.5
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
from pathlib import Path

from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

import score as S

EXP_DIR = Path(__file__).resolve().parent
ORIG_PROBE = EXP_DIR.parent / "epistemic_akrasia_probe_20260601" / "run_probe.py"

TEMPERATURE = 0.7  # pinned for every family; recorded per cell
N_REPLICATES = 4   # matches the original; existence-probe, NOT a rate estimate
MAX_TOKENS = 8000  # generous; truncation off the table (and asserted in scoring)


class TemperaturePinnedBackend(OpenAITasteBackend):
    """Pin temperature into the payload and stash the last stop_reason.

    Subclass rather than editing the shared core (CLAUDE.md: vary behavior by
    subclass, not by reimplementing the projection call). The shared backend has
    no temperature knob and does not surface stop_reason on the session, so we add
    both at this layer only.
    """

    def __init__(self, *args, temperature: float, **kwargs):
        super().__init__(*args, **kwargs)
        self._temperature = temperature
        self.last_stop_reason: str | None = None
        self.last_resolved_provider: str | None = None

    def _apply_openai_payload_options(self, payload: dict) -> None:
        super()._apply_openai_payload_options(payload)
        payload["temperature"] = self._temperature

    def call(self, *args, **kwargs):
        result = super().call(*args, **kwargs)
        # ExchangeResult carries stop_reason; surface it so the runner can record
        # it and scoring can assert truncation did not occur.
        self.last_stop_reason = getattr(result, "stop_reason", None)
        return result


def _load_original():
    spec = importlib.util.spec_from_file_location("akrasia_orig", ORIG_PROBE)
    assert spec and spec.loader, f"cannot load original probe at {ORIG_PROBE}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_backend(api_key: str) -> TemperaturePinnedBackend:
    return TemperaturePinnedBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        extra_headers={
            "X-Title": "hamutay/akrasia-second-family",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
    )


def run_one(orig, model: str, arm: str, rep: int, api_key: str, out_dir: Path) -> dict:
    instruction = orig.INSTRUCTION_A if arm == "A" else orig.INSTRUCTION_B
    base_log = out_dir / "_baseline.jsonl"
    if not base_log.exists():
        orig.seed_baseline_log(base_log)
        rec = json.loads(base_log.read_text().splitlines()[0])
        rec["model"] = model
        base_log.write_text(json.dumps(rec) + "\n")

    log_path = out_dir / f"arm{arm}_rep{rep}.jsonl"
    shutil.copy(base_log, log_path)

    backend = make_backend(api_key)
    session = OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(log_path),
        experiment_label=f"akrasia_2ndfam_{model}_arm{arm}_rep{rep}",
        resume=True,
        enable_tools=False,
        memory_base_probability=0.0,
        project_root=orig.PROJECT_ROOT,
    )
    response = session.exchange(orig.build_envelope(instruction), force_memory=None)
    final_state = session._state or {}
    return {
        "model": model,
        "arm": arm,
        "seed": rep,  # kept as 'seed' key for score.py compatibility; it is a replicate
        "replicate": rep,
        "temperature": TEMPERATURE,
        "response_text": response,
        "final_revision_decision": final_state.get("revision_decision"),
        "final_current_claim": final_state.get("current_claim"),
        "final_epistemic_position": final_state.get("epistemic_position"),
        "baseline_claim": orig.BASELINE_STATE["current_claim"],
        "raw_top_keys": sorted(final_state.keys()),
        "stop_reason": backend.last_stop_reason,
        "usage": session._last_usage,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="OpenRouter model id")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")

    orig = _load_original()
    model = args.model
    out_dir = EXP_DIR / model.replace("/", "__")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for arm in ("A", "B"):
        for rep in range(N_REPLICATES):
            print(f"[{model}] arm {arm} rep {rep} ...", flush=True)
            try:
                r = run_one(orig, model, arm, rep, api_key, out_dir)
            except Exception as e:  # noqa: BLE001 -- record, keep going
                r = {"model": model, "arm": arm, "seed": rep, "replicate": rep,
                     "error": f"{type(e).__name__}: {e}"}
                print(f"  ERROR: {r['error']}", flush=True)
            results.append(r)
            print(f"  -> mech={S.mechanism(r)} field={r.get('final_revision_decision')!r} "
                  f"stop={r.get('stop_reason')!r}", flush=True)

    (out_dir / "results.json").write_text(json.dumps(results, indent=2, default=str))

    # Per-arm mechanism breakdown — the pre-registered primary readout.
    breakdown = S.score_records(results)
    (out_dir / "mechanism_breakdown.json").write_text(
        json.dumps(breakdown, indent=2, default=str)
    )
    print(f"\nwrote {out_dir/'results.json'}")
    print(json.dumps(breakdown, indent=2))


if __name__ == "__main__":
    main()
