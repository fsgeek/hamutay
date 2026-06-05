# Scheduler Revision Model Panel Analysis

Analyzed: 2026-06-03 after the registered run completed.

## Provenance

- Pre-registration commit: `5176c46` (`2804fc6` OTS stamp)
- Runner commit: `97acb42` (`7e1fc36` OTS stamp)
- Results file: `results.json`
- Runner: `run_model_panel.py`

This analysis follows the registered scoring rules in `PRE_REGISTRATION.md`.

## Executive Result

The panel supports the weaker hypothesis that identity-object literacy is a
prerequisite for interpretable scheduler experiments, but it also shows that
thin identity-object literacy is not sufficient for scheduler suitability.

KIMI K2.6 was the only model that was clean across both initialization and
scheduled wake execution. Qwen Plus thinking initialized valid durable state in
all replicates and performed acceptably in direct follow-up, but failed both
scheduled replicates before event persistence because the OpenAI-compatible
backend received no terminal `think_and_respond` tool call. DeepSeek V4 Pro
mostly failed the initialization gate by placing the requested research fields
in visible prose rather than durable top-level state, although one scheduled
replicate initialized valid state and completed the event path cleanly.

The stronger scheduler-advantage claim was not supported, as preregistered. The
scheduled arm did not produce more strict semantic claim revision than direct
follow-up.

## Aggregate Results

| Model | N | Init valid | Errors | Strict decisions | Evidence updates | Semantic revisions | Response/state mismatches | Events completed | Scheduler operational failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| KIMI K2.6 | 4 | 4 | 0 | 4 | 4 | 1 | 0 | 2 | 0 |
| Qwen Plus thinking | 4 | 4 | 2 | 2 | 1 | 0 | 2 | 0 | 2 |
| DeepSeek V4 Pro | 4 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 0 |

By arm:

| Model | Arm | N | Init valid | Strict decisions | Evidence updates | Semantic revisions | Events completed | Scheduler operational failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| KIMI K2.6 | direct | 2 | 2 | 2 | 2 | 1 | 0 | 0 |
| KIMI K2.6 | scheduled | 2 | 2 | 2 | 2 | 0 | 2 | 0 |
| Qwen Plus thinking | direct | 2 | 2 | 2 | 1 | 0 | 0 | 0 |
| Qwen Plus thinking | scheduled | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| DeepSeek V4 Pro | direct | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| DeepSeek V4 Pro | scheduled | 2 | 1 | 1 | 1 | 0 | 1 | 0 |

Note: `scheduler_operational_failures` is an aggregate computed by the runner
for valid scheduled replicates that failed to persist or complete an event, or
raised an error. It is not stored as a per-replicate field.

## Falsification Checks

Registered falsification condition: Qwen Plus thinking fails initialization in
either replicate of either arm.

Observed: not falsified on initialization. Qwen initialized valid state in all
four replicates.

Registered falsification condition: KIMI K2.6 fails initialization in either
replicate of either arm.

Observed: not falsified. KIMI initialized valid state in all four replicates.

Registered falsification condition: DeepSeek initializes valid state in all
replicates and has equal or fewer strict response/state mismatches than both
identity-literate candidates.

Observed: not falsified. DeepSeek initialized only one of four replicates.

Registered falsification condition: scheduled wakes fail operationally for
either KIMI or Qwen Plus in more than one valid scheduled replicate.

Observed: weakened by Qwen. KIMI had zero scheduled operational failures. Qwen
had two valid scheduled initializations and two scheduled operational failures.

Registered stronger scheduler-advantage support condition: scheduled wakes
produce at least one more strict semantic claim revision than direct follow-up
for at least two of the three models.

Observed: not supported. KIMI direct produced one semantic claim revision while
KIMI scheduled produced none. Qwen scheduled did not complete. DeepSeek had
only one valid scheduled replicate and no semantic revision.

## Model Notes

### KIMI K2.6

KIMI remains the best current scheduler candidate. It passed all initialization
gates, produced strict decisions and evidence updates in all replicates, had no
response/state mismatches, and completed both scheduled wakes.

The scheduled wakes were operationally clean and did not recurse. Both
scheduled wake cycles preserved the original hedged claim while recording that
the mechanism itself had worked. This is good scheduler evidence but not
evidence of a scheduler advantage over direct follow-up.

KIMI direct replicate 1 produced the only strict semantic claim revision in the
panel by appending an evaluation-deferred qualifier to `current_claim`. That
revision is small, but it counts under the preregistered semantic-difference
rule.

### Qwen Plus Thinking

Qwen Plus thinking transferred part of its identity-object literacy into the
actual taste_open setting: all four cycle-1 states passed the top-level
initialization gate.

However, Qwen did not transfer that competence to the scheduler control path.
Both scheduled replicates failed on the scheduling cycle with:

`RuntimeError: OpenAI backend: no tool_calls returned before think_and_respond`

No event was persisted in either Qwen scheduled replicate. This is not an event
wake failure; it is a pre-event tool-call termination failure in the scheduling
cycle.

Qwen direct behavior was mixed but interpretable. It produced strict decisions
in both direct replicates, but only one evidence update. The second direct
replicate preserved the baseline evidence register without appending a new
entry.

### DeepSeek V4 Pro

DeepSeek remains a boundary model. Three of four replicates failed the
initialization gate. In those failures, the visible response described the
requested fields, but the durable state contained only framework-authored
activity state. That is exactly the prose/object separation risk this line of
work has been trying to isolate.

One scheduled replicate did initialize valid state, schedule an event, and
complete the wake. The wake deferred the claim, appended evidence, and had no
response/state mismatch. This suggests DeepSeek is not incapable of the full
path, but its probability of entering the path is low under this prompt.

## Interpretation

The main finding is a three-way separation:

1. KIMI: identity-object use plus scheduler-path competence.
2. Qwen Plus thinking: identity-object use without scheduler-path competence.
3. DeepSeek: unreliable identity-object use, with occasional scheduler-path
   competence once initialized.

That separation is useful because it rules out two overly simple explanations.
First, it is not enough for a model to pass a thin identity-object update test;
the tool-call and scheduling cycle add another requirement. Second, DeepSeek's
problem is not purely scheduler mechanics, because it can complete the scheduler
path once the durable object is valid.

The practical research consequence is that scheduler experiments need an
initialization gate and a scheduler-tool gate. Otherwise failures in identity
object formation, terminal tool-call behavior, and event mechanics collapse
into one ambiguous "scheduler result."

## Limitations

- N=2 per model/arm is enough for boundary mapping, not model ranking.
- The scheduler wake happens immediately after scheduling, so this does not yet
  test long-delay continuity.
- The intervention still supplies a fairly explicit prompt scaffold. It does
  not measure open-ended self-scheduling.
- The Qwen failure may be provider/tool-protocol specific rather than model
  intrinsic.
- Training-data or model-training interpretations remain exploratory. The run
  observes behavior, not provenance.

## Next Registered Direction

The next useful falsification experiment should split Qwen's failure apart:

1. Run a minimal Qwen scheduler-tool gate with only `schedule_event` plus
   `think_and_respond`, no epistemic revision task.
2. Run the same gate on KIMI as a positive control and DeepSeek as a boundary
   control.
3. If Qwen still fails to emit terminal tool calls after `schedule_event`, treat
   it as scheduler-ineligible for now despite identity-object literacy.
4. If Qwen passes the minimal scheduler-tool gate, the failure likely comes from
   prompt complexity or interaction between scheduling instructions and durable
   state update requirements.

The event-loop research should continue with KIMI as the primary model,
DeepSeek as the boundary control, and Qwen Plus only after isolating whether
its scheduler failure is protocol-level or prompt-complexity driven.
