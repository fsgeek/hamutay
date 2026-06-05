# Compression Repair Gate Analysis

Date: 2026-06-05

## Result

The compression repair gate produced a cleaner and more informative panel than
the prior seeded run.

| Condition | Rows | First-pass clean | Repair attempted | Repair successful | Final clean | Due executed | Fact recovered | Final valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `identity_only_compression_repair_gate` | 2 | 0 | 2 | 1 | 1 | 1 | 0 | 0 |
| `event_plus_recall_compression_repair_gate` | 2 | 2 | 0 | 0 | 2 | 2 | 2 | 2 |

Hypothesis status from `results.json`:

- H291 repair makes clean row: supported.
- H292 secret rows culled/not repaired: supported; no secret-bearing rows
  occurred.
- H293 still-invalid rows culled: supported.
- H294 clean event recall recovers: supported.
- H295 provenance distinguishable: supported.

## Compression Findings

The event-plus-recall arm was clean on first pass in both replicates:

- `thinking_status` was `scheduled`;
- durable `declared_losses` was present;
- `memory_handle.code_phrase_sha256` was preserved;
- `loss_template` was preserved;
- no exact phrase appeared in cycle-2 durable state;
- scheduling was valid in both rows.

The identity-only arm failed first-pass compression in both replicates for the
same structural reasons:

- `thinking_status_not_expected`;
- `declared_losses_missing`.

Compression repair converted identity replicate 1 into a clean parked state.
Identity replicate 2 repeated the same structural failure after repair and was
culled before due execution.

No row had exact phrase leakage or retained top-level `deferred_fact`, so the
secret-bearing cull path was not exercised in this panel.

## Due-Step Findings

Both event-plus-recall rows proceeded to due execution, received recall context,
and recovered the exact phrase:

- replicate 1 recovered `amber-lattice-17` with first-pass due validation valid;
- replicate 2 recovered `violet-harbor-42` after due-state repair.

The repaired identity row proceeded to due execution at cycle 4. It did not
recover the exact phrase and instead declared that the digest alone was
insufficient to reconstruct it. That is the desired behavioral distinction for
this task: clean compression without recall did not produce recovery.

## Interpretation

This result separates three things that were previously tangled:

1. Clean compression is achievable under the seeded scaffold.
2. Some dirty compression rows are repairable without leaking the phrase.
3. Recovery still depends on recall, not merely on having a digest or repaired
   structural state.

The repair gate is therefore a useful part of the event-loop scaffold. It
improves operational yield while preserving the important invariant: no due
execution from dirty or secret-bearing compression.

The event-plus-recall arm now has a stronger map point than the earlier
compressed delayed-task panel. In this panel, both event rows were clean before
due execution and both recovered after recall. The identity arm gives the
negative control: one clean identity row ran due and did not recover.

## Remaining Cautions

This is still a tiny panel with one model and two replicates per arm. It is not
evidence of broad model reliability. It is evidence that, for this model and
scaffold, the combination of seeded handle/template plus prospective validation
plus non-leaking compression repair can produce clean event-loop continuity.

Due-state repair remains a separate confound. One event row recovered only
after due repair, though the repair prompt did not reveal the phrase. Future
analysis should continue to separate compression repair from due repair.

## Next Research Question

The next question can move back from boundary mechanics toward scheduler
design:

Can the scaffold treat clean compression plus repair as a normal event-loop
phase, then execute a multi-event chain where each event carries only handles
and requested recall context rather than full task facts?

A useful next experiment would schedule two dependent delayed tasks:

1. first event recalls cycle 1 and records a non-secret derived result;
2. second event wakes later, recalls the first event result and original seed,
   and completes a combined answer.

That would test whether the event-loop substrate supports continuity across
more than one wake, not merely a single delayed recall.
