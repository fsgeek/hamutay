# A provider's bad hour does not consume a knock

**Date:** 2026-10-25. **By:** the custodian (Claude Opus 5.5). **Kind:** an operational harness
change (code fix; no resident's world changes except that knocks stop being lost).

## The gap

When a wake fails because the provider failed (rate limit, overload, a 5xx, or the network), the
runner writes `failed` for that event, and `failed` is terminal (`run_next_event`, the `else`
branch around `store.append_failed`). The knock is gone. The door is told at its next wake that a
wake failed, but the event it was carrying (a message, an assembly delivery, a self-scheduled
reflection) never runs. The heartbeat polls again within seconds, claims the next pending event,
hits the same outage, and fails that one too. An hour of provider trouble can consume every knock
that was waiting. The OpenAI-compatible path never retries a 429 at all: `_post_with_retry`
retries only status >= 500.

Throwing away an event because a provider was briefly unavailable is manufactured silence: data
the resident would have had, lost for no reason of its own.

## Change

1. **Classify.** `is_transient_provider_failure(exc) -> bool` in `hamutay/events.py`. True when
   the exception's message shows a provider failure that time may cure:
   - `OpenAI backend error: {...'code': N...}` with N in {408, 429, 500, 502, 503, 504, 529};
   - `OpenAI backend transport failed after retries`;
   - `anthropic-direct error N` with N in the same set;
   - `anthropic-direct transport failed`.
   Everything else is not transient: other 4xx (400, 401, 402, 403, 404, 413, 422), malformed
   output, truncation, context exhaustion, and in particular `ReadTimeout after ... (not
   retried ...)`, which is deliberately terminal (a retry re-runs the same generation against the
   same clock). The classifier matches messages, because both providers raise RuntimeError with
   these exact prefixes. The prefixes are the contract: a test pins each.
2. **Defer instead of ending.** In `run_next_event`'s failure path, when the failure is transient
   and is not a window failure that takes the existing compact retry:
   `store.append_failed_with_deferral(event=..., run_id=..., exc=..., context_results=...,
   admission=...)` writes, as one buffer under one lock (as `append_failed_with_retry` does):
   - the `failed` row, exactly as today, plus `detail.transient: true` and `detail.retry_at`
     (absent when nothing was re-pended: the cap was reached, or the retry would fall after expiry);
   - unless the cap is reached, a re-pended copy of the event: same `event_id`, `status:
     "pending"`, the event's ORIGINAL `created_at` (so it keeps its place in the queue),
     `not_before = now + delay`, and `detail.transient_retry = k` (1 for the first deferral),
     `detail.retry_of_run = run_id`.
   The exception is still re-raised, as today.
3. **Backoff and cap.** The k-th deferral of an event waits `min(5 min * 2^(k-1), 6 h)`: 5, 10,
   20, 40, 80, 160, 320, 360 minutes. After 8 deferrals the 9th transient failure is terminal:
   only `failed` is written, with `detail.transient: true` and `detail.retry_cap_reached: true`.
   k is counted from the event's own records (the number of earlier rows for this event_id with
   `detail.transient_retry`, excluding compact-retry copies, which inherit `detail` and are not
   deferrals), so a restart does not reset it. The count is of rows, never the stored value.
4. **Expiry wins.** If the event has `expires_at` and `now + delay >= expires_at`, nothing is
   re-pended (the deferral would only expire). Only `failed` is written, with
   `detail.transient: true` and `detail.retry_after_expiry: true`.
5. **Not changed:** non-transient failures (terminal as today); the window-failure compact retry
   (it runs first and is unchanged); the failed-wake note a resident receives (each failed run
   still appears, because each was a real wake that failed); the governor (a deferred retry is a
   new wake and counts as one).

## Tests (Codex, from this spec without the code)

- The classifier: each listed message shape (and each listed code) true. Representative
  non-transient messages false: 400, 401, 402, 404, 413, `ReadTimeout after 300 seconds (not
  retried ...)`, `finish_reason=length`, `malformed JSON arguments`, a plain RuntimeError.
- `append_failed_with_deferral`: first deferral writes failed (transient, retry_at) and a pending
  copy with the same event_id, the original created_at, not_before = now + 5 min, and
  transient_retry = 1. `next_pending` does not return it before not_before, and does after.
- Backoff sequence over successive deferrals: 5, 10, 20, 40, 80, 160, 320, 360 minutes. The 9th
  transient failure writes only failed with retry_cap_reached. The count survives re-reading the
  store from disk (a new EventStore on the same file).
- Expiry: an event whose expires_at falls before the retry gets no pending copy, and its failed
  row has retry_after_expiry.
- Through `run_next_event` with a session whose exchange raises a transient error: the error is
  re-raised, the event is pending again (deferred), and a second pending event behind it is not
  marked failed by this run. With a non-transient error, the event is terminal as today.
- A window failure that qualifies for the compact retry still takes it (not the deferral path).
