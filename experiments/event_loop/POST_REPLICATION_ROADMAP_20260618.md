# Post-Replication Event-Loop Roadmap

Date: 2026-06-18

## Purpose

This artifact preserves the current roadmap after the committed prospective live
replication of symbolic event-loop append-only non-inferiority. It is intended
to be referenced by future goals so the thread does not rely on in-context
memory alone.

## Evidence Anchor

Prospective protocol:

- Commit: `156dc71` (`Preregister symbolic append-only replication`)
- Experiment: `event_loop_symbolic_append_only_noninferiority_20260618`
- Symbolic contract: `framework_bound_symbolic_continuation.v1`

Live evidence:

- Commit: `1060849` (`Record symbolic append-only live replication`)
- Result directory:
  `experiments/event_loop/event_loop_symbolic_append_only_noninferiority_20260618_direct_deepseek`
- Endpoint: direct DeepSeek, `https://api.deepseek.com`
- Model: `deepseek-v4-pro`
- Classification: `survived`
- Event-loop mean artifact quality: `0.85`
- Append-only mean artifact quality: `0.85`
- Shared-surface observability: event-loop `1.0`, append-only `1.0`
- Scheduler reconstruction added value: `1.0`

Important caveat: declared-loss rate was `0.0` across both conditions. The
replication supports non-inferiority under the committed scoring rule, but it
does not show that either condition handled declared-loss discipline well.

## Ordering Principle

Prefer experiments that maximize information gain while preserving failure
attribution clarity. Do not add broad degrees of freedom before isolating the
clearest known weakness.

In short:

1. Reduce ambiguity in the measurement surface.
2. Then raise the comparison bar.
3. Then lengthen the loop.
4. Then add concurrency and operational recovery.
5. Then generalize across providers.

## Current Priority

Current roadmap state: `complete`.

Next execution target:

> No remaining item on this roadmap. Future work should open a new roadmap or
> extend this one with a new decision log entry.

Reason this is complete: all six roadmap items have committed protocol and
result evidence. The final provider panel passed with direct DeepSeek as the
known-good anchor and OpenRouter DeepSeek as the alternate provider row.

Measurement policy carried forward:

- future exact declared-loss scores require an explicit exact-marker contract in
  the prompt/rubric; or
- a future experiment must preregister a semantic declared-loss scorer before
  using semantic loss declarations as scored evidence.

Closure criteria:

- all six roadmap items have committed result evidence;
- the provider panel ran the same small protocol across direct DeepSeek and
  OpenRouter DeepSeek;
- provider-specific terminal-surface failures were separated from framework
  failures; and
- no framework failure remained on the final panel.

## Roadmap

### 1. Declared-Loss Discipline Stress Test

Rationale: This is the clearest weakness exposed by the prospective
replication. Both conditions survived, but both failed declared-loss discipline
under the current scorer. A narrow stress test should determine whether the
failure is caused by prompt/rubric design, model behavior, or harness/scoring
behavior.

Expected output: an experiment that makes loss declaration unavoidable and
checks whether the loss materially changes the recommendation.

Status: complete. Result:
`experiments/event_loop/declared_loss_discipline_stress_20260618_direct_deepseek`.
Classification: `prompt_rubric_primary_with_lexical_scorer_caveat`. The model
declared the limitation semantically in the unanchored live row but did not
receive exact-marker credit; it passed exact-marker scoring when the prompt
included the exact declared-loss contract.

### 2. Harder Append-Only Baseline

Rationale: The current append-only bar may be too low. Hardening the baseline
before resolving declared-loss scoring would confound failures, so this comes
second.

Expected output: a stricter append-only baseline prompt, rubric, or task set
that tests whether event-loop non-inferiority survives against a stronger
one-shot condition.

Status: complete. Result:
`experiments/event_loop/harder_append_only_baseline_20260618_direct_deepseek`.
Classification: `survived`. Event-loop mean artifact quality was `1.0`; harder
append-only mean artifact quality was `1.0`; both conditions had declared-loss
rate `1.0` across all rows under the exact-marker contract.

### 3. Longer-Horizon Sustained Loop

Rationale: This is strategically central to the event-loop thesis, but it has
more moving parts. It should follow cleaner measurement and baseline surfaces.

Expected output: a sustained single-entity loop with inbound work,
self-scheduled continuation, housekeeping, restart frontier updates, and final
artifact synthesis across more than one task.

Status: complete. Result:
`experiments/event_loop/longer_horizon_sustained_loop_20260618_direct_deepseek`.
Classification: `passed`. The run completed two inbound tasks, two
framework-bound continuations, two housekeeping events, one final artifact
synthesis, and eight restart-frontier commits with no failure attribution.

### 4. Multi-Entity Event Loop

Rationale: Multi-entity scheduling adds identity, isolation, attribution, and
fairness concerns. These are valuable only after a single-entity sustained loop
is credible.

Expected output: a panel with multiple AI entities or workstreams and explicit
checks for identity drift, context contamination, and attribution errors.

Status: live attempt failed. Result:
`experiments/event_loop/multi_entity_event_loop_20260618_direct_deepseek`.
Classification: `failed`. The run completed all six expected events, used the
expected terminal surfaces, preserved the red/red_stream and blue/blue_stream
identity pairs on entity-scoped events, and wrote seven restart-frontier
records. It failed the audit and final contamination/attribution checks because
the blue continuation included an `entity_red` reference and the audit marked
that as possible context contamination. Inspection showed blue's prior wake
state inherited red's `continuation_status` and `probe_status`, so the next
highest-information step is an entity-scoped state isolation repair probe rather
than the restart/resume test.

Repair status: complete. Result:
`experiments/event_loop/multi_entity_state_isolation_repair_20260618_direct_deepseek`.
Classification: `passed`. The repair restored entity-scoped wake state before
each entity event. The live run completed all six events, preserved explicit
entity/workstream identity, showed no foreign-entity mentions in entity-event
prior states, passed audit/final contamination and attribution checks, and
wrote restart-frontier evidence with no failure attribution records.

### 5. Restart/Resume Under Interruption

Rationale: Existing restart-frontier evidence is structural. A stronger test
should deliberately interrupt and resume a nontrivial loop.

Expected output: a run that interrupts mid-execution and resumes from committed
artifacts without losing scheduler identity, carried state, or failure
attribution.

Status: complete. Result:
`experiments/event_loop/restart_resume_interruption_20260618_direct_deepseek`.
Classification: `passed`. The run completed inbound, self-scheduled
continuation, and housekeeping events. The housekeeping event history was
`pending`, `running`, `pending`, `running`, `completed`, demonstrating recovery
from an interrupted claimed event. No events were suppressed, completed result
records were present in the resumed session log, five restart-frontier records
were written, and no failure attribution records were produced.

### 6. Provider Variance Panel

Rationale: Provider differences are real, but broad provider comparison is less
useful before the task and scoring surfaces are sharper.

Expected output: a small provider panel that distinguishes framework robustness
from provider-specific terminal-surface behavior.

Status: complete. Result:
`experiments/event_loop/provider_variance_panel_20260618`.
Classification: `passed`. The panel reused the committed direct DeepSeek
restart/resume result as the known-good anchor and added an OpenRouter DeepSeek
row using the same restart/resume protocol with terminal tool choice `auto`.
Both rows passed; the panel conclusion was
`no_provider_variance_detected_on_panel`.

## Recommended Roadmap Goal

Maintain and refine the post-replication roadmap for event-loop viability:
prioritize experiments by information gain and attribution clarity, starting
with declared-loss discipline, then harder append-only baseline, longer-horizon
sustained loop, multi-entity scheduling, restart/resume interruption, and
provider variance.

## Recommended Next Execution Goal

Open a new roadmap if the next research question is broader than this
post-replication sequence. Candidate next directions are larger provider
panels, longer-horizon multi-entity operation, or moving the experiment-layer
state isolation repair into reviewed substrate code.

## Decision Log

- 2026-06-18: Created roadmap after prospective symbolic append-only
  replication survived. Ranked declared-loss discipline first because it is the
  clearest observed weakness and can be isolated without adding sustained-loop,
  multi-entity, restart, or provider-panel degrees of freedom.
- 2026-06-18: Refined roadmap with explicit current priority and readiness
  criteria so future goals can target this artifact directly.
- 2026-06-18: Completed declared-loss discipline stress test. Deterministic
  controls showed exact-marker scoring is lexical: exact marker passed,
  semantic-equivalent loss declaration failed exact scoring, and an exact marker
  without a constrained recommendation was not materially disciplined. Live
  direct-DeepSeek rows showed the model can comply when the exact marker is
  explicit. Moved current priority to harder append-only baseline.
- 2026-06-18: Completed harder append-only baseline test. The symbolic
  event-loop condition survived against the stronger one-shot append-only
  baseline with equal perfect artifact quality and declared-loss scores. Moved
  current priority to longer-horizon sustained loop because it should provide
  more information than another single-artifact comparison.
- 2026-06-18: Completed longer-horizon sustained loop test. The live direct
  DeepSeek run passed with seven completed events, two inbound tasks, two
  continuations, two housekeeping events, one final synthesis artifact, and
  eight restart-frontier commits. Moved current priority to multi-entity event
  loop.
- 2026-06-18: Ran the live multi-entity event loop test. Scheduler execution
  completed, terminal surfaces matched the preregistered sequence, explicit
  entity/workstream identity was preserved, and restart-frontier evidence was
  written. The run failed because the global wake state carried red fields into
  the blue prior state; blue then produced a cross-entity continuation note,
  and both audit and final artifact marked contamination/attribution errors.
  Kept the roadmap on multi-entity work, narrowed to entity-scoped state
  isolation repair before restart/resume.
- 2026-06-18: Completed the multi-entity state isolation repair probe. The live
  direct DeepSeek run passed after the experiment layer restored per-entity wake
  state before each entity event. Entity-event prior states contained no
  foreign-entity mentions, the audit and final artifact reported no
  contamination or attribution errors, and the run had no failure attribution
  records. Moved current priority to restart/resume under interruption.
- 2026-06-18: Completed the restart/resume interruption probe. The live direct
  DeepSeek run passed with an intentionally interrupted claimed housekeeping
  event recovered from `running` back to `pending`, then completed by a resumed
  session. The interrupted event lifecycle was `pending`, `running`, `pending`,
  `running`, `completed`; no events were suppressed and no failure attribution
  records were produced. Moved current priority to provider variance.
- 2026-06-18: Completed the provider variance panel. The committed direct
  DeepSeek restart/resume result and the new OpenRouter DeepSeek row both
  passed the same restart/resume protocol with terminal tool choice `auto`.
  Panel conclusion: `no_provider_variance_detected_on_panel`. Marked this
  roadmap complete.

## Update Discipline

When the roadmap changes, update this file with:

- the new ordering;
- the rationale for the change;
- the evidence that caused the change;
- whether the change affects the roadmap goal, the next execution goal, or both.
