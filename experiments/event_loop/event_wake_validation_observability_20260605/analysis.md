# Analysis: Event Wake Validation Observability

Date: 2026-06-05

## Result

Completed event records now carry compact wake validation summaries when a
scheduled wake runs with an active state validator.

- H216 scheduler behavior is preserved: supported.
- H217 completed records include a summary when `state_validation` exists:
  supported.
- H218 unvalidated wakes omit the summary: supported.
- H219 event reports surface validation outcomes: supported.
- H220 model-authored state, repair artifacts, and merge diagnostics are not
  mutated by this observability change: supported by deterministic tests.

## Implementation

Added `build_wake_validation_summary` in `src/hamutay/events.py`.

The summary is extracted after `OpenTasteSession.exchange` completes and is
passed to `EventStore.append_completed` as optional audit metadata. It includes:

- validation status;
- first-pass status;
- repair attempted flag;
- repair status;
- repaired flag;
- whether repair raw output and repair validation are present;
- repair protected-field diagnostic counts when present.

The event runner does not feed this metadata back into the prompt, state merge,
validator, or repair builder. It is copied observability only.

`summarize_event_log` and `format_event_report` now expose the compact outcome
for completed events.

## Test Evidence

Deterministic tests cover:

- unvalidated scheduled wake completes with no `wake_validation` field;
- first-pass valid wake records `wake_validation.status == "valid"`;
- repaired wake records first-pass invalid, repaired status, repair raw output
  presence, repair validation presence, and protected `cycle` update
  diagnostics;
- human-readable event reports render validation status for completed wakes.

## Interpretation

This resolves a data hygiene problem in the event-loop substrate. Future
scheduled-event experiments no longer need to manually join the session JSONL
and event JSONL just to classify wake outcomes. The full validation and repair
artifacts remain in the session log; the event log carries enough summary to
support scheduler-level observability and reports.

This does not change the research boundary found in the delayed-thinking
example variant. DeepSeek still failed first-pass durable wake state use there.
The improvement is that future scheduler experiments can classify those
failures as first-pass, repaired, unrepaired, or repair-failed directly from
the event log.

## Verification

Commands run:

```bash
uv run python -m py_compile src/hamutay/events.py tests/unit/test_events.py
uv run pytest tests/unit/test_events.py -q
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed;
- event unit suite: 54 passed;
- focused regression suite: 296 passed.
