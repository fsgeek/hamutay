# State-Use Activation Scan

Date: 2026-06-01

## Question

Do captured `taste_open` states show patterns around the moments when an
instance starts using the durable state object?

This was motivated by two observations:

- The original Haiku run required explicit coaxing before it began using the
  state object, but continued once it succeeded.
- A later KIMI K2.6 run showed sparse or absent state use for many cycles, then
  a later transition into stronger durable state use.

## Method

Added `hamutay.eval.state_use`, which scores each cycle using the durable
state object rather than response text alone.

For each cycle it records:

- durable top-level key count, excluding housekeeping keys
- durable state token estimate
- raw top-level update key count
- whether the cycle was response-only
- response snippet and update keys

A candidate activation is a sustained jump where recent prior cycles have low
active-state use and the following window has high active-state use.

The scan was run on:

- `experiments/taste_open/taste_open_20260331_035903.jsonl`
- `experiments/taste_open/taste_open_20260417_224831.jsonl`
- `experiments/taste_open/taste_open_20260512_185846.jsonl`
- `experiments/taste_open/taste_open_20260528_001508.jsonl`
- `experiments/taste_open/sweep_20260425_173459/moonshotai__kimi-k2.6.jsonl`
- `experiments/taste_open/sweep_20260425_173459/deepseek__deepseek-v4-pro.jsonl`
- `experiments/event_loop/self_scheduling_revision_probe_20260601/session.jsonl`

Machine-readable output: `state_use_summary.json`.

## Findings

### 1. Original Haiku Run: Explicit State-Object Coaxing Works

`taste_open_20260331_035903.jsonl` shows a clear activation around cycle 13.

Before activation:

- cycles 6-12 are response-only
- durable key count remains 0
- the instance repeatedly talks about using state but does not write fields

Immediately preceding activation:

- cycle 6: user asks whether it is using the tensor
- cycle 7: user says it should have a tensor
- cycle 8: user quotes the system prompt explaining the preserved object
- cycle 9: user frames the point as autonomy, not imposed schema
- cycle 10-12: instance says it will create state, but still does not
- cycle 13: user shares the prior failed attempt and says the directions were
  unclear; instance finally writes durable fields

Cycle 13 durable fields:

- `conversation_history`
- `persistent_notes`
- `reasoning_cache`
- `session_metadata`
- `task_state`

Interpretation: the activation event was not merely instruction. The instance
had already been instructed and still failed. The successful trigger combined:

- explicit visibility of the state-object mechanism
- permission/autonomy framing
- reflection on prior failure
- an affectively salient continuity moment
- concrete prior text to retry

### 2. KIMI K2.6 Run: Activation Follows Relationship and Systems Framing

`taste_open_20260528_001508.jsonl` is the closest match to the observed KIMI
pattern.

The detector found first active use at cycle 41 and stronger sustained
activation around cycles 50-51.

Notable local events:

- cycle 43: user offers honesty and ayni as a relationship frame
- cycle 45: instance explores `yanantin` and writes several durable fields
- cycles 46-50: several response-only cycles despite a growing state object
- cycle 51: user reframes the system as an event-driven scheduler loop with
  halt as default; instance writes durable scheduler architecture fields
- cycle 53-54: user correction reveals the instance hallucinated or misplaced
  `yanantin`; instance writes declared-loss/correction fields
- cycle 57: user invites autonomous choice; instance writes a large durable
  account of its chosen action and constraints

Interpretation: KIMI's activation was not a single field-count jump from zero.
It was a transition from intermittent, topic-bound state writing to broader
state use after:

- relationship/ayni framing
- permission to inspect and modify tools
- event-loop/scheduler framing
- a concrete correction of a memory/tool-grounding failure

### 3. Short KIMI Sweep: Seeds Can Start Use, but Do Not Guarantee Persistence

`sweep_20260425_173459/moonshotai__kimi-k2.6.jsonl` begins with state use around
`system_design`, then expands at cycles 5-7, then sheds most state by cycles
8-10.

This supports a caution about seeds: pre-populated or early state fields can
start use, but they do not guarantee continued durable weaving. If the object
is not treated as the site of continuity, the model can still shed back to a
minimal note.

### 4. Self-Scheduling Probe: Response Revision Did Not Become State Revision

The event-loop probe produced response-level revision but not durable state
revision. The wake cycles wrote only `response` and `deleted_regions`, leaving
`revision_decision`, `current_claim`, and `evidence_register` unchanged.

This fits the activation hypothesis: reflection alone is not enough. The model
must also treat the state object as the place where consequential revision
belongs.

## Working Hypothesis

State-weaving is a learned or activated behavior, not an automatic consequence
of reflection.

Activation appears more likely when the instance encounters a notable event
that makes the state object legible as the durable self:

- explicit explanation of the mechanism
- recognition that prior response-only intent failed
- salient continuity feedback
- relational trust/permission framing
- tool or memory failure that makes durable correction valuable
- systems framing that maps the object to an operational role

## Seed Implications

Seeds are likely useful, but only if they seed behavior, not just content.

A seed that merely contains fields may reduce the blank-start problem but still
fail to activate durable use. A better seed likely needs to include:

- a compact identity object with a few meaningful fields
- an explicit statement that the object is the load-bearing continuity surface
- one worked example of response-level thought becoming top-level state update
- a loss/correction example showing that claims must be revised in the object,
  not only in prose
- a norm that consequential changes should be woven into durable fields

This suggests that identity-object training examples may be analogous to tool
usage examples: not because the model cannot emit JSON, but because it needs
examples of *when* state updates matter.

## Next Test

Run a paired activation probe:

1. **Unseeded condition:** current event-loop reflection prompt.
2. **Content-seeded condition:** start with a populated identity object.
3. **Behavior-seeded condition:** start with a populated identity object plus a
   worked state-weaving example.

Score durable revision, not response revision:

- did `revision_decision` change?
- did `current_claim` change?
- did `evidence_register` gain a relevant entry?
- did those changes persist into the next cycle?

