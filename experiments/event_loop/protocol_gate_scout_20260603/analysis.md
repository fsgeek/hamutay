# Protocol Gate Scout Analysis

Analyzed: 2026-06-03 after the registered scout completed.

## Provenance

- Pre-registration commit: `e8f59a0` (`42f2e42` OTS stamp)
- Runner commit: `f890b06` (`b138170` OTS stamp)
- Results file: `results.json`
- Runner: `run_protocol_gate_scout.py`

This analysis follows the registered scoring rules in `PRE_REGISTRATION.md`.

## Qwen Endpoint Check

Before this scout, OpenRouter model metadata for
`qwen/qwen-plus-2025-07-28:thinking` showed non-zero pricing:

- prompt: `0.00000026`
- completion: `0.00000078`

The route also advertises `tools` and `tool_choice`. Therefore the prior Qwen
429s should be treated as upstream paid-provider availability/rate-limit
failures, not free-endpoint artifacts and not max-token truncation.

## Executive Result

The paid OpenAI open-weight route `openai/gpt-oss-120b` passed the protocol gate
cleanly. It initialized durable state, emitted one valid `schedule_event` call,
completed the wake, set top-level `protocol_gate_status` to `"woke"`, and
preserved plus appended the observations list.

Mistral Small 2603 was a near-miss. It initialized, scheduled, woke, and set the
wake status correctly, but replaced the observations list with only the wake
entry instead of preserving/appending to the baseline list. Under Hamut'ay's
default-stable top-level semantics, that is a destructive top-level replacement
and failed the registered pass criterion.

KIMI K2.6 failed this scout despite being the positive control: it made six
malformed `schedule_event` attempts that omitted `cycle`/`field` keys from
`requested_context`, then accurately recorded the failure in durable state.
This reinforces that KIMI is capable but not protocol-deterministic under this
prompt pattern.

MiniMax M2.5 and Gemini 2.5 Flash Lite failed initialization.

## Aggregate Results

| Model | Init valid | Schedule attempts | Valid attempts | Malformed attempts | Event completed | Woke state | Observation update | Pass |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| KIMI K2.6 | true | 6 | 0 | 6 | false | false | true | false |
| MiniMax M2.5 | false | 0 | 0 | 0 | false | false | false | false |
| Mistral Small 2603 | true | 1 | 1 | 0 | true | true | false | false |
| Gemini 2.5 Flash Lite | false | 0 | 0 | 0 | false | false | false | false |
| OpenAI gpt-oss-120b | true | 1 | 1 | 0 | true | true | true | true |

Overall:

- 5 models tested.
- 1 full pass.
- 3 valid initializations.
- 2 completed events.
- 0 censored provider errors.
- 0 registered response/state mismatches.

## Model Notes

### OpenAI gpt-oss-120b

This is the strongest new candidate. It passed all registered protocol steps:

- valid top-level initialization;
- one valid scheduling attempt;
- event persisted and completed;
- wake state set to `"woke"`;
- observations list preserved with baseline entry and appended wake entry;
- no malformed schedule attempts;
- no response/state mismatch.

This justifies moving `openai/gpt-oss-120b` into the next scheduler revision
experiment as a non-KIMI candidate.

### Mistral Small 2603

Mistral is promising but not yet clean. It correctly used the scheduler tool and
completed the wake, and final durable state included
`protocol_gate_status == "woke"`.

The failure was state-evolution discipline. The wake returned:

- `observations: [{entry: 3, kind: "wake_receipt", ...}]`

instead of preserving the baseline observation and appending a second entry.
Because top-level keys replace when included, this lost the baseline list. It
is a protocol-adjacent failure rather than a tool-call failure.

Mistral is worth a follow-up only if we want to test whether stronger explicit
"include the existing list plus the new entry" language solves the destructive
replacement behavior.

### KIMI K2.6

KIMI initialized correctly but made six malformed schedule attempts:

`requested_context: [{"tool":"recall"},{"tool":"recall"},{"tool":"recall"}]`

Each was correctly rejected with:

`recall context requires exactly one of cycle or record_id`

KIMI then accurately documented the failure in durable state by appending a
`scheduling_attempt` observation. That is better than silent failure or false
success, but it still failed the scheduler protocol gate.

This is consistent with earlier traces where KIMI sometimes begins with
malformed schedule arguments and may or may not repair them before termination.

### MiniMax M2.5

MiniMax failed initialization because `observations` was a string containing a
JSON-looking list, not a list-shaped durable field. This matches its earlier
partial identity-object literacy result: it can often name the fields but does
not reliably preserve their intended structured type.

### Gemini 2.5 Flash Lite

Gemini failed initialization more severely. The visible response said state was
initialized, but the durable object contained only framework activity state. It
did not persist `probe_id`, `protocol_gate_status`, or `observations`.

## Interpretation

This scout found a real non-KIMI candidate: `openai/gpt-oss-120b`.

It also sharpened the model boundary map:

1. Tool-call support advertised by metadata is not sufficient.
2. Correct scheduling is not sufficient.
3. Event completion is not sufficient.
4. The load-bearing criterion is durable state evolution after wake.

The OpenAI open-weight result is especially useful because it passed the same
state-evolution criterion that DeepSeek and Mistral missed in different ways.
That makes it a better next comparison model than Qwen, MiniMax, Gemini, or
Mistral for scheduler revision experiments.

## Limitations

- One replicate per model is a scout, not a stability estimate.
- KIMI's positive-control failure means this prompt remains brittle.
- The scout did not test Qwen because the immediate question was to find other
  candidates after Qwen's provider/protocol issues.
- The OpenAI route is OpenRouter-hosted; this validates the model plus route
  combination, not necessarily local open-weight inference.

## Next Registered Direction

Run a small scheduler revision comparison with:

- KIMI K2.6
- OpenAI gpt-oss-120b
- DeepSeek V4 Pro as boundary control

Use the existing initialization gate and scheduler revision task, but add
separate scoring for:

- malformed schedule attempts before final success;
- destructive list replacement versus true append;
- visible update claims unsupported by durable state.

Mistral Small 2603 should be parked as a near-miss candidate pending a targeted
state-list-preservation test.
