# Analysis: Terminal-Surface Substrate Smoke Repair

Date: 2026-06-05

## Result

The repair smoke passed.

Aggregate:

- rows: 2
- both requested contexts delivered: 2/2
- terminal parse/state-record success: 2/2
- final valid: 2/2
- exact phrase recovered: 2/2
- filtered `word-word-number` intermediate referenced: 2/2
- terminal surface tool/label observed in completed event summaries: 2/2
- bounded-call violations: 0/2
- runner errors: 0/2

Hypothesis outcomes:

- H371 passed.
- H372 passed.
- H373 passed.
- H374 passed.
- H375 passed.

## Comparison To Failed Smoke

The prior smoke failed 0/2 before state commit because the common
`CountingBackend` wrapper did not expose `call_terminal_surface`. Context
delivery was already 2/2 in that failed run.

The wrapper-delegation patch changed `OpenTasteSession` so terminal-surface
calls delegate through wrappers with an inner backend that supports
`call_terminal_surface`, preserving integer call-count observability.

After that patch:

- the same scheduled-event terminal surface completed 2/2;
- both rows passed the existing second-wake validator;
- event observability included `terminal_surface_tool` and
  `terminal_surface_label`.

## Interpretation

The first-class production path now reproduces the behavior found in the
experimental narrow-surface panels for this bounded second-wake task. This
validates the minimal substrate implementation:

- scheduled events can carry a terminal surface declaration;
- event envelopes expose it;
- `OpenTasteSession` uses the declared terminal surface instead of broad
  `think_and_respond`;
- OpenAI-compatible transport uses `tool_choice: auto`;
- the terminal tool output is translated into a durable state update;
- wake validation and event-log observability still operate normally.

The next research question is no longer whether this mechanism can work. It is
where the boundary lies: which scheduled wake classes should use narrow
surfaces, and what terminal surface schemas are appropriate for each.
