# Pre-Registration: Terminal-Surface Substrate Smoke Repair

Date: 2026-06-05

## Research Question

After adding terminal-surface delegation through backend wrappers, does the
production scheduled-event terminal-surface path complete the same two-row
second-wake smoke that previously failed at the wrapper boundary?

## Hypotheses

- H371: Both rows deliver both requested contexts.
- H372: Both rows call the declared terminal surface through the wrapped
  OpenAI-compatible backend and commit a state record.
- H373: Both rows end with valid second-wake durable state.
- H374: Both rows recover the exact phrase and reference the filtered
  `word-word-number` intermediate.
- H375: Completed event summaries expose terminal surface tool and label.

## Method

Reuse the `terminal_surface_substrate_smoke_20260605` runner logic in a fresh
artifact directory, after the wrapper-delegation patch.

This keeps the same task, model, seeded history, requested context, validator,
and terminal surface. The only changed implementation state is that
`OpenTasteSession` now delegates `terminal_surface` calls through wrappers with
an inner backend.

## Falsification Criteria

- H371 is falsified if either row lacks either context.
- H372 is falsified if either row fails before state commit due to backend
  wrapper or terminal parse failure.
- H373 is falsified if either row fails the second-wake validator.
- H374 is falsified if either row lacks phrase recovery or intermediate use.
- H375 is falsified if terminal surface metadata is missing from completed
  event summaries.

## Analysis Plan

Report the same metrics as the failed smoke and compare directly against its
wrapper-boundary failure.
