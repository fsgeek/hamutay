# Analysis: Production Terminal-Surface Substrate Smoke

Date: 2026-06-05

## Result

The first production smoke falsified the implementation, not the terminal
surface concept.

Aggregate:

- rows: 2
- both requested contexts delivered: 2/2
- terminal parse/state-record success: 0/2
- final valid: 0/2
- event-log terminal surface metadata observed: 0/2 completed rows

Both rows failed with:

```text
'CountingBackend' object has no attribute 'call_terminal_surface'
```

## Interpretation

The event substrate worked up to context delivery:

- `recall(cycle=1)` delivered the exact phrase;
- filtered bound-record recall delivered only `chain_intermediate`;
- event summaries recorded the terminal surface tool and label on failed
  events.

The failure boundary was the backend wrapper. The production
`OpenAITasteBackend` had `call_terminal_surface`, but the common experimental
`CountingBackend` wrapper used by runners did not expose or delegate that
method. `OpenTasteSession` therefore failed before calling the underlying
OpenAI-compatible backend.

## Next Step

Patch `OpenTasteSession` to delegate terminal-surface calls through wrapper
backends that expose an inner `backend` with `call_terminal_surface`, while
preserving call-count observability for wrappers with an integer `calls` field.
Then rerun the smoke in a fresh preregistered repair directory.
