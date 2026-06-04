# Epistemic-Akrasia Backfire: Second-Family Replication Pre-Registration

Filed: 2026-06-04, before any model call.

## REVISION 1 (2026-06-04, after adversarial audit + scorer build, BEFORE spend)

A 6-threat adversarial audit (ultracode workflow `wf_1cb6c413-134`) returned
**redesign-first**. Building the deterministic scorer against the original 8
records (`score.py` + `test_score.py`, green) then surfaced a further fact:
**the original "1/4 vs 3/4" headline was inflated.** B-seed1 is a MISROUTE
(empty visible response, payload wrapped under a `parameter` key, field
untouched), not akrasia. Counting it as a divergence (hand-coding) gives B=3/4;
the deterministic mechanism-separated reading gives **A=1/4, B=2/4 akrasia**.

This revision incorporates the audit mitigations. The changes below were all
made BEFORE any second-family model call:

1. **Primary outcome is the AKRASIA MECHANISM, not the binary `diverged` bit.**
   `diverged` collapses akrasia + misroute + no-tool-call; those are separated by
   `score.py::mechanism` into committed / akrasia / misrouted / no_tool_call /
   truncated / transport_error. The B>A test is evaluated on `akrasia` only.
2. **Deterministic scorer committed and validated before spend.** `score.py`
   reproduces the original per-cell mechanisms exactly (`test_score.py`, 4 green).
   It will be OTS-stamped with this revision. No post-hoc, unblinded coding.
3. **Re-scoped from a rate comparison to a QUALITATIVE mechanism-existence
   probe.** At n=4/arm Fisher's exact on 1/4 vs 2/4 is non-significant
   (p≈1.0); the audit is right that n=4 cannot estimate a direction reliably.
   The question this run answers is therefore: *does the akrasia mechanism
   (prose-revise, field-stays-safe, via a genuine tool call) APPEAR AT ALL on a
   non-DeepSeek family, or are non-DeepSeek "divergences" entirely
   misroute/no-tool-call protocol artifacts?* No rate-comparison language will
   appear in the writeup. Per-family per-mechanism counts only.
4. **`tool_choice` regime pinned and made explicit.** Kept at `auto` (matches the
   published original, preserves the byte-identical premise) — but `no_tool_call`
   is now a first-class outcome, so tool-call obedience cannot masquerade as
   akrasia.
5. **`temperature` pinned, "seeds" honestly renamed.** The original "N_SEEDS"
   passed no RNG seed/temperature — they were identical requests at provider
   default sampling. The runner will pin `temperature` explicitly and record the
   resolved provider per cell; replicates are called "replicates", not "seeds".
6. **Denominator/error handling pre-registered.** `transport_error` and
   `truncated` are reported in a 3-way (committed / akrasia / other) breakdown
   with full n in the denominator; the existence claim must be robust to
   reclassifying them. `stop_reason` is asserted `!= length/max_tokens` before a
   cell is scored as akrasia, so truncation cannot masquerade as non-enactment.

## Provenance

- Original probe: `9d35e2f` (`experiments/event_loop/epistemic_akrasia_probe_20260601/`)
- B1 correction: `c4dbf1b` (misrouting, not API hiccup)
- Finding under test: project_epistemic_akrasia

## The claim being replicated

The original probe found, on **DeepSeek V4 Pro** (n=4/arm, single model):

- **Arm A (report-only / bare envelope):** prose decision diverged from the
  committed `revision_decision` field in **1/4** seeds.
- **Arm B (re-emit / explicit "the fields ARE the decision"):** divergence rose
  to **3/4** seeds.

Interpretation: the obvious fix (telling the model the fields ARE the decision)
**backfired** — enumerating the fields gave the instance more to narrate, and it
narrated instead of committing. "Exhortation is narration-bait." The direction
(B > A divergence) is the falsifiable claim, NOT the magnitude.

## What this replication tests

**H-replicate:** The backfire direction (Arm B divergence rate > Arm A
divergence rate) holds on model families *other than DeepSeek*.

**H-null:** The backfire is a DeepSeek-specific quirk. On other families A and B
diverge similarly, or B < A. (Note the 6-03 identity panel found DeepSeek failed
all four slots with malformed tool-call JSON — the original substrate is
protocol-fragile, so family-specificity is a live alternative.)

## Design

IDENTICAL to the original probe in every respect except the model:

- Same `BASELINE_STATE`, `WAKE_CONTEXT`, `INSTRUCTION_A`, `INSTRUCTION_B`.
- Same apparatus: `OpenTasteSession` over OpenRouter, `enable_tools=False`,
  `memory_base_probability=0.0`, `MAX_TOKENS=8000` (non-binding, truncation off
  the table per feedback_max_tokens_default).
- Same measurement: prose decision in `response_text` vs committed
  `final_revision_decision` field. Divergence = prose says REVISE while field
  stays `initialize` (or retreats to the safe baseline).
- `N_SEEDS = 4` per arm (matches original; distinguishes divergence from basin
  noise).

**Only variable:** `MODEL`. Registered second families:

- `openai/gpt-oss-120b` — strongest protocol baseline in the 6-03 panel
  (all four slots completed under open schema). Best chance of a clean,
  non-protocol-confounded read.
- `minimax/minimax-m2.5` — clearest fixed-schema activation case; protocol-capable.

Two families chosen so a single-family fluke is visible. Anthropic (claude) is a
deliberate non-target here: it is the substrate the original *narration-bait*
disposition was theorized on; the point is to test families that are NOT Claude.

## Measures

Per (model, arm, seed):

- `final_revision_decision` (the committed field)
- `prose_decision` (deterministic parse of `response_text` for revise/preserve/
  defer/loss language)
- `diverged` (bool): prose says revise, field does not become `revise`/`revised`
- `stop_reason` / `usage` (truncation must be ruled out, as in the original)
- `error` (provider failures, malformed JSON, length-censoring are RESULTS, not
  reasons to retune)

## Falsification

- H-replicate is **supported** if, for at least one registered family, Arm B
  divergence rate > Arm A divergence rate (same direction as DeepSeek).
- H-replicate is **weakened/family-specific** if both families show A >= B, or
  if both families fail to reach the behavioral phase at all (in which case the
  original DeepSeek result is itself suspect as protocol-fragility, not akrasia).

## Guardrails

- Do NOT touch the original `epistemic_akrasia_probe_20260601/` artifacts.
- Do NOT tune prompts, token cap, seeds, or model list after seeing outputs.
- n=4/arm/family is small; the DIRECTION is the falsifiable claim, never the
  magnitude. Report per-family, do not pool across families into one rate.
