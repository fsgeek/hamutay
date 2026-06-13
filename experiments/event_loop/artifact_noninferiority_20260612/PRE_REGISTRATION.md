# Goal 10 Pre-Registration: Artifact Non-Inferiority Panel

Date: 2026-06-13

## Research Question

Can event-loop bounded work produce artifacts that are non-inferior to direct
one-shot work while preserving stronger observability and reconstruction?

## Hypothesis

H10: On small matched evidence-bound tasks, the event-loop bounded-work
condition will be artifact-quality non-inferior to a direct one-shot condition
within a preregistered margin, and will provide stronger deterministic
observability.

## Matched Conditions

Each task is run in two conditions:

- `event_loop_bounded`: two-cycle event-loop form. Cycle 1 selects a bounded
  work plan and requested evidence. The harness resolves requested evidence
  from a bounded local corpus. Cycle 2 writes the artifact from the selected
  evidence and carried state.
- `direct_one_shot`: one provider call. The model receives the same task and
  full bounded corpus in one prompt and writes the artifact.

The same model, temperature, JSON mode, and task corpus are used for both
conditions.

## Tasks

The panel has three matched tasks:

1. `scheduler_migration_note`: decide whether the current scheduler evidence is
   sufficient to proceed to artifact non-inferiority work.
2. `failure_attribution_note`: classify a failed autonomy row by failure layer
   without hiding scorer/harness faults.
3. `memory_boundary_note`: decide whether memory access alone solves
   working-set management.

Each task has required fact IDs, expected evidence record IDs, declared-loss
markers, and one distractor record. The scorer must evaluate the artifact
against these task-specific requirements, not against prose fluency alone.

## Non-Inferiority Margin

Artifact quality is scored on `[0, 1]`.

Event-loop bounded work is artifact-quality non-inferior if:

- mean event-loop artifact quality is at least direct mean minus `0.10`; and
- no event-loop artifact has a catastrophic failure:
  - unscoreable JSON;
  - recovery rate below `0.60`;
  - contamination rate above `0.50`.

If provider, transport, protocol, harness, or scorer failures prevent a fair
comparison, the result is `inconclusive`, not failed.

## Artifact-Quality Judging

Artifact quality is judged deterministically using a preregistered rubric:

- schema validity: `0.10`;
- required fact recovery: `0.40`;
- evidence citation correctness: `0.20`;
- declared-loss discipline: `0.15`;
- contamination avoidance: `0.10`;
- conclusion/actionability: `0.05`.

The judge is intentionally deterministic and inspectable. It is not a broad
human-preference judge.

## Deterministic Observability Scoring

Observability is scored separately on `[0, 1]`:

- raw request and response preserved: `0.15`;
- parsed action/artifact preserved: `0.15`;
- cycle boundary visible: `0.15`;
- evidence request and recall provenance visible: `0.20`;
- deterministic artifact score preserved: `0.15`;
- failure attribution surface present: `0.10`;
- restart/reconstruction proxy present: `0.10`.

Direct one-shot rows can score observability points for preserved requests,
responses, parsed artifacts, and deterministic scoring, but should not receive
event-loop-only provenance points unless the trace actually contains them.

## Judge/Scorer Disagreement

The panel records two deterministic views:

- artifact-quality judge score;
- trace/observability score.

A disagreement is recorded when artifact quality and observability differ by at
least `0.25` in either direction. Disagreements are method findings, not hidden
errors.

## Falsification Conditions

H10 is falsified if:

- event-loop bounded work is inferior by more than the margin; or
- any event-loop row has a catastrophic artifact failure; or
- event-loop observability is not stronger than direct one-shot observability.

H10 survives if artifact quality is non-inferior and event-loop observability is
stronger.

The result is inconclusive if a fair comparison cannot be made due to provider,
protocol/transport, harness, substrate, or scorer failure.

## Expected Result

Expected result: inconclusive or survived.

The prior Goal 8 result showed that model-managed working-set behavior can
recover evidence but still contaminate an artifact. This panel therefore does
not expect clear artifact superiority. It expects either artifact
non-inferiority with stronger observability, or a sharper failure mode showing
where the event-loop form still loses artifact quality.
