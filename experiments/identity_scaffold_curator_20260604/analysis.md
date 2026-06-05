# Identity Scaffold Curator Analysis

Analysis date: 2026-06-04.

## Provenance

- Pre-registration: `c86653a` (`2e3b98d` OTS stamp)
- Implementation: `9e7e958` (`23ca6bf` OTS stamp)
- Model calls: none

## What Changed

`OpenTasteSession` now accepts an optional `continuity_curator` hook.

When configured, the session calls the curator after a successful cycle with:

- cycle number;
- source record ID;
- timestamp;
- prior state;
- raw model output;
- visible response text;
- merged state.

The curator artifact is logged durably as `continuity_curation` in the cycle
JSONL record. If the artifact contains `summary` or `carry_forward_summary`,
the scaffold injects a compact `Continuity curator summary` block into the next
cycle's system prompt.

The curator does not mutate the identity object. It is context for the next
cycle, not an automatic state update.

## Validation

- `uv run pytest tests/unit/test_events.py`: pass, 35 tests
- `uv run pytest tests/test_taste_open.py tests/unit/test_exchange_tools.py tests/unit/test_executor.py`: pass, 64 tests
- `uv run python -m py_compile src/hamutay/taste_open.py`: pass
- `git diff --check -- src/hamutay/taste_open.py tests/unit/test_events.py`: pass

## Hypothesis Assessment

### H23: Curator Hook Is Backward-Compatible

Supported for this slice.

No-curator sessions do not include curator context in the system prompt and do
not write `continuity_curation` or `curator_context_injection` fields to the
cycle log.

Existing event, taste-open, exchange-tool, and executor tests pass.

### H24: Curator Artifact Survives The Scheduling Boundary

Supported for this slice.

A fake curator's cycle-1 summary is logged in cycle 1 and injected into the
cycle-2 system prompt. The cycle-2 log records the injected curator context and
links it to the source record ID.

### H25: Curator Failure Is Observable And Non-Silent

Supported for this slice.

A fake curator failure is logged as a failed `continuity_curation` record. No
empty successful summary is injected into the next cycle.

## Interpretation

This is a scaffold capability, not a behavioral result.

The system can now represent the architecture implied by the experiments:

- identity object: model-owned state;
- continuity curator: post-cycle lifecycle artifact;
- next-cycle injection: bounded continuity context;
- recall/tools: still separate and unchanged.

This is the first implementation step toward not making the identity object
carry the entire memory system.

## Not In This Slice

- no model-backed curator;
- no CLI flag for enabling a model-backed curator;
- no recall-hook expansion;
- no behavioral panel using the new scaffold hook;
- no changes to schedule-event semantics.

## Recommended Next Step

Preregister a model-backed curator adapter for the hook, using the repaired
scorer as the primary metric. Keep recall expansion deferred until the curator
lifecycle is tested with real model outputs.
