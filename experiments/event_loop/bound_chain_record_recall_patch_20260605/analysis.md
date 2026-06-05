# Bound Chain After In-Session Record-ID Recall Patch Analysis

Date: 2026-06-05

## Result

The in-session `record_id` recall patch changed the bound-chain result from a
clean addressing failure to a partial success with a new observability/data
cleanliness confound.

| Rows | First wake valid | Bound second event | Bound record delivered | Second wake valid | Final recovered | Record-ID context errors |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 | 1 | 1 | 1 | 1 | 0 |

Focused tests before the live run:

```text
79 passed
```

Hypothesis status from `results.json`:

- H311 bound record-ID recall resolves: supported in 1/2 rows.
- H312 final recovery with bound intermediate: supported in 1/2 rows.
- H313 first-wake contract preserved: partially supported; 1/2 rows valid.
- H314 unknown/cross-session fallback preserved: supported by focused tests.
- H315 provenance distinguishable: supported.

## Before/After

Previous `bound_chain_contract_20260605` result:

- first wake valid: 2/2;
- bound second event appended: 2/2;
- bound record-ID context requested: 2/2;
- bound record-ID context delivered: 0/2;
- explicit error: `record_id mode requires a bridge (persistence backend)`.

Patched rerun:

- first wake valid: 1/2;
- bound second event appended: 1/2;
- bound record-ID context requested: 1/1 due-executed second wake;
- bound record-ID context delivered: 1/1;
- explicit bridge error: 0.

The substrate patch therefore fixed the specific record-ID delivery failure for
in-session records.

## Replicate Outcomes

Replicate 1 failed at first wake before continuation binding:

- event status: failed;
- failure: `deleted_regions` overlapped updates for `declared_losses`;
- no bound second event was appended.

This is a known structured-object failure mode: the model tried to delete and
update the same top-level key in one cycle.

Replicate 2 completed the full chain:

- first wake valid;
- continuation request present;
- bound second event appended with first wake `result_record_id`;
- second wake received cycle-1 recall and bound record-ID recall;
- bound record-ID recall returned in-session content;
- final answer recovered `violet-harbor-42`;
- final evidence referenced `word-word-number` and the bound first-wake record
  ID.

## New Confound

The successful bound record included `_activity_log` content from the first
wake. The first wake called `bash` to verify the digest:

```text
echo -n "violet-harbor-42" | sha256sum
```

The validator intentionally excluded `_activity_log` from durable state leakage
checks because it is framework-authored activity metadata, not model-owned
identity state. However, `recall(record_id=...)` returned the full record
content, including `_activity_log`. That means the bound record recall was not
clean with respect to exact-phrase exposure.

The final answer also had cycle-1 recall, so phrase recovery did not depend
solely on this activity-log leakage. Still, the leakage matters for any future
experiment that treats bound record recall as a non-secret intermediate.

## Interpretation

The patch succeeded at the substrate level: in-session record-ID recall can now
resolve a newly produced wake record without requiring a persistence bridge.

It also exposed the next design requirement: record-ID recall needs a scoped or
filtered mode for event-bound continuation. Returning framework activity logs
can reintroduce data the model intentionally omitted from model-owned durable
state.

This turns the next question from "can we bind by record ID?" into "what exactly
should a bound continuation recall expose?"

## Next Research Question

The next useful slice is a filtered bound-record recall test.

Possible approaches:

- request `record_id` recall with `field="chain_intermediate"` for the bound
  first-wake record;
- or change event-bound recall to exclude `_activity_log` by default;
- or add an explicit `content_scope`/`include_activity_log` option later.

The narrowest falsification experiment is to rerun the bound-chain contract
with the second event requesting:

```json
{"tool": "recall", "record_id": "<first_wake_result_record_id>", "field": "chain_intermediate"}
```

That would test whether in-session record-ID recall can deliver just the
non-secret intermediate and avoid framework-log leakage.
