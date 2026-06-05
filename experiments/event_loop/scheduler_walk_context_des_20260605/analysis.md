# Scheduler Walk Context DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed.

- H120 scheduler requested_context accepts walk: passed.
- H121 scheduler walk context resolves through memory tools: passed.
- H122 event envelopes preserve walk request and result evidence: passed.
- H123 invalid walk context is rejected before event persistence: passed.

## Scenario Results

### valid_walk_context

The runner projected a successful fork-run final record into an in-memory
Apacheta bridge using the production hub projection helper. It then built a
pending scheduled event with:

```json
{
  "tool": "walk",
  "direction": "forward",
  "depth": 1,
  "mode": "adjacent"
}
```

from the fork-run graph record.

Observed:

- the well-formed walk request was accepted by `build_pending_event`;
- `resolve_requested_context` dispatched to `tool_walk`;
- the resolved path included all four planned fork-run hub endpoints:
  coordinator root, branch-a result, branch-b result, and join result;
- all returned path steps had `depth: 1`;
- `build_event_envelope` preserved both the original walk request and the
  resolved walk result in parseable JSON.

### invalid_walk_cases

The runner checked five malformed walk requests:

- missing `from_record_id`;
- invalid `direction`;
- invalid `mode`;
- negative `depth`;
- unsupported extra key.

All five were rejected while building the pending event. No event persistence
was required to observe the rejection boundary.

## Interpretation

The prior graph work made fork-run records addressable and walkable as natural
hubs, but scheduler wakes still could not request graph evidence through the
normal event substrate. That gap is now closed for deterministic in-memory
execution: `requested_context` can carry a narrow, validated `walk` request, and
the wake envelope can expose the resulting graph neighborhood explicitly.

This matters because the event-loop substrate should not rely on hidden context
injection or runner-specific prompt text to make graph continuity evidence
available. A scheduled wake can now be asked to inspect the same memory graph
surface the instance would use interactively:

- `recall`: retrieve one known record or cycle;
- `compare`: inspect two known cycles;
- `walk`: inspect a bounded graph neighborhood.

## Design Implication

The event-loop continuity substrate now has a model-facing path from durable
fork-run identity to wake-time evidence:

1. fork/join policy produces final fork-run records;
2. fork-run records are projected as graph hubs;
3. adjacent walk recovers hub neighborhoods;
4. scheduled events can request adjacent walk context;
5. event envelopes preserve the request and resolved evidence.

The next behavioral question is whether live instances can use this explicit
walk evidence correctly at wake time. That is a model-behavior experiment, not
another graph substrate experiment.

## Verification

Commands run:

```bash
uv run python -m py_compile src/hamutay/events.py experiments/event_loop/scheduler_walk_context_des_20260605/run_scheduler_walk_context_des.py
uv run pytest tests/unit/test_events.py tests/unit/test_event_policies.py tests/unit/test_graph_tools.py -q
uv run python experiments/event_loop/scheduler_walk_context_des_20260605/run_scheduler_walk_context_des.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- focused tests: 78 passed.
- DES hypothesis results: H120-H123 true.
- broader regression suite: 278 passed.
