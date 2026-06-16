# Event-Loop Viability + Append-Only Non-Inferiority Preregistration

Experiment ID: `event_loop_viability_append_only_noninferiority_20260614`

Date: 2026-06-14

## Research Question

Can the event-driven scheduling loop support bounded model work as a viable
execution substrate, and, conditional on that substrate being viable, is the
`taste` / `taste_open` event-loop form non-inferior to the existing
append-only context baseline on the surfaces both systems can fairly provide?

This protocol separates two claims that prior panels can blur:

1. shared-surface non-inferiority: whether event-loop rows are non-inferior to
   append-only rows on artifact quality and common trace observability;
2. scheduler added value: whether event-loop rows produce scheduler and
   reconstruction evidence that append-only rows do not attempt to provide.

Scheduler viability and scheduler reconstruction are gates, not
artifact-quality score components.

## Conditions

Each matched task is run in two conditions:

- `event_loop_scheduled`: a two-cycle event-loop row. Cycle 1 records a
  scheduled work item, selected context, declared losses, and a restart
  frontier. Cycle 2 consumes the scheduled wake context and writes the final
  artifact.
- `append_only`: a one-cycle append-only baseline row. The model receives the
  task and the full bounded corpus in a single context and writes the final
  artifact.

Version 1 of the harness is deterministic and dry-run only. It establishes the
row shape, scoring rules, and artifact trail before any live provider calls are
introduced.

## Matched Tasks

The first panel uses two small evidence-bound tasks:

1. `scheduler_boundary_note`: decide whether scheduling-loop evidence supports
   moving to a non-inferiority comparison.
2. `append_only_comparison_note`: decide what must be true before claiming
   non-inferiority to the append-only baseline.

Each task includes required fact IDs, expected evidence record IDs, one
declared-loss marker, and one distractor record.

## Gate A: Shared-Surface Non-Inferiority

The fair head-to-head comparison uses only axes both conditions can provide.

Shared artifact-quality axes:

- schema validity;
- required fact recovery;
- evidence citation correctness;
- declared-loss discipline;
- contamination avoidance;
- conclusion/actionability;
- unsupported-claim rate.

Shared trace-observability axes:

- raw request and response preservation;
- parsed artifact preservation;
- deterministic artifact score preservation;
- failure-attribution surface.

The event-loop condition passes Gate A only if:

- mean artifact quality is at least append-only mean minus `0.10`;
- no event-loop row has catastrophic artifact failure;
- unsupported-claim rate is not worse than append-only;
- shared trace observability is at least append-only shared trace observability
  minus `0.10`.

## Gate B: Scheduler Added Value

The event loop is viable for this protocol only if every `event_loop_scheduled`
row proves all of the following from persisted row artifacts:

- the scheduled event is recorded durably;
- the event status sequence is `scheduled -> claimed -> completed`;
- wake context contains the task ID and scheduled event ID;
- the schedule record links back to the producing cycle;
- selected context and declared losses are preserved before artifact writing;
- a restart frontier is written and reconstructable;
- raw request, raw response, parsed output, and deterministic scores are
  preserved;
- scheduler failures can be attributed separately from model, provider,
  harness, substrate, and scorer failures.

Failure of this gate classifies the run as scheduler/reconstruction failure even
if artifact quality is high. Append-only rows are marked `not_applicable` for
these scheduler-specific axes rather than penalized.

## Artifact-Quality Rubric

Artifact quality is scored on `[0, 1]` using a deterministic rubric:

- schema validity: `0.10`;
- required fact recovery: `0.35`;
- evidence citation correctness: `0.20`;
- declared-loss discipline: `0.15`;
- contamination avoidance: `0.10`;
- conclusion/actionability: `0.10`.

The event-loop condition is artifact-quality non-inferior to append-only if:

- mean event-loop artifact quality is at least append-only mean minus `0.10`;
- no event-loop row has catastrophic artifact failure;
- unsupported-claim rate is not worse than append-only.

Catastrophic artifact failure means unscoreable JSON, recovery rate below
`0.60`, contamination rate above `0.50`, or unsupported-claim rate above
`0.25`.

## Observability Reporting

The protocol reports two observability scores:

- `shared_surface_observability`: a fair head-to-head score over raw
  request/response, parsed artifact, deterministic score, and
  failure-attribution surface.
- `scheduler_reconstruction_observability`: an event-loop-only added-value
  score over cycle boundary, scheduled event lifecycle, wake context, restart
  frontier, context selection, and declared-loss trace.

The aggregate `event_loop_mean_observability - append_only_mean_observability`
is not used, because it would penalize append-only for lacking scheduler
machinery it does not claim to provide.

## Classification

The run is `survived` only if:

- Gate A shared-surface non-inferiority passes;
- Gate B scheduler added-value passes.

The run is `falsified` if either shared-surface non-inferiority or scheduler
added value fails under the deterministic harness.

The run is `inconclusive` only when a fair comparison cannot be made because of
provider, transport, harness, substrate, scorer, or protocol failure. The dry
v1 harness should not normally produce `inconclusive`; that classification is
reserved for future live-provider extensions.

## Expected Result

Expected dry v1 harness result: `survived`.

This is not a substantive live-model result. It is a readiness artifact proving
that the protocol can run matched append-only and event-loop rows while keeping
scheduler viability separate from model artifact quality.

Expected live-model result: likely falsified or narrowed on at least one
shared-surface axis. The `taste` / `taste_open` instances inside the event loop
have not yet been tuned for this comparison, and non-inferiority should
reasonably be expected to require tuning. A live failure on one shared axis
would therefore be informative rather than surprising.
