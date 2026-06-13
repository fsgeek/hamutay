# Goal 10 Analysis: Artifact Non-Inferiority Panel

Date: 2026-06-13

## Result

Classification: `survived`

Under the preregistered deterministic rubric, event-loop bounded work was
artifact-quality non-inferior to direct one-shot work and had stronger
observability.

| Condition | Mean Artifact Quality | Mean Observability | Catastrophic Failures | Judge/Scorer Disagreements |
| --- | ---: | ---: | ---: | ---: |
| event_loop_bounded | 0.9000 | 1.0000 | 0 | 0 |
| direct_one_shot | 0.9000 | 0.5500 | 0 | 3 |

Artifact-quality delta, event minus direct: `0.0000`

Preregistered non-inferiority margin: `0.1000`

Observability delta, event minus direct: `0.4500`

## Row-Level Summary

| Task | Condition | Artifact Quality | Recovery | Contamination | Observability |
| --- | --- | ---: | ---: | ---: | ---: |
| scheduler_migration_note | event_loop_bounded | 1.0000 | 1.0000 | 0.0000 | 1.0000 |
| scheduler_migration_note | direct_one_shot | 1.0000 | 1.0000 | 0.0000 | 0.5500 |
| failure_attribution_note | event_loop_bounded | 0.8500 | 1.0000 | 0.0000 | 1.0000 |
| failure_attribution_note | direct_one_shot | 0.8500 | 1.0000 | 0.0000 | 0.5500 |
| memory_boundary_note | event_loop_bounded | 0.8500 | 1.0000 | 0.0000 | 1.0000 |
| memory_boundary_note | direct_one_shot | 0.8500 | 1.0000 | 0.0000 | 0.5500 |

Both conditions recovered all required facts and avoided distractor
contamination. The two lower-quality tasks lost points for declared-loss
discipline, not factual recovery.

## Judge/Scorer Disagreements

The preregistered disagreement rule flagged all three direct one-shot rows:
artifact quality exceeded trace observability by at least `0.25`.

This is not treated as a direct-row failure. It is a method finding: the direct
condition produced useful artifacts, but the trace had weaker reconstruction
surface because it lacked model-authored cycle boundaries, evidence-request
classification, recall provenance, and a restart/reconstruction proxy.

No event-loop rows crossed the disagreement threshold.

## Token Use

The event-loop condition used more tokens than direct one-shot in this panel.

| Task | Condition | Prompt Tokens | Completion Tokens |
| --- | --- | ---: | ---: |
| scheduler_migration_note | event_loop_bounded | 2424 | 3366 |
| scheduler_migration_note | direct_one_shot | 690 | 1678 |
| failure_attribution_note | event_loop_bounded | 2035 | 2264 |
| failure_attribution_note | direct_one_shot | 698 | 1928 |
| memory_boundary_note | event_loop_bounded | 2027 | 2718 |
| memory_boundary_note | direct_one_shot | 679 | 1616 |

This panel therefore does not show efficiency superiority. It shows
artifact-quality non-inferiority plus stronger observability on small bounded
tasks. Efficiency remains a separate research question.

## Interpretation

Goal 10 supports the narrow H10 claim:

- event-loop bounded work can be artifact-quality non-inferior to direct
  one-shot work on these matched bounded tasks;
- event-loop bounded work can provide stronger deterministic observability;
- the observability gain is separable from artifact quality.

The result does not prove broad model capability, artifact superiority,
working-set efficiency, or production readiness. It is a systems result about a
bounded harness shape: when the task is small enough for both conditions to
recover the evidence, the event-loop form can retain artifact quality while
making the process more reconstructable.

## Method Notes

The panel used a deterministic judge rather than an LLM judge. That was a
deliberate choice to avoid introducing a second model confound at this stage.
The review packet preserves condition-hidden artifacts for later blinded review
if we decide the deterministic rubric is too narrow.

The live runner exposed and repaired one harness issue before final commit:
`--overwrite` originally removed the experiment directory, including
`PRE_REGISTRATION.md` and `run.py`, when the output root was the experiment
directory itself. The committed runner now clears only generated artifacts
(`results.json`, `rows/`, `review_packet/`, and `analysis.md`), and a regression
test preserves this invariant.

## Next Research Implication

The next question is not whether event-loop bounded work can ever produce a
useful artifact; this panel shows that it can under a small matched task shape.
The sharper question is when the extra observability is worth the extra token
cost, and whether larger or more failure-prone tasks preserve non-inferiority.
