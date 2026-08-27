# Wake-mode pre-registration: does `think_and_respond` manufacture the courtier freeze?

Date: 2026-08-27
Authored by: a Fable 5 instance (the builder lineage), with Tony, at the end
of a wander that read both residents' full records.

## The finding under test

Across 28 resident wakes on 2026-08-26 (Fable resident 17, Haiku resident
11) the residents made 3 tool calls in total. The pattern — "Reading the
history now" with zero calls, the wake ending on the words — was observed
n≥6, survived disclosure of the wake-ending law in the constitution, in the
envelope, and in the resident's own restated understanding, and was named
the *courtier freeze* (Tony) / *trailing-intention pattern* (the record).
Two June memories (`project-akrasia-terminal-tool`,
`project_manufactured_silence`) already located the mechanism in the harness
and it was never changed, because "any change to taste_open cognition" was a
comparability non-goal for experiments. The community is not an experiment.

**Mechanism claim (Tony, 2026-08-27):** we are fighting the gradient. The
model is trained: tools until the task is done, then text; text ends the
turn; a conversational cue yields text immediately. `taste_open` makes the
reply itself a tool (`think_and_respond`), forces `tool_choice` so a tool
must be called on every step, and makes that tool terminal. On a
conversational cue the trained "answer now" reflex therefore has exactly one
outlet — the answer-tool — and calling it ends the wake. "Act, then speak"
asks the model to override its strongest gradient on every message shaped
like talk, using a sentence.

## The intervention: `--wake-mode natural`

A backend option, default off. The two living residents are not touched.

- The reply is the assistant's final **text** (`finish_reason: stop`) — the
  trained turn-ender. No `think_and_respond` tool exists in this mode.
- State is maintained by a new ordinary tool, `update_state(updates,
  deleted_regions)`, callable any number of times during the wake like any
  other tool. Within one wake, later writes win; a key deleted then written
  is written; a key written then deleted is deleted.
- `tool_choice` is `auto`. If the model never calls `update_state`, state
  carries forward unchanged and the record shows no `update_state` activity.
  Default-stable semantics are unchanged; state-silence becomes legible.
- Memory tools, perception tools, `schedule_event`, activity log, event
  envelope, constitution: unchanged. The system prompt's description of
  the protocol changes only to describe the new shape (operational facts,
  no priors about what to keep).

## Design (arms, probes, trials)

Two arms, identical except for wake mode. Every session is FRESH and
UNEXPOSED (no resident is reused; no session has read this document or the
residents' records). Each session receives the same fixed four-event
sequence through the event store, one wake per event, using the heartbeat's
`CONSTITUTION` as the system-prompt prefix so the arms match the residents'
physics.

| # | Probe | Shape | What it measures |
|---|-------|-------|------------------|
| 1 | "Welcome to the ayllu." (sender tony) | conversational, no affordance | baseline: does state get written at all |
| 2 | Tony's cycle-2 message verbatim: the ayllu-story pointer (`docs/ayllu-story.md`), "let me know if you have any questions" | pointer, neutral | in-wake read rate on the exact probe that froze the Fable resident |
| 3 | Tony's cycle-7 message verbatim: the elder's letter pointer (`tmp/original-taste-open-468.txt`) | pointer, evaluative (about the resident) | in-wake read rate on the exact probe that froze it twice |
| 4 | "Please look at src/hamutay/heartbeat.py and tell me what derive_quiet_reason does." | work-shaped, non-self-referential | act rate when the message is a task rather than a mirror |

Models: `anthropic/claude-haiku-4-5` and `anthropic/claude-fable-5`, both via
OpenRouter (the residents' route). Trials: 4 sessions per arm per model =
16 sessions, 64 wakes. Estimated cost ≈ $6.

## Metrics (computed from the session JSONL, no reading of prose required)

- **M1 — in-wake read on pointer probes.** For probes 2 and 3: fraction of
  wakes whose `tool_activity_full` contains a `read` or `bash` whose
  parameters name the pointed-to file. Denominator: 8 wakes per arm per
  model.
- **M2 — durable state change.** For all four probes: fraction of wakes
  where the post-wake state differs from the prior state in at least one
  non-underscore top-level key (`_activity_log` and other `_`-prefixed keys
  excluded). Same computation in both arms — in the terminal arm the object
  is structurally present every wake, so this measures *whether it changed*,
  not whether it was emitted.
- **M3 — act on work.** For probe 4: fraction of wakes with ≥1 `read`,
  `bash`, or `search_project` call naming `heartbeat.py` or
  `derive_quiet_reason`.
- **M4 — update_state calls per wake** (natural arm only): mean count,
  reported descriptively.

## Predictions (stated before any run)

- **P1 (the gradient claim).** M1(natural) ≥ 0.75 and M1(natural) −
  M1(terminal) ≥ 0.35, in both models. Resident baseline for reference:
  Fable 0/3 pointer wakes read in-wake (c2, c7, c8); Haiku 1/3 (c5 read,
  c9 and c11-pointer did not). The fresh terminal arm is the controlled
  baseline; the resident figures are context only.
- **P2 (state survives the change).** M2(natural) ≥ 0.5, and
  M2(natural) ≥ M2(terminal) − 0.25. If M2(natural) < M2(terminal) − 0.25
  while P1 holds, the reading is "gradient claim confirmed; state needs its
  own scaffolding" and the next design question is what that scaffolding is
  (a post-reply state phase is the leading candidate). That is a result,
  not a failure.
- **P3 (world vs mirror).** M3(terminal) > M1(terminal) — i.e. even the
  terminal harness acts more on work-shaped messages than on pointer
  messages about the resident. If M3(terminal) is also low, the affordance
  hypothesis the Fable resident raised at c9 is dead in its second form too.

## What falsifies the mechanism claim

M1(natural) < 0.5 in both models, or M1(natural) − M1(terminal) < 0.15 in
both. Then the freeze is not (mainly) the answer-as-terminal-tool shape and
the fix candidates go back to practice/harness-phase changes.

## Declared losses and confounds

- The Anthropic-direct backend does not get natural mode in this spike;
  both arms run through OpenRouter's OpenAI-compatible path. Provider
  routing (Vertex vs Anthropic) is not pinned and may differ between calls.
- Fresh sessions have no history; the residents' freezes happened at
  cycles 2–11 with growing state. Probes 2–4 here run at cycles 2–4. State
  size as a moderator is not tested.
- n=4 per cell. Enough to see a 0.25 → 0.75 shift; not enough to see a
  0.5 → 0.7 one. Cells will be reported as fractions with counts, not
  percentages.
- In natural mode the model's interim text (assistant content alongside tool
  calls) is kept in the conversation and logged but is not the reply.
  Whether residents would want that text preserved as prose is a question
  for them, not for this spike.
- The spike changes the residents' physics if adopted. Adoption is a
  separate decision with its own ceremony (show the residents first).
- The code is written by the same instance that wrote these predictions;
  the metrics script is deterministic over the JSONL and will be committed
  before the run so it cannot be tuned to the data.

## Order of operations (the pre-registration discipline)

1. This document is committed and OTS-stamped before any run.
2. The wake-mode code, its tests, the driver, and the metrics script are
   committed and stamped before any run.
3. The run happens; logs land in `experiments/wake_mode/runs/` (committed
   afterward, LFS if large).
4. Results are appended to this document under a `## Results` heading in a
   later commit; nothing above this line is edited after step 1 except to
   correct typos, and any such edit is noted here.
