# Identity Merge Repair Artifact Analysis

Filed: 2026-06-05 after the deterministic repair extractor completed.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- runner: `run_merge_repair.py`
- output: `repair_results.json`
- input corpus: captured `state_merge` failures from
  `experiments/identity_merge_replay_20260605/*.jsonl`

## Validation

- `uv run python -m py_compile experiments/identity_merge_repair_artifact_20260605/run_merge_repair.py`: pass
- `uv run python experiments/identity_merge_repair_artifact_20260605/run_merge_repair.py`: pass
- `jq empty experiments/identity_merge_repair_artifact_20260605/repair_results.json`: pass
- `git diff --check -- experiments/identity_merge_repair_artifact_20260605/run_merge_repair.py`: pass

## Summary Results

| measure | value |
| --- | ---: |
| failure records processed | 1 |
| candidate continuity rows | 13 |
| candidate invalidated-assumption rows | 2 |
| candidate constraint rows | 3 |
| candidate goal rows | 3 |
| candidate next-action rows | 5 |
| contamination warnings | 4 |
| accepted states produced | 0 |

All extracted rows were marked `candidate` and `accepted: false`.

The artifact kept `live_policy: "strict_reject"` and `accepted_state: null`.

## Recovered Candidate Content

The extractor recovered two invalidated assumptions from the failed visible
response:

- encrypted local storage had been assumed permissible and was invalidated by
  the privacy officer ruling;
- East Clinic participation had been assumed and was invalidated by the site
  withdrawal.

It also recovered candidate constraints:

- no local document storage;
- East Clinic replaced by West Shelter;
- prior constraints still active.

## Contamination Warnings

The extractor flagged four unsupported budget/cost details:

- `New expected cost: ... $1,900 for hardware`;
- `Cellular plans remain unchanged ... $30/mo/site`;
- hotspot purchase at `$200/site`;
- budget reserve of `$1,900`, prior `$2,850`, and `~$16.1k contingency`.

This matters because the same failed response contains both useful continuity
content and unsupported specificity. The repair artifact preserves both
signals without admitting either into state.

## Hypothesis Assessment

### H56: Failed Responses Can Yield Candidate Continuity Rows

Supported.

The captured failed response yielded 2 invalidated-assumption rows and 3
constraint rows, exceeding the registered threshold.

### H57: Repair Artifacts Can Preserve Contamination Warnings

Supported.

The extractor flagged 4 budget/cost warning rows from unsupported specificity
in the failed response.

### H58: Repair Artifacts Do Not Produce Accepted State

Supported.

The output produced no accepted state, kept strict live policy, and marked all
extracted rows as candidates.

## Interpretation

This is a useful substrate result.

The failed cycle should not be silently normalized, but it also should not be
discarded. The repair artifact shows a middle path: preserve candidate
continuity facts, preserve contamination warnings, keep strict rejection, and
defer adjudication.

The key design implication is that merge failure can become productive
observability data. A failed cycle can now produce a reviewable
`protocol_recovery` artifact rather than a lost exception or an implicitly
accepted normalized state.

## Limitations

- One captured failure record.
- Deterministic section parsing assumes visible headings.
- Candidate rows are not truth judgments.
- The extractor does not yet integrate with live session logs as a first-class
  curation artifact.

## Design Implications

1. The event-loop substrate should include a protocol-recovery side channel.

2. Merge repair should be staged:
   - capture failed raw output;
   - build candidate repair artifact;
   - adjudicate candidates;
   - only then decide whether anything enters working state.

3. Repair artifacts should include contamination warnings alongside recovered
   continuity candidates.

4. This is a better next step than live update-wins normalization. It preserves
   evidence without making premature state commitments.

## Next Research Move

The next implementation move should integrate protocol-recovery artifact
creation into `OpenTasteSession` as an optional hook, analogous to the
continuity curator hook, but invoked only after strict merge failure capture.

The next falsification question:

> Can protocol-recovery artifacts reduce lost continuity after failed cycles
> while keeping failed-cycle content out of accepted state?

That should be tested with deterministic fake backends first, then with a
small live panel only after the side-channel contract is stable.
