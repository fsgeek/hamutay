# Pre-Registration: Production Terminal-Surface Substrate Smoke

Date: 2026-06-05

## Research Question

Does the first-class scheduler `terminal_surface` substrate reproduce the
validated narrow second-wake behavior when exercised through production
`build_pending_event` and `run_next_event` rather than an experimental backend
wrapper?

## Hypotheses

- H361: Production terminal-surface events deliver both requested contexts in
  both smoke rows.
- H362: The OpenAI-compatible production backend uses the declared narrow
  terminal tool successfully in both rows.
- H363: Both rows end with valid second-wake durable state.
- H364: Both rows recover the exact phrase and reference the filtered
  `word-word-number` intermediate.
- H365: Event-log observability records the terminal surface tool/label.

## Method

Run two live DeepSeek v4 Pro second-wake-only smoke rows.

The seeded history and requested context match the prior panels:

- cycle 1: exact phrase and digest;
- cycle 2: clean compressed state;
- cycle 3: valid first-wake continuation state with `chain_intermediate`;
- event context:
  - `recall(cycle=1)`;
  - `recall(record_id=<cycle_3_record_id>, field="chain_intermediate")`.

The event is created with production `terminal_surface`:

- tool: `complete_second_wake`;
- tool choice: `auto`;
- copied fields:
  - `chain_final_answer`;
  - `chain_final_evidence`;
- substrate-set fields:
  - `thinking_status: bound_chain_completed`;
  - `chain_stage: second_wake_complete`;
  - `bound_record_id_used`;
  - baseline observation;
  - `protocol_surface` metadata.

The runner uses normal `OpenTasteSession`, `OpenAITasteBackend`, and
`step_pending_events`; no experimental terminal backend wrapper is used.

## Falsification Criteria

- H361 is falsified if either row lacks either context.
- H362 is falsified if either row fails before committing a state record due to
  terminal tool parse/provider failure.
- H363 is falsified if either row fails the second-wake validator.
- H364 is falsified if either row lacks phrase recovery or intermediate use.
- H365 is falsified if completed event summaries do not expose terminal surface
  tool/label metadata.

## Analysis Plan

Report:

- context delivery count;
- terminal parse/state-record count;
- final valid count;
- phrase recovery count;
- intermediate-use count;
- event summary terminal-surface fields;
- failure labels by row.
