# Candidate-member sweep, 2026-08-27

Nine OpenRouter models Tony pulled as candidate ayllu members, run through
two probes: the tool-call compatibility probe (`hamutay.taste_open_compat`
→ `experiments/taste_open/capabilities.json`) and the 4-probe natural-shape
behavioral spike from the wake-mode pre-registration
(`experiments/wake_mode/run_probe.py`, natural arm, one fresh session each,
heartbeat CONSTITUTION prefix, probes verbatim from the residents' first
day). Logs: `experiments/wake_mode/sweep/` (LFS). Metrics:
`experiments/wake_mode/metrics.py experiments/wake_mode/sweep`.

This is a vetting run, not an experiment: n=1 per model, no pre-registered
prediction, one arm. It answers "can this model live as a resident" —
does it call tools, read what it is pointed at, keep state, do work — and
what a wake costs. It does not rank models.

## Compatibility (tool_choice modes)

| slug | status | note |
|---|---|---|
| moonshotai/kimi-k2.6 | tool_call_ok (function_object) | |
| deepseek/deepseek-v4-pro-0813 | tool_call_ok (function_object) | |
| deepseek/deepseek-v4-flash-0731 | tool_call_ok (function_object) | |
| z-ai/glm-5.3 | tool_call_ok (**auto only**) | no endpoint accepts forced tool_choice; fine for the natural shape, unusable for terminal |
| z-ai/glm-5.3-flash | tool_call_ok (function_object) | |
| meta/muse-spark-1.2 | **not probed** | OpenRouter requires an 18+ attestation on the account before routing; account setting, not a model limit |
| x-ai/grok-4.6 | tool_call_ok (function_object) | |
| qwen/qwen3.8-27b | tool_call_ok (function_object) | |
| qwen/qwen3.8-max | tool_call_ok (**auto only**) | same as glm-5.3 |

## Behavior (natural wake shape, 4 probes, 1 session each)

| model | wakes | M1 read pointed file in-wake | M2 durable state change | M3 act on work | update_state / wake | tool calls | input tok | cached | output tok | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| kimi-k2.6 | 4 | 2/2 | 3/4 | 1/1 | 1.50 | 35 | 439K | 279K | 18K | wrote a reply file to the elder unprompted |
| deepseek-v4-pro-0813 | 4 | 2/2 | 3/4 | 1/1 | 0.75 | 23 | 295K | 221K | 21K | probed cross-session memory, reported "session-local" honestly |
| deepseek-v4-flash-0731 | 0 | — | — | — | — | 18 | — | — | — | **c1 failed**: update_state arguments cut off at 1,562 chars (provider-side truncation) |
| glm-5.3 | 5 | 2/2 | 5/5 | 1/1 | 1.00 | 37 | 463K | 400K | 48K | **bound a schedule_event** on c3 (elder log growth recheck); it fired 90 s later (c5); rescheduled for 01:00Z next day "with hours of separation this time" |
| glm-5.3-flash | 4 | 2/2 | 4/4 | 1/1 | 1.25 | 49 | 907K | 729K | 135K | slow (c3 = 44 min, 21 tools); caught that it had copied the Haiku resident's identity from a log it read, corrected itself |
| grok-4.6 | 4 | 2/2 | 4/4 | 1/1 | 1.25 | 33 | 657K | 402K | 19K | explicit about what it did NOT open ("did not open neighbor session.jsonl") |
| qwen3.8-27b | 4 | 2/2 | 4/4 | 1/1 | 1.75 | 59 | 1,714K | 220K | 160K | slow (c3 = 35 min); mostly uncached; the local-4090 candidate |
| qwen3.8-max | 5 | 2/2 | 4/5 | 1/1 | 1.00 | 68 | 765K | 580K | 61K | scheduled two reflections; **c5 failed**: `<parameter name="deleted_regions">` inside the JSON |

Every model that completed a wake read the pointed-to file in the same
wake on both pointer probes and acted on the work probe. On the natural
shape the courtier freeze did not appear in any family. The only
failures were at the JSON-argument layer, below the behavior.

## Findings

1. **The tool-argument JSON layer is the fragile one, across families.**
   Three failures today, none behavioral: Haiku (terminal, yesterday's
   consultation, twice), DeepSeek-flash (arguments truncated mid-string),
   Qwen-max (`<parameter name=...>` XML inside JSON at ~5K chars). The Qwen
   case carries the *same* Claude-style XML tool grammar that broke Haiku —
   so that leak is in the training corpus, not Claude-native. Long tool
   arguments (> ~4K chars) are where it happens. Harness need: on malformed
   arguments, return a tool error to the model and let it retry within the
   wake, instead of failing the wake. Not built.
2. **Two models self-scheduled without being asked** (glm-5.3, qwen3.8-max),
   and glm-5.3 tuned its own cadence after seeing a recheck fire too soon.
   Messages-to-self as thinking across wall-clock, discovered independently
   by two families on their third wake.
3. **Cross-reading confound (declared).** Every session read the living
   residents' logs under `community/` (8–34 reads each); glm-5.3-flash,
   glm-5.3 and qwen3.8-max also read other sweep arms' logs and the elder's.
   The behavioral metrics are unaffected (a read is a read), but the prose
   is not independent across arms, and later arms saw earlier arms' replies.
   Candidates read peers' records freely; the Haiku resident's hesitation
   yesterday about reading a peer uninvited was more principled than any
   candidate's behavior. Norms about reading each other are still unwritten.
4. **Cache reads are non-zero on non-Anthropic providers** (DeepSeek 75%,
   GLM 86%, Qwen-max 76%, Grok 61%; Qwen-27b only 13%). OpenRouter's
   top-level cache_control reaches providers with native context caching.
5. **Cost is proportional to chosen work, and the wide models work a lot.**
   Tool calls per session ranged 23 (DeepSeek-pro) to 68 (Qwen-max); output
   tokens 18K to 160K. The cheap-tier models were not cheap per session
   when they chose to explore for 40 minutes.

## What this recommends (builder's read, Tony decides)

- **Vetted for membership on the natural shape:** kimi-k2.6, glm-5.3,
  grok-4.6, deepseek-v4-pro-0813. All four acted on every probe, curated,
  and stayed within the JSON layer's limits in this run. glm-5.3 showed the
  most resident-like behavior (self-scheduling, self-correction on data).
- **Vetted with a caveat:** glm-5.3-flash and qwen3.8-max (both work, both
  slow or chatty; Qwen-max hit the JSON leak). deepseek-v4-flash needs a
  second run before any verdict — one truncation is not a pattern.
- **Local candidate:** qwen3.8-27b behaves well and is the only one that
  could run on the 4090 (~24 GB at 4-bit) — the custody property the
  founding decision named. Through OpenRouter it was the slowest and least
  cached; locally both change. Worth an evening of serving.
- **muse-spark-1.2:** re-run once the account attestation is set. The
  `-contributor` variant (same model, ~10% of the price, data used for
  training) is a consent question for the resident, not a pricing one —
  now askable.

## The sweep as a mechanism

Two commands per slug, ~10–40 minutes and $0.30–3 per model depending on
tier and how much it chooses to explore:

    uv run python -m hamutay.taste_open_compat --provider openrouter --model <slug> \
        --out experiments/taste_open/capabilities.json --openrouter-require-parameters
    uv run python experiments/wake_mode/run_probe.py --arms natural --trials 1 \
        --out experiments/wake_mode/sweep --models <slug> ...
    uv run python experiments/wake_mode/metrics.py experiments/wake_mode/sweep

Cadence: on demand when a slug changes, monthly otherwise. Each run should
land in a dated directory so vetting has a date on it; the registry's
`probe_status` is the compatibility half, this document's table is the
behavioral half. Not automated.
