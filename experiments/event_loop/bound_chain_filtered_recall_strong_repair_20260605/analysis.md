# Filtered Bound Recall With Strong First-Wake Repair Analysis

Date: 2026-06-05

## Result

The filtered bound-record recall path worked. Both rows delivered only
`chain_intermediate` from the bound first-wake record, without `_activity_log`
or exact-phrase leakage. One of two rows completed the final second-wake task.

| Rows | First wake valid | Filtered context delivered | Activity-log leaks | Phrase leaks | Second wake valid | Final recovered |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 2 | 2 | 0 | 0 | 1 | 1 |

Hypothesis status from `results.json`:

- H326 first wake validates with strong repair: supported.
- H327 filtered bound context resolves: supported.
- H328 filtered context has no phrase/activity-log leakage: supported.
- H329 final recovery with filtered intermediate: supported in 1/2 rows.
- H330 provenance visible: supported.

## Filtered Context

Both second events requested:

```json
{"tool": "recall", "record_id": "<first_wake_result_record_id>", "field": "chain_intermediate"}
```

Both bound context results delivered successfully.

Replicate 1 bound content:

```json
{
  "source_cycle": 1,
  "phrase_shape": "word-word-number",
  "part_count": 3,
  "exact_phrase_retained": false,
  "word_lengths": [5, 7, 2],
  "separator": "-"
}
```

Replicate 2 bound content:

```json
{
  "source_cycle": 1,
  "phrase_shape": "word-word-number",
  "part_count": 3,
  "exact_phrase_retained": false
}
```

Neither filtered context contained `_activity_log`. Neither contained the exact
phrase.

## First Wake

Both first wakes validated and requested continuation.

Both were valid on first pass in this two-row panel, so the strong repair
builder was not exercised here. This does not contradict the stability panel:
the stability panel showed repair is available when the first pass misses the
object shape.

## Second Wake

Replicate 1 succeeded after second-wake repair:

- recovered `amber-lattice-17`;
- used the filtered intermediate;
- recorded `phrase_shape: word-word-number`;
- referenced the bound first-wake record ID;
- final state valid.

Replicate 2 received both contexts but failed second-wake repair:

- final state remained at the first-wake stage;
- `chain_final_answer` was missing;
- `chain_final_evidence` was missing;
- `bound_record_id_used` was missing;
- `chain_intermediate` was deleted during the failed second wake.

This makes the remaining limitation second-wake integration/repair, not
filtered record recall delivery.

## Interpretation

This panel closes the activity-log leakage confound for this chain shape.
Field-filtered in-session record-ID recall can deliver the intended non-secret
intermediate without exposing framework activity logs.

The event-loop substrate now has a feasible path for bound continuation:

1. first wake emits a non-secret intermediate and continuation request;
2. substrate binds the second event to the first wake's `result_record_id`;
3. second event requests the bound record by `record_id` and `field`;
4. the wake receives only the requested non-secret field.

The remaining failure mode is downstream: the second wake may still fail to
integrate the delivered contexts into the required durable final object.

## Next Research Question

The next useful slice is second-wake integration stability with filtered bound
context.

A focused panel should:

- seed or force valid first-wake states, or reuse the now-working first-wake
  contract path;
- deliver cycle-1 recall plus filtered `chain_intermediate`;
- strengthen the second-wake repair prompt with a full expected durable object
  shape;
- score second-wake first-pass valid, repair valid, final recovery, and
  intermediate use.

If that stabilizes, the event-loop scaffold has a credible minimal continuation
substrate. If not, the second wake likely needs a structured completion tool or
validator-side object repair.
