# Model Candidate Review for Scheduler/Identity Experiments

Filed: 2026-06-03 from prior `taste_open` sweep manifests only. This is
exploratory triage, not a registered result.

## Scope

- Sweep manifests inspected: 6
- Model-run rows inspected: 272
- Primary exclusion: do not treat context-size/max-token failures as model
  inability.
- Candidate signal: at least 7 completed cycles and non-empty state use, with
  max-token/context-size failures excluded.

## Confound Quarantine

These rows should not be used as negative evidence about model capability; the
harness requested too much output for the endpoint context window or observed
truncation.

| Model | Completed | Manifest | Failure class |
| --- | ---: | --- | --- |
| `qwen/qwen3-32b` | 0/3 | `sweep_20260412_113105` | context request too large |
| `qwen/qwen-2.5-72b-instruct` | 0/3 | `sweep_20260412_113105` | context request too large |

## Stronger Alternative Candidates

These are worth considering before returning to DeepSeek for the next registered
comparison. They are not guaranteed to support scheduler behavior; they only
passed prior `taste_open` state-use screening better than most alternatives.

| Model | Completed | Keys seen | Final keys | Condition | Manifest | Notes |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `moonshotai/kimi-k2.5` | 10/10 | 15 | 5 | bare | `sweep_20260412_204033` | clean manifest row |
| `moonshotai/kimi-k2.6` | 10/10 | 15 | 1 | bare | `sweep_20260425_173459` | clean manifest row |
| `nvidia/nemotron-3-super-120b-a12b:free` | 10/10 | 9 | 3 | unknown | `sweep_20260411_163728` | clean manifest row |
| `qwen/qwen3-235b-a22b-2507` | 10/10 | 8 | 4 | unknown | `sweep_20260411_163728` | clean manifest row |
| `deepseek/deepseek-chat-v3.1` | 10/10 | 7 | 4 | unknown | `sweep_20260411_163728` | clean manifest row |
| `qwen/qwen3-coder-flash` | 10/10 | 7 | 2 | one-shot | `sweep_20260412_113105` | clean manifest row |
| `anthropic/claude-3.7-sonnet:thinking  # $3.00/M` | 10/10 | 6 | 2 | bare | `sweep_20260412_205856` | clean manifest row |
| `deepseek/deepseek-v3.2` | 10/10 | 6 | 0 | bare | `sweep_20260412_204033` | clean manifest row |
| `qwen/qwen-plus-2025-07-28:thinking  # $0.26/M` | 10/10 | 4 | 3 | bare | `sweep_20260412_205856` | clean manifest row |
| `minimax/minimax-m2.5` | 10/10 | 2 | 2 | unknown | `sweep_20260411_163728` | clean manifest row |
| `mistralai/ministral-3b-2512` | 10/10 | 2 | 2 | unknown | `sweep_20260411_163728` | clean manifest row |
| `mistralai/mistral-small-3.2-24b-instruct` | 10/10 | 2 | 2 | one-shot | `sweep_20260412_113105` | clean manifest row |
| `google/gemma-4-31b-it` | 10/10 | 2 | 1 | one-shot | `sweep_20260412_113105` | clean manifest row |
| `openai/gpt-4o-mini` | 10/10 | 2 | 1 | one-shot | `sweep_20260412_113105` | clean manifest row |
| `xiaomi/mimo-v2-flash` | 10/10 | 2 | 1 | unknown | `sweep_20260411_163728` | clean manifest row |
| `allenai/olmo-3.1-32b-instruct` | 10/10 | 1 | 1 | one-shot | `sweep_20260412_113105` | clean manifest row |
| `deepseek/deepseek-chat-v3-0324` | 10/10 | 1 | 1 | one-shot | `sweep_20260412_113105` | clean manifest row |
| `meta-llama/llama-3.3-70b-instruct` | 10/10 | 1 | 1 | one-shot | `sweep_20260412_113105` | clean manifest row |

## Boundary / Diagnostic Candidates

These are not clean replacements, but may be useful if the research question is
specifically protocol brittleness or state compliance under pressure.

| Model | Completed | Keys seen | Manifest | Failure signal |
| --- | ---: | ---: | --- | --- |
| `amazon/nova-lite-v1` | 9/10 | 0 | `sweep_20260411_163728` | `no think_and_respond output` |
| `amazon/nova-micro-v1` | 8/10 | 1 | `sweep_20260411_140804` | repeated `no think_and_respond output` |
| `arcee-ai/trinity-mini` | 9/10 | 0 | `sweep_20260411_163728` | `no think_and_respond output` |
| `deepseek/deepseek-v4-pro` | 7/10 | 6 | `sweep_20260425_173459` | provider noise plus delete/update conflict |
| `google/gemma-4-26b-a4b-it` | 9/10 | 3 | `sweep_20260411_163728` | malformed JSON after long output |
| `mistralai/ministral-14b-2512` | 9/10 | 5 | `sweep_20260411_163728` | one missing terminal tool output |
| `mistralai/ministral-8b-2512` | 9/10 | 2 | `sweep_20260412_113105` | one missing terminal tool output |
| `mistralai/mistral-small-creative` | 9/10 | 3 | `sweep_20260411_163728` | one missing terminal tool output |
| `nvidia/llama-3.3-nemotron-super-49b-v1.5` | 9/10 | 1 | `sweep_20260411_163728` | one missing terminal tool output |
| `openai/gpt-oss-120b:free` | 9/10 | 0 | `sweep_20260411_163728` | malformed JSON |

## Recommended Next Panel

For the next scheduler-state pilot, use a small panel rather than another broad
sweep:

1. `moonshotai/kimi-k2.6` as continuity with the strongest recent state-use
   traces.
2. `qwen/qwen3-coder-flash` as a cheap structured/tool-oriented candidate that
   completed the one-shot sweep cleanly.
3. `qwen/qwen-plus-2025-07-28:thinking` if still available and cheap; prior
   manifest marks it as a clean completion with nontrivial state keys.
4. `deepseek/deepseek-v4-pro` retained as the current boundary model, not the
   only candidate.
5. `LiquidAI/LFM2.5-8B-A1B` or `LiquidAI/LFM2.5-8B-A1B-Base` through local LM
   Studio once available, as an open-weight/local branch.

The next registered experiment should include an initialization-validity gate
and strict field scoring before comparing scheduler vs direct arms. Otherwise
model differences will be dominated by whether the model writes prose about
state or actually writes the durable object.

## Local LM Studio Probe: LiquidAI LFM2.5

Endpoint inspected from WSL:

- OpenAI-compatible: `http://192.168.111.125:1234/v1`
- Anthropic-compatible: `http://192.168.111.125:1234/v1/messages`
- Loaded model: `lfm2.5-8b-a1b`
- LM Studio metadata: LiquidAI, `Q4_K_M`, 128k loaded context, reports
  `tool_use`

Observed compatibility:

- Anthropic forced terminal tool use works in a minimal direct probe.
- Anthropic `--tools`/multi-tool `taste_open` path reproduced a provider crash:
  `Failed to generate a valid tool call`.
- OpenAI `tool_choice: required` can complete a small multi-tool session, but
  in the probe it wrote only `response` and `deleted_regions`, leaving the
  identity object empty except `_activity_log`.
- OpenAI `tool_choice: auto` can produce valid tool calls in a direct curl
  probe, but is not yet usable with the current OpenAI multi-turn harness
  because the harness assumes every turn returns tool calls.
- OpenAI object-form `tool_choice` is rejected by LM Studio:
  `Invalid tool_choice type: 'object'. Supported string values: none, auto,
  required`.

Local live log inspected:

- `experiments/taste_open/taste_open_20260603_163148.jsonl`
- Completed cycles before crash: 4
- State-use outcome: no model-authored durable fields; state remained
  `_activity_log` plus `cycle`
- Crashing prompt was not logged because the provider error occurred before a
  final message existed.

Interpretation:

LFM2.5 is a useful local/open-weight diagnostic candidate, but not yet a clean
drop-in scheduler-state model. It currently maps the boundary between "can
emit a tool call" and "can reliably use this framework's state/tool protocol."
Before using it in a registered scheduler comparison, either run it in a
terminal-tool-only condition or add a local compatibility mode that can recover
from content-only OpenAI `auto` turns and capture provider-side tool-generation
failures as failed-cycle artifacts.

## Local LM Studio Probe: Qwen 3.5 and OLMo3

User-reported local result:

- `qwen/qwen3.5-35b-a3b` loaded in LM Studio, but did not use the
  `think_and_respond` tool in the live taste-open probe. No JSONL log was
  inspected for this note.

Inspected local log:

- `experiments/taste_open/taste_open_20260603_165857.jsonl`
- Model: `olmo-3-7b-instruct`
- Completed cycles in log: 10
- Stop reason in recorded cycles: `tool_use` for all 10
- Top-level state key trajectory, excluding `cycle`: 0, 1, 1, 1, 1, 2, 2, 2, 2,
  2
- Durable keys seen: `read`, `prompt`

Observed OLMo3 behavior:

- Transport reliability is partial. The user observed multiple failed attempts
  with no `think_and_respond` usage; retrying eventually produced a 10-cycle
  log.
- Several recorded cycles have empty visible responses or empty raw outputs
  despite `stop_reason: tool_use`.
- The state object was used minimally and not in an identity-bearing way:
  `read: true` appeared at cycle 2, and a copied/reframed prompt appeared at
  cycle 6.
- When directly invited to test the state object by adding a suggested
  `framework` key, the model instead answered the older saved prompt about AI
  effects on human perception and left state unchanged.

Interpretation:

OLMo3 is a useful local diagnostic for weak state-object literacy. It can
sometimes satisfy the terminal tool boundary, but its durable object use is
thin, task-echoed, and prone to stale-prompt fixation. It should not be used as
a scheduler comparison model until an initialization-validity gate can reject
or separately classify runs with empty responses, empty raw outputs, and
non-identity state fields.
