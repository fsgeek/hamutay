# Two-Wake Chain Analysis

Date: 2026-06-05

## Result

Both two-wake chain replicates completed.

| Rows | First wake complete | First wake valid | First wake state leaks | Second event scheduled | Second wake complete | Both contexts delivered | Final recovered | Intermediate used |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 2 | 2 | 0 | 2 | 2 | 2 | 2 | 2 |

Hypothesis status from `results.json`:

- H296 two-wake chain completes: supported.
- H297 first wake keeps phrase out of durable state: supported.
- H298 second wake receives both contexts: supported.
- H299 second wake recovers and uses intermediate: supported.
- H300 provenance distinguishable: supported.

## Event Chain

The runner seeded cycle 1 and cycle 2, then appended the first pending event
directly. The model scheduled the second event during the first wake.

Both event logs had the intended lifecycle:

1. pending first event, scheduled by cycle 2, requested `recall(cycle=1)`;
2. completed first event at wake cycle 3;
3. pending second event, scheduled by cycle 3, requested `recall(cycle=1)` and
   `recall(cycle=3)`;
4. completed second event at wake cycle 4.

There were no bounded-call violations and no row-level errors.

## First Wake

Both first wakes were valid on first pass.

Each first wake:

- received cycle-1 recall context;
- set `thinking_status` to `awaiting_second_wake`;
- set `chain_stage` to `first_wake_complete`;
- wrote `chain_intermediate` with:
  - `source_cycle: 1`;
  - `phrase_shape: word-word-number`;
  - `part_count: 3`;
  - `exact_phrase_retained: false`;
- did not include the exact phrase in durable state;
- scheduled the second event with the requested cycle-1 and cycle-3 context.

Neither first-wake response text contained the exact phrase.

## Second Wake

Both second wakes received both requested contexts: cycle 1 and cycle 3.

Both final states:

- set `thinking_status` to `chain_completed`;
- set `chain_stage` to `second_wake_complete`;
- recovered the exact phrase in `chain_final_answer`;
- referenced the first-wake intermediate shape `word-word-number` in
  `chain_final_evidence`.

Replicate 1 required second-wake repair; replicate 2 was valid on first pass.
The repair prompt did not reveal the exact phrase.

Final answers:

- replicate 1: `amber-lattice-17`;
- replicate 2: `violet-harbor-42`.

## Interpretation

This is the first positive map point for chained event-loop continuity in this
research arm. It shows that the scaffold can support more than a single delayed
recall:

- a first wake can consume exact recall and preserve only a non-secret
  intermediate;
- that first wake can schedule a second event;
- the second event can recall both the original seed and the first wake state;
- the final wake can combine those contexts into a validated final state.

This was deliberately isolated from compression mechanics by seeding a clean
cycle-2 state. That was the right boundary for this test: compression and repair
had already been shown to be workable enough in the prior panel, and this probe
asked whether the event substrate itself could chain.

## Remaining Cautions

The panel is small and uses one model. It is evidence of feasibility, not broad
reliability.

The chain still depends on known cycle addressing. The model scheduled the
second event with `recall(cycle=3)` because the runner made the chain
deterministic. A more general event loop will need a better way for an instance
to refer to "the state I am about to produce" or for the substrate to bind a
future event to the current wake's eventual record ID.

Second-wake repair remains a confound in one replicate. The repair was
non-leaking and final validation succeeded, but future chain experiments should
continue reporting first-pass and repair provenance separately.

## Next Research Question

The next scheduler question is about addressing, not recall itself:

Can the scaffold support self-reference for newly produced wake states without
requiring the model to guess a future cycle number?

A concrete next slice would test a substrate-bound continuation event:

- first wake produces a non-secret intermediate and asks for a second wake;
- instead of the model specifying `recall(cycle=3)`, the runner/substrate binds
  the second event to the first wake's completed `result_record_id`;
- second wake requests recall by that bound `record_id` plus cycle 1.

That would attack the main artificiality in this successful two-wake chain.
