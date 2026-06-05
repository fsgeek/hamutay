# Identity Merge Replay Analysis

Filed: 2026-06-05 after the registered capture panel completed.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- runner: `run_merge_replay.py`
- raw logs: `mistralai__mistral-small-2603_claim_table_guardrail_delta_900_r*.jsonl`
- scored results: `results.json`

## Validation

- `uv run python -m py_compile experiments/identity_merge_replay_20260605/run_merge_replay.py`: pass
- `uv run python experiments/identity_merge_replay_20260605/run_merge_replay.py --help`: pass
- `uv run python experiments/identity_merge_replay_20260605/run_merge_replay.py --rescore`: pass, 6 logs rescored
- `jq empty experiments/identity_merge_replay_20260605/results.json`: pass
- `git diff --check -- experiments/identity_merge_replay_20260605/run_merge_replay.py`: pass

## Registered Panel

Model:

- `mistralai/mistral-small-2603`

Condition:

- `claim_table_guardrail_delta_900`

Replicates:

- 6 registered slots
- 5 completed
- 1 strict merge failure captured
- 0 censored provider/rate/length failures

## Summary Results

| measure | value |
| --- | ---: |
| total runs | 6 |
| completed runs | 5 |
| errors | 1 |
| captured `state_merge` failure records | 1 |
| captured overlap keys | 1 |
| central overlap keys | 1 |
| overlap keys with revision language in state update | 0 |

Captured overlap key counts:

| key | count |
| --- | ---: |
| `assumptions` | 1 |

Replay outcome:

| policy | retained overlap keys | dropped overlap keys | produces normalized state |
| --- | ---: | ---: | --- |
| `strict_reject` | 0 | 1 | no |
| `update_wins` | 1 | 0 | yes |
| `delete_wins` | 0 | 1 | yes |
| `delete_then_update` | 1 | 0 | yes |

`update_wins` and `delete_then_update` produced identical replay states for
the captured failure.

## Captured Failure Shape

The single captured failure occurred at cycle 3 in replicate 3:

- overlap key: `assumptions`
- `deleted_regions`: `["assumptions"]`
- raw state update for `assumptions`: `[]`
- prior `assumptions`: six initial planning assumptions
- visible response: included a substantive "Invalidated Assumptions" section
  naming local-storage and East Clinic assumptions as invalidated.

This is important. The model did not encode the substantive invalidation in
the state field that overlapped. It encoded the invalidation in visible prose
and represented the state-field replacement as an empty list.

## Hypothesis Assessment

### H52: Strict Capture Produces Replayable Merge Failures

Supported.

The panel produced one captured `state_merge` failure record with raw output,
prior state, usage, failure classification, and overlap keys preserved.

### H53: Update-Wins Preserves More Authored Structure Than Delete-Wins

Mechanically supported, semantically weak.

`update_wins` retained the overlap key and `delete_wins` dropped it. However,
the retained value was an empty list, so the structural win did not preserve
the actual invalidation content. The useful revision information was in the
visible response, not the overlapping state field.

### H54: Delete-Then-Update Is an Alias of Update-Wins for Top-Level Fields

Supported.

For the captured top-level overlap, `delete_then_update` and `update_wins`
produced identical replay states.

### H55: Replay Data Is Not Enough To Pick A Live Policy

Supported.

Replay identified the structural consequences of each policy, but it did not
settle live semantics. In this captured failure, update-wins would preserve an
empty `assumptions` field while delete-wins would remove it. Neither policy
captures the substantive invalidation text that the model placed in the
visible response.

## Interpretation

The capture-and-replay path works, but this first payload argues against a
simple live normalizer.

The prior intuition was that overlap might mean "replace this field." This
case is close to that mechanically, but not semantically: the replacement value
is empty and the actual revision lives in prose. Accepting update-wins would
avoid losing the run, but it would not necessarily improve the durable
identity object. Accepting delete-wins would also lose the prior assumptions
and provide no structured invalidation trail.

This points to a different substrate need: when merge fails, the framework
should preserve the failed raw output and perhaps later support an explicit
repair/replay workflow, but live automatic normalization is still not
justified.

## Limitations

- Only one captured failure in this panel.
- The panel used one model and one condition.
- Replay did not continue the session from normalized candidate states.
- Risk scoring was structural and heuristic.

## Design Implications

1. The failure-capture instrumentation is useful and should stay.

2. Top-level `delete_then_update` should be treated as an alias of
   `update_wins`; future live-policy discussions should not treat them as
   independent alternatives unless sub-field deletion semantics are added.

3. A live normalizer should not be introduced yet. The first captured payload
   shows that preserving the overlapping field can still miss the revision
   semantics.

4. The next substrate step should be a replay/repair design rather than silent
   normalization: use captured raw output, visible response, prior state, and a
   repair policy to produce an explicit `protocol_recovery` artifact.

## Next Research Move

The next useful experiment is not another live Mistral panel. It is a
deterministic repair-spec slice:

> Can a merge-failure repair artifact recover structured invalidation content
> from the failed raw output and visible response without mutating live state?

That would test whether failed cycles can become analyzable repair candidates
before any normalized state is accepted into the working identity object.
