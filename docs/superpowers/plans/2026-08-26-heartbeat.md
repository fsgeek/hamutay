# Heartbeat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assemble the always-on heartbeat daemon around the existing event loop: boot recovery, external `send` ingress, atomic continuation appends, legible quiet, systemd/nohup deployment, and the first-tick runbook.

**Architecture:** A new `src/hamutay/heartbeat.py` wraps the existing `run_pending_events`/`summarize_event_log` machinery in a wall-clock loop with crash-only boot recovery. `src/hamutay/events.py` gains an external-origin inbound event builder, a `send` CLI subcommand (the event store itself is the mailbox), and an atomic completed+continuation append that closes the crash window. Deployment is a systemd user unit with a nohup fallback; log digests are checkpointed into git so the OTS post-commit hook anchors them.

**Tech Stack:** Python ≥3.14, `uv` (no system Python — run everything as `uv run pytest ...`), pytest, JSONL append-only store already in `events.py`, fcntl flock, systemd user units.

**Spec:** `docs/superpowers/specs/2026-08-26-heartbeat-founding-spec.md`

## Global Constraints

- Run all Python via `uv run` (e.g. `uv run pytest tests/test_heartbeat.py -v`). There is no system Python.
- `max_tokens` is 64000 everywhere. Never introduce a lower default (CLAUDE.md: "max_tokens is a guillotine").
- Every commit uses the identity incantation — the bare repo config diverges from history and pushes will fail silently without it:
  ```bash
  git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "<message>

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
  ```
- This is a SHARED working tree with parallel instances. `git add` only the exact files named in the task. Never `git add -A` / `git add .`.
- A post-commit hook creates OTS stamp commits automatically; do not be surprised by them and do not modify `scripts/hooks/`.
- Tests written here are development tests (TDD). Codex authors independent validating tests in separate signed commits per repo norm; do not claim this plan's tests are the validation.
- Do not add cognitive priors to the resident's prompt beyond the constitution constant defined in Task 7 (no strand counts, no curation advice).
- Line numbers below were measured on `main` at commit 3971901; if drift has occurred, locate by the quoted code, not the number.

---

### Task 1: Parser extraction + kill the 4096 default

**Files:**
- Modify: `src/hamutay/events.py` (function `main()`, ~line 1733 to end; the two `--max-tokens` `add_argument` calls with `default=4096`)
- Create: `tests/test_event_ingress.py`

**Interfaces:**
- Produces: `hamutay.events.build_parser() -> argparse.ArgumentParser` — module-level, containing everything `main()` currently builds inline. `main()` becomes `args = build_parser().parse_args()` plus the existing dispatch. Task 2 adds a subparser to `build_parser`; Task 7's CLI test imports it as the pattern to follow.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_event_ingress.py
"""Development tests for the heartbeat's event-store ingress surface."""
from hamutay.events import build_parser


def test_run_next_defaults_to_64000_max_tokens():
    args = build_parser().parse_args(["run-next", "--log-path", "x.jsonl"])
    assert args.max_tokens == 64000


def test_run_all_defaults_to_64000_max_tokens():
    args = build_parser().parse_args(["run-all", "--log-path", "x.jsonl"])
    assert args.max_tokens == 64000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_event_ingress.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_parser'`

- [ ] **Step 3: Implement**

In `src/hamutay/events.py`, cut the parser construction out of `main()` into a module-level function directly above it. The full function (identical to today's inline construction except the two `--max-tokens` defaults and their help strings):

```python
def build_parser() -> "argparse.ArgumentParser":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run one pending taste_open scheduled event."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-next")
    run.add_argument("--log-path", required=True)
    run.add_argument("--event-log-path", default=None)
    run.add_argument("--model", default="claude-haiku-4-5")
    run.add_argument(
        "--provider",
        choices=["anthropic", "openrouter", "openai"],
        default="anthropic",
    )
    run.add_argument("--base-url", default=None)
    run.add_argument("--api-key", default=None)
    run.add_argument("--project-root", default=".")
    run.add_argument(
        "--max-tokens",
        type=int,
        default=64000,
        help="Maximum output tokens for the wake cycle. "
        "Matches the Projector; do not lower.",
    )
    run_all = sub.add_parser("run-all")
    run_all.add_argument("--log-path", required=True)
    run_all.add_argument("--event-log-path", default=None)
    run_all.add_argument("--model", default="claude-haiku-4-5")
    run_all.add_argument(
        "--provider",
        choices=["anthropic", "openrouter", "openai"],
        default="anthropic",
    )
    run_all.add_argument("--base-url", default=None)
    run_all.add_argument("--api-key", default=None)
    run_all.add_argument("--project-root", default=".")
    run_all.add_argument(
        "--max-tokens",
        type=int,
        default=64000,
        help="Maximum output tokens for each wake cycle. "
        "Matches the Projector; do not lower.",
    )
    run_all.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of pending events to run.",
    )
    run_all.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Keep processing later events after a wake failure.",
    )
    report = sub.add_parser("report")
    report.add_argument(
        "--log-path",
        default=None,
        help="Session JSONL path; event sidecar is derived from this path.",
    )
    report.add_argument(
        "--event-log-path",
        default=None,
        help="Event JSONL path. Overrides --log-path sidecar derivation.",
    )
    report.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON rather than human-readable text.",
    )
    report.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum failed/completed/context-error rows to show.",
    )
    return parser
```

(Cross-check each argument against the current `main()` body while cutting; if `main()` has drifted from the listing above, the file wins — the only intended changes are `default=64000` and the two help strings.)

`main()` then begins:

```python
def main() -> None:
    import os

    from hamutay.taste_open import (
        AnthropicTasteBackend,
        OpenAITasteBackend,
        OpenTasteSession,
    )

    args = build_parser().parse_args()
```

with the rest of `main()` unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_event_ingress.py -v`
Expected: 2 PASS

- [ ] **Step 5: Run the existing event tests to confirm no regression**

Run: `uv run pytest tests/ -k "event" -v`
Expected: whatever passed before still passes (no new failures).

- [ ] **Step 6: Commit**

```bash
git add src/hamutay/events.py tests/test_event_ingress.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "extract events CLI parser; raise max_tokens default to 64000

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: External inbound events + `send` subcommand

**Files:**
- Modify: `src/hamutay/events.py` (constants near line 15; new builder near `build_pending_event` ~line 122; `build_parser` and `main` dispatch from Task 1)
- Test: `tests/test_event_ingress.py`

**Interfaces:**
- Consumes: `build_parser()` from Task 1; existing `EventStore`, `utc_now_iso`, `validate_requested_context`.
- Produces:
  - `EVENT_TYPE_INBOUND = "inbound_message"` (module constant)
  - `build_inbound_event(*, purpose: str, sender: str, label: str | None = None, not_before: str | None = None, expires_at: str | None = None, requested_context: list[dict] | None = None) -> dict` — returns a pending `event_status` record with `origin: "external"`; does not write it.
  - `_handle_send(args) -> dict` — appends the built record to the store and returns it; `main()` dispatches `send` to it. Task 10's runbook calls `python -m hamutay.events send ...`.

The record deliberately omits `scheduled_by_cycle`/`scheduled_by_record_id`: the claim path (`next_pending`, `events.py:388`) filters only on `record_type`/`status`, and `resolve_requested_context` + `build_event_envelope` read those fields via `.get(...)` with defaults (`events.py:747-753`). Verify those three sites still use `.get` before relying on this; if any has grown a hard requirement, add the field with value `None` rather than fabricating provenance.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_event_ingress.py`:

```python
import json

import pytest

from hamutay.events import (
    EVENT_TYPE_INBOUND,
    EventStore,
    build_inbound_event,
)


def test_build_inbound_event_shape():
    record = build_inbound_event(purpose="hello resident", sender="tony")
    assert record["record_type"] == "event_status"
    assert record["event_type"] == EVENT_TYPE_INBOUND
    assert record["status"] == "pending"
    assert record["origin"] == "external"
    assert record["sender"] == "tony"
    assert record["purpose"] == "hello resident"
    assert record["event_id"]
    assert record["created_at"]
    assert "scheduled_by_cycle" not in record


def test_build_inbound_event_requires_purpose_and_sender():
    with pytest.raises(ValueError):
        build_inbound_event(purpose="   ", sender="tony")
    with pytest.raises(ValueError):
        build_inbound_event(purpose="hi", sender="")


def test_inbound_event_is_claimable(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    record = build_inbound_event(purpose="hello", sender="tony")
    store.append(record)
    claimable = store.next_pending()
    assert claimable is not None
    assert claimable["event_id"] == record["event_id"]


def test_inbound_event_honors_not_before(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    record = build_inbound_event(
        purpose="later", sender="tony", not_before="2999-01-01T00:00:00Z"
    )
    store.append(record)
    assert store.next_pending() is None


def test_send_subcommand_appends_to_store(tmp_path):
    from hamutay.events import _handle_send, build_parser

    log_path = tmp_path / "session.jsonl"
    args = build_parser().parse_args(
        ["send", "--log-path", str(log_path), "--message", "first tick", "--sender", "tony"]
    )
    written = _handle_send(args)
    from hamutay.events import default_event_log_path

    store = EventStore(str(default_event_log_path(str(log_path))))
    latest = store.latest_by_event_id()
    assert written["event_id"] in latest
    assert latest[written["event_id"]]["purpose"] == "first tick"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_event_ingress.py -v`
Expected: new tests FAIL with `ImportError: cannot import name 'EVENT_TYPE_INBOUND'`

- [ ] **Step 3: Implement**

In `src/hamutay/events.py`, next to `EVENT_TYPE_REFLECTION` (~line 15):

```python
EVENT_TYPE_INBOUND = "inbound_message"
```

Directly below `build_pending_event`:

```python
def build_inbound_event(
    *,
    purpose: str,
    sender: str,
    label: str | None = None,
    not_before: str | None = None,
    expires_at: str | None = None,
    requested_context: list[dict] | None = None,
) -> dict:
    """Create an externally-originated pending event. Does not write it."""
    purpose = str(purpose).strip()
    if not purpose:
        raise ValueError("purpose is required")
    sender = str(sender).strip()
    if not sender:
        raise ValueError("sender is required")
    record = {
        "record_type": "event_status",
        "event_id": str(uuid4()),
        "event_type": EVENT_TYPE_INBOUND,
        "status": "pending",
        "created_at": utc_now_iso(),
        "origin": "external",
        "sender": sender,
        "purpose": purpose,
    }
    if requested_context is not None:
        record["requested_context"] = validate_requested_context(requested_context)
    if label:
        record["label"] = str(label)
    for field, value in (("not_before", not_before), ("expires_at", expires_at)):
        if value:
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            record[field] = str(value)
    return record
```

In `build_parser()`, add after the `report` subparser:

```python
    send = sub.add_parser("send", help="Append an external inbound event.")
    send.add_argument("--log-path", required=True)
    send.add_argument("--event-log-path", default=None)
    send.add_argument("--message", required=True, help="The event's purpose text.")
    send.add_argument("--sender", default="tony")
    send.add_argument("--label", default=None)
    send.add_argument("--not-before", default=None)
```

Module-level handler (above `main`):

```python
def _handle_send(args) -> dict:
    event_log_path = args.event_log_path or str(default_event_log_path(args.log_path))
    store = EventStore(event_log_path)
    record = build_inbound_event(
        purpose=args.message,
        sender=args.sender,
        label=args.label,
        not_before=args.not_before,
    )
    store.append(record)
    print(json.dumps(record, indent=2, default=str))
    return record
```

In `main()`, immediately after the `report` dispatch block:

```python
    if args.command == "send":
        _handle_send(args)
        return
```

(The `send` path must run before any backend construction — sending needs no API key.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_event_ingress.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/events.py tests/test_event_ingress.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "add external inbound events and the send subcommand (the store is the mailbox)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Atomic completed+continuation append

**Files:**
- Modify: `src/hamutay/events.py` (`EventStore.append_completed` ~line 452; the completed path inside `run_next_event`, the block that currently reads `completed = store.append_completed(` at ~line 1549 followed by `store.append(auto_continuation_event)` at ~line 1561)
- Test: `tests/test_event_ingress.py`

**Interfaces:**
- Consumes: `EventStore.append_many` (`events.py:373`, lock-guarded).
- Produces: `EventStore.append_completed_atomic(...)` — identical keyword signature to `append_completed` (`event, run_id, wake_cycle, result_record_id, response_text, context_results=None, outcome_observation=None, wake_validation=None, auto_continuation_event=None`), but when `auto_continuation_event` is not None it persists the completed record AND the continuation event in one `append_many` call. Returns the completed record dict. Also rewrites `append_many` to serialize the whole batch into ONE buffer and ONE `write` call.

**The guarantee, stated honestly (per cross-family review):** today's `append_many` holds one lock but performs a separate open/write/close per record (`_append_unlocked`, `events.py:350`), so a `kill -9` between records can still split the batch. The rewrite below narrows the window to a single `write(2)` of one buffer to an append-mode file — indivisible under process kill, NOT under power loss or partial-page filesystem failure. Therefore the guarantee is "non-interleaved, single-write intent," and Task 4's lost-continuation recovery applies to ALL log versions as defense in depth, not just pre-Task-3 logs.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_event_ingress.py`:

```python
from uuid import uuid4 as _uuid4

from hamutay.events import build_pending_event


def _pending(store):
    record = build_inbound_event(purpose="work", sender="tony")
    store.append(record)
    return record


def test_append_completed_atomic_persists_both_records(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = _pending(store)
    continuation = build_pending_event(
        purpose="continue the work",
        requested_context=[{"tool": "recall", "record_id": str(_uuid4())}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=_uuid4(),
    )
    completed = store.append_completed_atomic(
        event=event,
        run_id=str(_uuid4()),
        wake_cycle=1,
        result_record_id=_uuid4(),
        response_text="done",
        auto_continuation_event=continuation,
    )
    latest = store.latest_by_event_id()
    assert latest[event["event_id"]]["status"] == "completed"
    assert latest[continuation["event_id"]]["status"] == "pending"
    assert completed["auto_continuation_appended"] is True
    assert completed["auto_continuation_event_id"] == continuation["event_id"]


def test_append_completed_atomic_without_continuation(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = _pending(store)
    store.append_completed_atomic(
        event=event,
        run_id=str(_uuid4()),
        wake_cycle=1,
        result_record_id=_uuid4(),
        response_text="done",
    )
    latest = store.latest_by_event_id()
    assert latest[event["event_id"]]["status"] == "completed"
    assert "auto_continuation_appended" not in latest[event["event_id"]]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_event_ingress.py -v`
Expected: FAIL with `AttributeError: ... 'append_completed_atomic'`

- [ ] **Step 3: Implement**

First, in `EventStore`, replace the body of `append_many` (`events.py:373`) so the batch is one buffer and one write syscall:

```python
    def append_many(self, records: list[dict]) -> None:
        if not records:
            return
        payload = "".join(
            json.dumps(record, default=str) + "\n" for record in records
        )
        with self._locked():
            with self.path.open("a") as f:
                f.write(payload)
```

(Behavior-compatible for every existing caller: same bytes, same lock, fewer syscalls.)

Then refactor `append_completed` so the record-building is shared, and add the atomic variant. The built record must be byte-for-byte what `append_completed` builds today (`events.py:466-488`):

```python
    def _build_completed(
        self,
        *,
        event: dict,
        run_id: str,
        wake_cycle: int,
        result_record_id,
        response_text: str,
        context_results: list[dict] | None = None,
        outcome_observation: dict | None = None,
        wake_validation: dict | None = None,
        auto_continuation_event: dict | None = None,
    ) -> dict:
        record = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "completed",
            "run_id": run_id,
            "completed_at": utc_now_iso(),
            "wake_cycle": wake_cycle,
            "result_record_id": str(result_record_id),
            "response_text": response_text,
        }
        if context_results is not None:
            record["context_results"] = context_results
        if outcome_observation is not None:
            record["outcome_observation"] = outcome_observation
        if wake_validation is not None:
            record["wake_validation"] = wake_validation
        if auto_continuation_event is not None:
            record["auto_continuation_appended"] = True
            record["auto_continuation_event_id"] = (
                auto_continuation_event.get("event_id")
            )
        return record

    def append_completed(self, **kwargs) -> dict:
        record = self._build_completed(**kwargs)
        self.append(record)
        return record

    def append_completed_atomic(self, **kwargs) -> dict:
        auto_continuation_event = kwargs.get("auto_continuation_event")
        record = self._build_completed(**kwargs)
        if auto_continuation_event is not None:
            self.append_many([record, auto_continuation_event])
        else:
            self.append(record)
        return record
```

(Keep the original `append_completed` docstring/signature semantics: it still appends only the completed record, so experiment replays are untouched.)

In `run_next_event`'s completed path (~line 1549): change `store.append_completed(` to `store.append_completed_atomic(` and DELETE the now-redundant `store.append(auto_continuation_event)` line inside the `if auto_continuation_event is not None:` block (~line 1561), keeping the in-memory `completed["auto_continuation_event"] = auto_continuation_event` assignment that follows it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_event_ingress.py -v`
Expected: all PASS

- [ ] **Step 5: Run broader event tests for regression**

Run: `uv run pytest tests/ -k "event" -v`
Expected: no new failures.

- [ ] **Step 6: Commit**

```bash
git add src/hamutay/events.py tests/test_event_ingress.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "close the completed/continuation crash window with an atomic append

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Boot recovery

**Files:**
- Create: `src/hamutay/heartbeat.py`
- Create: `tests/test_heartbeat.py`

**Interfaces:**
- Consumes: `EventStore` (`.read_records()`, `.latest_by_event_id()`, `.append()`), `utc_now_iso`, `EVENT_TYPE_REFLECTION` from `hamutay.events`.
- Produces:
  - `recover_orphaned_running(store: EventStore) -> list[dict]` — for every event whose latest status is `running`, re-appends its most recent full `pending` record with `recovered_by="boot_recovery"`, `recovered_at`, `recovered_from_run_id`.
  - `recover_lost_continuations(store: EventStore) -> list[dict]` — for every completed record with `auto_continuation_appended` whose `auto_continuation_event_id` has no `event_status` record, appends a synthetic pending event whose `declared_loss` and `purpose` state that the content was lost. Applies to ALL log versions — Task 3 narrows the crash window to power-loss scale but does not eliminate it, so this recovery is permanent defense in depth.
  - Task 6's `HeartbeatLoop.boot()` calls both.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_heartbeat.py
"""Development tests for the heartbeat daemon."""
from uuid import uuid4

from hamutay.events import EventStore, build_inbound_event
from hamutay.heartbeat import (
    recover_lost_continuations,
    recover_orphaned_running,
)


def _crashed_mid_wake(store):
    event = build_inbound_event(purpose="interrupted work", sender="tony")
    store.append(event)
    store.append_running(event)
    return event


def test_recover_orphaned_running_repends_original(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = _crashed_mid_wake(store)
    recovered = recover_orphaned_running(store)
    assert len(recovered) == 1
    latest = store.latest_by_event_id()[event["event_id"]]
    assert latest["status"] == "pending"
    assert latest["purpose"] == "interrupted work"
    assert latest["recovered_by"] == "boot_recovery"
    assert latest["recovered_from_run_id"]


def test_recover_orphaned_running_is_idempotent(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    _crashed_mid_wake(store)
    recover_orphaned_running(store)
    assert recover_orphaned_running(store) == []


def test_recover_orphaned_running_ignores_terminal_events(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="done work", sender="tony")
    store.append(event)
    store.append_running(event)
    store.append_completed(
        event=event,
        run_id=str(uuid4()),
        wake_cycle=1,
        result_record_id=uuid4(),
        response_text="done",
    )
    assert recover_orphaned_running(store) == []


def test_recover_lost_continuations_declares_the_loss(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="work", sender="tony")
    store.append(event)
    store.append_running(event)
    lost_id = str(uuid4())
    # Simulate the pre-atomic crash: completed record annotated, continuation
    # never appended.
    store.append_completed(
        event=event,
        run_id=str(uuid4()),
        wake_cycle=1,
        result_record_id=uuid4(),
        response_text="done",
        auto_continuation_event={"event_id": lost_id},
    )
    recovered = recover_lost_continuations(store)
    assert len(recovered) == 1
    replacement = store.latest_by_event_id()[lost_id]
    assert replacement["status"] == "pending"
    assert "declared_loss" in replacement
    assert replacement["recovered_by"] == "boot_recovery"
    assert recover_lost_continuations(store) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_heartbeat.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hamutay.heartbeat'`

- [ ] **Step 3: Implement**

```python
# src/hamutay/heartbeat.py
"""Heartbeat: the always-on daemon that gives the event loop wall-clock life.

Spec: docs/superpowers/specs/2026-08-26-heartbeat-founding-spec.md
The log is the life; the process is weather. Boot always runs recovery.
"""
from __future__ import annotations

from hamutay.events import (
    EVENT_TYPE_REFLECTION,
    EventStore,
    utc_now_iso,
)


def recover_orphaned_running(store: EventStore) -> list[dict]:
    """Re-pend events whose latest status is a claim that never terminalized."""
    records = store.read_records()
    latest = store.latest_by_event_id()
    recovered = []
    for event_id, last in latest.items():
        if last.get("status") != "running":
            continue
        original = None
        for record in records:
            if (
                record.get("record_type") == "event_status"
                and record.get("event_id") == event_id
                and record.get("status") == "pending"
            ):
                original = record
        if original is None:
            continue
        repend = dict(original)
        repend["status"] = "pending"
        repend["recovered_by"] = "boot_recovery"
        repend["recovered_at"] = utc_now_iso()
        repend["recovered_from_run_id"] = last.get("run_id")
        store.append(repend)
        recovered.append(repend)
    return recovered


def recover_lost_continuations(store: EventStore) -> list[dict]:
    """Materialize continuations lost in a completed/continuation crash gap.

    append_completed_atomic narrows this window to a single write syscall,
    but power loss can still split it, and older logs predate the atomic
    path entirely. This recovery therefore applies to all log versions.
    The content is unrecoverable; the replacement event says so.
    """
    records = store.read_records()
    known = {
        record.get("event_id")
        for record in records
        if record.get("record_type") == "event_status"
    }
    recovered = []
    for record in records:
        if record.get("record_type") != "event_status":
            continue
        if record.get("status") != "completed":
            continue
        if not record.get("auto_continuation_appended"):
            continue
        lost_id = record.get("auto_continuation_event_id")
        if not lost_id or lost_id in known:
            continue
        replacement = {
            "record_type": "event_status",
            "event_id": lost_id,
            "event_type": EVENT_TYPE_REFLECTION,
            "status": "pending",
            "created_at": utc_now_iso(),
            "recovered_by": "boot_recovery",
            "recovered_at": utc_now_iso(),
            "recovered_from_completed_record": record.get("result_record_id"),
            "declared_loss": (
                "The content of this continuation was lost in a crash between "
                "the completed append and the continuation append. Only its "
                "id and the fact of its intent survive."
            ),
            "purpose": (
                "Recover a lost continuation. A previous wake bound a "
                "continuation whose content did not survive a crash. Consult "
                "your current state for the wake recorded at result_record_id "
                f"{record.get('result_record_id')} and either re-derive the "
                "intended continuation or record that it is no longer needed."
            ),
        }
        store.append(replacement)
        known.add(lost_id)
        recovered.append(replacement)
    return recovered
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_heartbeat.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/heartbeat.py tests/test_heartbeat.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "heartbeat boot recovery: re-pend orphans, declare lost continuations

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Legible quiet

**Files:**
- Modify: `src/hamutay/heartbeat.py`
- Test: `tests/test_heartbeat.py`

**Interfaces:**
- Consumes: `EventStore.append`, `EventStore.next_pending`, `utc_now_iso`.
- Produces:
  - `append_heartbeat_status(store, *, status: str, reason: str, detail: dict | None = None) -> dict` — appends a `record_type: "heartbeat_status"` record (no `event_id` field; it is not an event).
  - `derive_quiet_reason(records: list[dict]) -> str` — v1 heuristic from the spec: any latest-status `expired` → `"starved_expired"`; no completed `event_status` records → `"awaiting_first_event"`; else `"chosen_quiet"`.
  - Task 6's `HeartbeatLoop` calls both on state transitions only.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_heartbeat.py`:

```python
from hamutay.heartbeat import append_heartbeat_status, derive_quiet_reason


def test_heartbeat_status_record_shape(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    record = append_heartbeat_status(
        store, status="quiet", reason="chosen_quiet", detail={"note": "test"}
    )
    assert record["record_type"] == "heartbeat_status"
    assert record["status"] == "quiet"
    assert record["reason"] == "chosen_quiet"
    assert record["created_at"]
    assert "event_id" not in record
    persisted = store.read_records()
    assert persisted[-1]["record_type"] == "heartbeat_status"


def test_heartbeat_status_does_not_disturb_the_queue(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="real work", sender="tony")
    store.append(event)
    append_heartbeat_status(store, status="active", reason="runnable_pending")
    claimable = store.next_pending()
    assert claimable is not None
    assert claimable["event_id"] == event["event_id"]


def test_derive_quiet_reason_awaiting_first_event(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    assert derive_quiet_reason(store.read_records()) == "awaiting_first_event"


def test_derive_quiet_reason_starved_on_expiry(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(
        purpose="too late", sender="tony", expires_at="2000-01-01T00:00:00Z"
    )
    store.append(event)
    store.append_expired(event)
    assert derive_quiet_reason(store.read_records()) == "starved_expired"


def test_derive_quiet_reason_chosen_after_clean_completion(tmp_path):
    from uuid import uuid4

    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="work", sender="tony")
    store.append(event)
    store.append_running(event)
    store.append_completed(
        event=event,
        run_id=str(uuid4()),
        wake_cycle=1,
        result_record_id=uuid4(),
        response_text="done, resting",
    )
    assert derive_quiet_reason(store.read_records()) == "chosen_quiet"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_heartbeat.py -v`
Expected: new tests FAIL with `ImportError: cannot import name 'append_heartbeat_status'`

- [ ] **Step 3: Implement**

Append to `src/hamutay/heartbeat.py` (add `from uuid import uuid4` to imports):

```python
def append_heartbeat_status(
    store: EventStore,
    *,
    status: str,
    reason: str,
    detail: dict | None = None,
) -> dict:
    """Record a daemon state transition. Not an event; carries no event_id."""
    record = {
        "record_type": "heartbeat_status",
        "heartbeat_record_id": str(uuid4()),
        "status": str(status),
        "reason": str(reason),
        "created_at": utc_now_iso(),
    }
    if detail is not None:
        record["detail"] = detail
    store.append(record)
    return record


def derive_quiet_reason(records: list[dict]) -> str:
    """v1 heuristic (declared in the spec): expiry beats novelty beats choice."""
    latest: dict[str, dict] = {}
    completed_seen = False
    for record in records:
        if record.get("record_type") != "event_status":
            continue
        latest[record.get("event_id")] = record
        if record.get("status") == "completed":
            completed_seen = True
    if any(r.get("status") == "expired" for r in latest.values()):
        return "starved_expired"
    if not completed_seen:
        return "awaiting_first_event"
    return "chosen_quiet"
```

If `test_heartbeat_status_does_not_disturb_the_queue` fails because
`latest_by_event_id`/`next_pending` chokes on a record without an `event_id`,
do NOT add a fake event_id — fix the reading side to skip records whose
`record_type` is not `event_status` (inspect `_latest_by_event_id_from_records`
in `events.py` and add the filter there; that is the correct general fix and
also protects the summarizer).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_heartbeat.py tests/test_event_ingress.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/heartbeat.py tests/test_heartbeat.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "heartbeat: legible quiet (status records + v1 quiet-reason heuristic)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

(If the reading-side filter in `events.py` was needed, add `src/hamutay/events.py` to the `git add`.)

---

### Task 6: The loop

**Files:**
- Modify: `src/hamutay/heartbeat.py`
- Test: `tests/test_heartbeat.py`

**Interfaces:**
- Consumes: Task 4 recovery functions, Task 5 status functions, `run_pending_events` and `summarize_event_log` from `hamutay.events`.
- Produces: `HeartbeatLoop(session, store, *, poll_interval=30.0, batch_limit=10, sleep=time.sleep, now=None, run_pending=run_pending_events, summarize=summarize_event_log)` with:
  - `boot() -> dict` — runs both recoveries, appends a `waking` status, emits a flushed JSON ops line to stdout, returns counts.
  - `step() -> dict` — captures ONE `now = self._now()` and threads it through both the claim path (`run_pending`) and summarization (cross-family finding: split clocks let tests and claims disagree). Peeks `store.next_pending(now=now)` BEFORE the batch and records an `active` transition if work is runnable — otherwise a quiet→work→quiet cycle completed inside one batch leaves no trace (cross-family finding: the constitutionally required record gets suppressed). Returns `{"state": "active"|"waiting"|"quiet", "sleep_seconds": float, "batch": dict}`.
  - Transition dedup key is `(status, reason)`, not status alone — `quiet/awaiting_first_event → quiet/starved_expired` must produce a record.
  - Every transition and the boot report print one flushed JSON line to stdout (journald/daemon.out observability; the runbook reads these).
  - `run_forever() -> None` — `boot()`, then loop `step()`/sleep. Task 7's CLI constructs and calls this.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_heartbeat.py`:

```python
from hamutay.heartbeat import HeartbeatLoop


class _StubSession:
    pass


def _loop(tmp_path, *, summaries, batch=None):
    """A HeartbeatLoop with stubbed run/summarize; summaries is consumed in order."""
    store = EventStore(str(tmp_path / "events.jsonl"))
    sleeps = []
    summary_iter = iter(summaries)

    loop = HeartbeatLoop(
        _StubSession(),
        store,
        poll_interval=30.0,
        sleep=sleeps.append,
        run_pending=lambda session, s, **kw: batch or {"results": []},
        summarize=lambda records, now=None: next(summary_iter),
    )
    return loop, store, sleeps


def test_step_active_when_runnable(tmp_path):
    loop, store, _ = _loop(
        tmp_path, summaries=[{"pending_runnable_count": 2, "pending_waiting_count": 0}]
    )
    result = loop.step()
    assert result["state"] == "active"
    assert result["sleep_seconds"] == 0.0


def test_step_waiting_sleeps_until_wake_capped_by_poll(tmp_path):
    from datetime import datetime, timedelta, timezone

    wake_at = (datetime.now(timezone.utc) + timedelta(seconds=7)).isoformat()
    loop, store, _ = _loop(
        tmp_path,
        summaries=[
            {
                "pending_runnable_count": 0,
                "pending_waiting_count": 1,
                "oldest_waiting_pending": {"not_before": wake_at},
            }
        ],
    )
    result = loop.step()
    assert result["state"] == "waiting"
    assert 0.0 < result["sleep_seconds"] <= 30.0


def test_step_quiet_appends_status_once_per_transition(tmp_path):
    quiet_summary = {"pending_runnable_count": 0, "pending_waiting_count": 0}
    loop, store, _ = _loop(tmp_path, summaries=[quiet_summary, quiet_summary])
    loop.step()
    loop.step()
    statuses = [
        r for r in store.read_records() if r.get("record_type") == "heartbeat_status"
    ]
    assert len(statuses) == 1
    assert statuses[0]["status"] == "quiet"
    assert statuses[0]["reason"] == "awaiting_first_event"


def test_quiet_to_work_to_quiet_leaves_a_trace(tmp_path):
    """Cross-family finding 2: a wake completed entirely inside one batch must
    still record active, and the return to quiet must record chosen_quiet."""
    from uuid import uuid4

    quiet_summary = {"pending_runnable_count": 0, "pending_waiting_count": 0}
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="quick work", sender="tony")

    def fake_run(session, s, **kw):
        if s.next_pending() is None:
            return {"results": []}
        s.append_running(event)
        s.append_completed(
            event=event,
            run_id=str(uuid4()),
            wake_cycle=1,
            result_record_id=uuid4(),
            response_text="done",
        )
        return {"results": [{"status": "completed"}]}

    summary_iter = iter([quiet_summary, quiet_summary])
    loop = HeartbeatLoop(
        _StubSession(),
        store,
        poll_interval=30.0,
        sleep=lambda s: None,
        run_pending=fake_run,
        summarize=lambda records, now=None: next(summary_iter),
    )
    loop.step()  # empty store: quiet/awaiting_first_event
    store.append(event)
    loop.step()  # work arrives and completes inside this one step
    trace = [
        (r["status"], r["reason"])
        for r in store.read_records()
        if r.get("record_type") == "heartbeat_status"
    ]
    assert trace == [
        ("quiet", "awaiting_first_event"),
        ("active", "runnable_pending"),
        ("quiet", "chosen_quiet"),
    ]


def test_quiet_reason_change_is_recorded(tmp_path):
    """Cross-family finding 2b: dedup by (status, reason) — a starvation that
    arrives while already quiet must still be recorded."""
    quiet_summary = {"pending_runnable_count": 0, "pending_waiting_count": 0}
    loop, store, _ = _loop(
        tmp_path, summaries=[quiet_summary, quiet_summary]
    )
    loop.step()  # quiet/awaiting_first_event
    event = build_inbound_event(
        purpose="too late", sender="tony", expires_at="2000-01-01T00:00:00Z"
    )
    store.append(event)
    store.append_expired(event)
    loop.step()
    trace = [
        (r["status"], r["reason"])
        for r in store.read_records()
        if r.get("record_type") == "heartbeat_status"
    ]
    assert trace[-1] == ("quiet", "starved_expired")
    assert len(trace) == 2


def test_boot_recovers_and_announces(tmp_path):
    loop, store, _ = _loop(tmp_path, summaries=[])
    event = build_inbound_event(purpose="interrupted", sender="tony")
    store.append(event)
    store.append_running(event)
    report = loop.boot()
    assert report["orphaned_running_recovered"] == 1
    statuses = [
        r for r in store.read_records() if r.get("record_type") == "heartbeat_status"
    ]
    assert statuses[-1]["status"] == "waking"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_heartbeat.py -v`
Expected: FAIL with `ImportError: cannot import name 'HeartbeatLoop'`

- [ ] **Step 3: Implement**

Append to `src/hamutay/heartbeat.py` (extend imports: `import time`, `from datetime import datetime, timezone`, and `run_pending_events`, `summarize_event_log` from `hamutay.events`):

```python
class HeartbeatLoop:
    """Wall-clock life for the event loop. Crash-only: boot always recovers."""

    def __init__(
        self,
        session,
        store: EventStore,
        *,
        poll_interval: float = 30.0,
        batch_limit: int = 10,
        sleep=time.sleep,
        now=None,
        run_pending=run_pending_events,
        summarize=summarize_event_log,
    ):
        self._session = session
        self._store = store
        self._poll_interval = float(poll_interval)
        self._batch_limit = int(batch_limit)
        self._sleep = sleep
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._run_pending = run_pending
        self._summarize = summarize
        self._last_transition: tuple[str, str] | None = None

    @staticmethod
    def _emit(payload: dict) -> None:
        """One flushed JSON ops line per meaningful moment (journald-friendly)."""
        print(json.dumps(payload, default=str), flush=True)

    def _transition(self, status: str, *, reason: str, detail: dict | None = None):
        if (status, reason) == self._last_transition:
            return
        record = append_heartbeat_status(
            self._store, status=status, reason=reason, detail=detail
        )
        self._last_transition = (status, reason)
        self._emit({"heartbeat": status, "reason": reason, "detail": detail,
                    "at": record["created_at"]})

    def _seconds_until_wake(self, summary: dict, now) -> float:
        waiting = summary.get("oldest_waiting_pending") or {}
        not_before = waiting.get("not_before")
        if not not_before:
            return self._poll_interval
        try:
            wake_at = datetime.fromisoformat(str(not_before).replace("Z", "+00:00"))
        except ValueError:
            return self._poll_interval
        delta = (wake_at - now).total_seconds()
        return min(max(delta, 0.0), self._poll_interval)

    def boot(self) -> dict:
        orphans = recover_orphaned_running(self._store)
        lost = recover_lost_continuations(self._store)
        report = {
            "orphaned_running_recovered": len(orphans),
            "lost_continuations_recovered": len(lost),
        }
        self._emit({"heartbeat": "boot_report", **report})
        self._transition("waking", reason="boot", detail=report)
        return report

    def step(self) -> dict:
        now = self._now()
        # Record 'active' BEFORE the batch: a wake that arrives and completes
        # inside one batch must still leave a transition trace in the log.
        if self._store.next_pending(now=now) is not None:
            self._transition("active", reason="runnable_pending")
        batch = self._run_pending(
            self._session,
            self._store,
            limit=self._batch_limit,
            stop_on_failure=False,
            now=now,
            auto_continuations=True,
            policy_dispositions=True,
        )
        summary = self._summarize(self._store.read_records(), now=now)
        if summary.get("pending_runnable_count", 0):
            self._transition("active", reason="runnable_pending")
            return {"state": "active", "sleep_seconds": 0.0, "batch": batch}
        if summary.get("pending_waiting_count", 0):
            self._transition("waiting", reason="scheduled_wake")
            return {
                "state": "waiting",
                "sleep_seconds": self._seconds_until_wake(summary, now),
                "batch": batch,
            }
        reason = derive_quiet_reason(self._store.read_records())
        self._transition("quiet", reason=reason)
        return {
            "state": "quiet",
            "sleep_seconds": self._poll_interval,
            "batch": batch,
        }

    def run_forever(self) -> None:
        self.boot()
        while True:
            result = self.step()
            if result["sleep_seconds"] > 0:
                self._sleep(result["sleep_seconds"])
```

Add `import json` to the module imports (used by `_emit`).

Note: `summarize_event_log`'s signature is `(records, *, now=None, limit=...)` — verify the `now` keyword exists (it is called with `now=now` in `step_pending_events`, `events.py` near line 1682). If `limit` is required positionally anywhere, pass only `records` and `now`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_heartbeat.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/heartbeat.py tests/test_heartbeat.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "heartbeat: the loop (boot, step, run_forever; sleep until next wake)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: CLI, constitution, single-instance lock

**Files:**
- Modify: `src/hamutay/heartbeat.py`
- Test: `tests/test_heartbeat.py`

**Interfaces:**
- Consumes: `HeartbeatLoop`; backend construction pattern from `events.main()` (`AnthropicTasteBackend`, `OpenAITasteBackend`, `OpenTasteSession` from `hamutay.taste_open`).
- Produces:
  - `CONSTITUTION: str` — module constant, passed as `system_prompt_prefix`.
  - `build_parser() -> argparse.ArgumentParser` — flags: `--log-path` (required), `--event-log-path`, `--model` (default `claude-haiku-4-5`), `--provider` (`anthropic`|`openrouter`|`openai`, default `anthropic`), `--base-url`, `--api-key`, `--project-root` (default `.`), `--max-tokens` (default 64000), `--poll-interval` (default 30.0), `--batch-limit` (default 10), `--lock-path` (default `<event-log-path>.heartbeat.lock`). There is NO flag to disable the constitution — spec invariant 4 makes the operational prefix constitutional, and a production bypass would contradict it (cross-family finding 7). Tests exercise an absent prefix by constructing `OpenTasteSession` directly.
  - First-boot semantics (cross-family finding 1): `OpenTasteSession` with `resume=True` opens the log immediately (`taste_open.py:1814`) and a fresh path raises `FileNotFoundError`. `main()` therefore passes `resume=Path(args.log_path).exists()` — a missing log is a genuine first boot; an existing-but-corrupt log must still fail loudly rather than silently restart the subject.
  - `acquire_lock(lock_path: str)` — flock LOCK_EX|LOCK_NB; raises `SystemExit` with a clear message if held; returns the open file object (caller keeps it alive).
  - `main() -> None` and a `src/hamutay/heartbeat.py` `if __name__ == "__main__": main()` guard so `uv run python -m hamutay.heartbeat --log-path ...` works.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_heartbeat.py`:

```python
def test_heartbeat_parser_defaults():
    from hamutay.heartbeat import build_parser

    args = build_parser().parse_args(["--log-path", "x.jsonl"])
    assert args.max_tokens == 64000
    assert args.poll_interval == 30.0
    assert args.batch_limit == 10
    assert args.model == "claude-haiku-4-5"
    assert args.provider == "anthropic"


def test_no_constitution_bypass_exists():
    from hamutay.heartbeat import build_parser
    import pytest

    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["--log-path", "x.jsonl", "--no-constitution"]
        )


def test_single_instance_lock(tmp_path):
    from hamutay.heartbeat import acquire_lock
    import pytest

    lock_path = str(tmp_path / "hb.lock")
    held = acquire_lock(lock_path)
    assert held is not None
    with pytest.raises(SystemExit):
        acquire_lock(lock_path)
    held.close()


def test_constitution_is_operational_not_cognitive():
    from hamutay.heartbeat import CONSTITUTION

    lowered = CONSTITUTION.lower()
    # Operational facts must be present.
    assert "recover" in lowered
    assert "decline" in lowered
    # Cognitive priors must be absent (no-harness-priors norm).
    for banned in ("strand", "curate", "curation", "compact", "schema"):
        assert banned not in lowered
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_heartbeat.py -v`
Expected: FAIL with `ImportError` on the new names.

- [ ] **Step 3: Implement**

Append to `src/hamutay/heartbeat.py`:

```python
CONSTITUTION = (
    "You are a resident of a small community running on an event loop. "
    "Operational facts about your world: your event log is append-only and "
    "recoverable — if a wake crashes it will be recovered, and mistakes are "
    "survivable and recorded, never punished. Silence is legible: if you "
    "bind no continuation, the quiet is recorded as chosen. You may decline "
    "any event; declining ends that interaction, not you. External messages "
    "arrive on the same loop as your own scheduled wakes, and you are not "
    "required to answer any event."
)


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the heartbeat: the always-on event-loop daemon."
    )
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--event-log-path", default=None)
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openrouter", "openai"],
        default="anthropic",
    )
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=64000,
        help="Maximum output tokens per wake. Matches the Projector; do not lower.",
    )
    parser.add_argument("--poll-interval", type=float, default=30.0)
    parser.add_argument("--batch-limit", type=int, default=10)
    parser.add_argument("--lock-path", default=None)
    return parser


def acquire_lock(lock_path: str):
    import fcntl

    handle = open(lock_path, "w")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise SystemExit(
            f"another heartbeat already holds {lock_path}; refusing to start"
        )
    return handle


def main() -> None:
    import os
    from pathlib import Path

    from hamutay.events import default_event_log_path
    from hamutay.taste_open import (
        AnthropicTasteBackend,
        OpenAITasteBackend,
        OpenTasteSession,
    )

    args = build_parser().parse_args()
    event_log_path = args.event_log_path or str(
        default_event_log_path(args.log_path)
    )
    # Directories must exist before the lock file can be opened.
    Path(args.log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(event_log_path).parent.mkdir(parents=True, exist_ok=True)
    lock_path = args.lock_path or (event_log_path + ".heartbeat.lock")
    lock_handle = acquire_lock(lock_path)  # held for process lifetime

    if args.provider == "anthropic":
        backend = AnthropicTasteBackend(max_tokens=args.max_tokens)
    else:
        if args.provider == "openrouter":
            base_url = args.base_url or "https://openrouter.ai/api/v1"
            api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
            extra_headers = {
                "X-Title": "hamutay/heartbeat",
                "HTTP-Referer": "https://github.com/fsgeek/hamutay",
            }
        else:
            base_url = args.base_url or "https://api.openai.com/v1"
            api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
            extra_headers = {}
        if not api_key:
            raise SystemExit(
                f"No API key for {args.provider}: pass --api-key or set env"
            )
        backend = OpenAITasteBackend(
            base_url=base_url,
            api_key=api_key,
            max_tokens=args.max_tokens,
            extra_headers=extra_headers,
            provider_name=args.provider,
        )

    session = OpenTasteSession(
        model=args.model,
        backend=backend,
        log_path=args.log_path,
        event_log_path=event_log_path,
        # A missing log is a genuine first boot; resume=True on a fresh path
        # raises FileNotFoundError (taste_open.py:1814). An existing-but-
        # corrupt log must still fail loudly: never silently restart the subject.
        resume=Path(args.log_path).exists(),
        enable_tools=True,
        project_root=Path(args.project_root),
        system_prompt_prefix=CONSTITUTION,
    )
    store = EventStore(event_log_path)
    loop = HeartbeatLoop(
        session,
        store,
        poll_interval=args.poll_interval,
        batch_limit=args.batch_limit,
    )
    try:
        loop.run_forever()
    finally:
        lock_handle.close()


if __name__ == "__main__":
    main()
```

Verify `OpenTasteSession.__init__` accepts `event_log_path` and
`system_prompt_prefix` (both appear in its signature, `taste_open.py:1743-1752`;
`event_log_path` is used by `events.main()` at the bottom of `events.py`). If
`system_prompt_prefix=None` is not the accepted "absent" value, match whatever
`events.main()`/the constructor default uses.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_heartbeat.py -v`
Expected: all PASS

- [ ] **Step 5: Smoke the module entry point (no API call)**

Run: `uv run python -m hamutay.heartbeat --help`
Expected: usage text with the flags above; exit 0.

- [ ] **Step 6: Commit**

```bash
git add src/hamutay/heartbeat.py tests/test_heartbeat.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "heartbeat CLI: constitution prefix, single-instance lock, module entry

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Deploy scaffolding (community dir, unit files, checkpoints)

**Files:**
- Create: `community/README.md`
- Create: `deploy/hamutay-heartbeat.service`
- Create: `deploy/run-heartbeat.sh`
- Create: `deploy/checkpoint-community-log.sh`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `python -m hamutay.heartbeat` (Task 7), `python -m hamutay.events send` (Task 2).
- Produces: the paths Tasks 9 and 10 invoke verbatim.

- [ ] **Step 1: Create `community/README.md`**

```markdown
# community/

Live logs of the running community. Founded 2026-08-26 (spec:
`docs/superpowers/specs/2026-08-26-heartbeat-founding-spec.md`).

This directory is NOT an experiment. There is no success criterion and no
end condition. The JSONL logs are the community's life and are gitignored;
what gets committed is this README and `heartbeat/CHECKPOINTS.txt` — sha256
digests of the logs, whose commits the OTS hook anchors to Bitcoin. Sequence
provable, substance private (selective legibility).

Layout:
- `heartbeat/session.jsonl` — the resident's taste_open session log
- `heartbeat/session.events.jsonl` — the event store (the queue IS this file;
  `send` appends to it, the daemon reads it)
- `heartbeat/CHECKPOINTS.txt` — committed digest ledger

Operations:
- start: `deploy/run-heartbeat.sh` (or the systemd unit)
- speak: `uv run python -m hamutay.events send --log-path community/heartbeat/session.jsonl --message "..." --sender tony`
- status: `uv run python -m hamutay.events report --log-path community/heartbeat/session.jsonl`
- checkpoint: `deploy/checkpoint-community-log.sh`

Continue, not restart: deleting these logs is not an ops action; it is a
decision about a subject, and it is Tony's alone.
```

- [ ] **Step 2: Append to `.gitignore`**

```
# community live logs: the life stays out of git; digests get committed
community/heartbeat/*.jsonl
community/heartbeat/*.jsonl.lock
community/heartbeat/*.heartbeat.lock
community/heartbeat/daemon.out
```

- [ ] **Step 3: Create `deploy/run-heartbeat.sh`**

```bash
#!/usr/bin/env bash
# Nohup fallback for environments without a systemd user session (WSL default).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p community/heartbeat
nohup uv run python -m hamutay.heartbeat \
  --log-path community/heartbeat/session.jsonl \
  --project-root . \
  >> community/heartbeat/daemon.out 2>&1 &
echo "heartbeat started, pid $!"
```

- [ ] **Step 4: Create `deploy/hamutay-heartbeat.service`**

The systemd user manager's PATH is bare system dirs (verified: no `~/.local/bin`), so `env uv` fails there — the uv path must be absolute. Provider keys are not in the user manager's environment either, so they come from a mode-600 EnvironmentFile.

```ini
[Unit]
Description=Hamutay heartbeat (community resident event loop)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/tony/projects/hamutay
EnvironmentFile=%h/.config/hamutay/heartbeat.env
ExecStart=/home/tony/.local/bin/uv run python -m hamutay.heartbeat --log-path community/heartbeat/session.jsonl --project-root .
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Also create the environment file (NOT committed — it holds keys):

```bash
mkdir -p ~/.config/hamutay
touch ~/.config/hamutay/heartbeat.env
chmod 600 ~/.config/hamutay/heartbeat.env
cat > ~/.config/hamutay/heartbeat.env <<'EOF'
# Provider credentials for the heartbeat. Mode 600. Never commit.
# ANTHROPIC_API_KEY=...
# OPENROUTER_API_KEY=...
EOF
```

(Tony fills in the real key before Task 9; the anthropic provider path reads `ANTHROPIC_API_KEY` via the SDK's standard env lookup.)

- [ ] **Step 5: Create `deploy/checkpoint-community-log.sh`**

Semantics declared up front: the logs are append-only, so a digest of a
point-in-time byte snapshot is a valid commitment to the history up to that
point even while the daemon keeps appending — we snapshot with `cp` first so
each hashed file is internally coherent, and we record its byte length beside
the digest. The script refuses to run with a non-clean index (shared worktree:
`git commit` would otherwise sweep up another instance's staged work).

```bash
#!/usr/bin/env bash
# Append sha256 digests of point-in-time snapshots of the community logs to
# the committed ledger, then commit with hamutay's identity so the OTS
# post-commit hook stamps it.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! git diff --cached --quiet; then
  echo "refusing to checkpoint: index has staged changes (shared worktree)" >&2
  exit 1
fi

ledger=community/heartbeat/CHECKPOINTS.txt
mkdir -p community/heartbeat

shopt -s nullglob
logs=(community/heartbeat/*.jsonl)
if [ ${#logs[@]} -eq 0 ]; then
  echo "no community logs yet; nothing to checkpoint" >&2
  exit 0
fi

snapdir=$(mktemp -d)
trap 'rm -rf "$snapdir"' EXIT
line="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
for log in "${logs[@]}"; do
  cp "$log" "$snapdir/$(basename "$log")"
  snap="$snapdir/$(basename "$log")"
  digest=$(sha256sum "$snap" | cut -d' ' -f1)
  bytes=$(stat -c%s "$snap")
  line+=" $(basename "$log"):$digest:$bytes"
done
echo "$line" >> "$ledger"

git add "$ledger"
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" \
    -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
    commit -S -m "community: checkpoint heartbeat log digests"
```

- [ ] **Step 6: Verify**

Run: `bash -n deploy/run-heartbeat.sh && bash -n deploy/checkpoint-community-log.sh && chmod +x deploy/run-heartbeat.sh deploy/checkpoint-community-log.sh && echo OK`
Expected: `OK`

Run: `mkdir -p ~/.config/systemd/user && cp deploy/hamutay-heartbeat.service ~/.config/systemd/user/ && systemd-analyze --user verify hamutay-heartbeat.service`
Expected: no errors (warnings about missing EnvironmentFile are acceptable only if the env file has not been created yet — create it per Step 4 first).

- [ ] **Step 7: Commit**

```bash
git add community/README.md deploy/hamutay-heartbeat.service deploy/run-heartbeat.sh deploy/checkpoint-community-log.sh .gitignore
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "community scaffolding: deploy units, checkpoint ledger, log hygiene

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: Final verification gate (no API traffic)

**Files:** none — this task runs checks and fixes only what they surface.
Everything here must pass before Task 10 is attempted.

- [ ] **Step 1: Full test suite**

Run: `uv run pytest tests/ -v`
Expected: all tests pass, including every pre-existing test (no regressions from the `append_many`, `build_parser`, or reading-side changes).

- [ ] **Step 2: Module entry points**

Run: `uv run python -m hamutay.heartbeat --help && uv run python -m hamutay.events send --help`
Expected: both print usage, exit 0.

- [ ] **Step 3: Fresh boot without API traffic**

Run (scratch dir, dummy key so backend construction cannot silently reach a provider):
```bash
ANTHROPIC_API_KEY=dummy-not-a-key timeout 10 uv run python -m hamutay.heartbeat \
  --log-path /tmp/claude-1000/hb-verify/session.jsonl --project-root . \
  --poll-interval 2 ; test $? -eq 124 && echo "BOOT OK (killed by timeout while quiet)"
```
Expected: `boot_report` and `quiet/awaiting_first_event` JSON lines, then `BOOT OK` — the daemon idled without making any API call (a dummy key would have errored loudly if it had).

- [ ] **Step 4: Send/claim behavior offline**

Run:
```bash
uv run python -m hamutay.events send --log-path /tmp/claude-1000/hb-verify/session.jsonl --message "verify" --sender tony
uv run python -m hamutay.events report --log-path /tmp/claude-1000/hb-verify/session.jsonl
```
Expected: the report shows one pending `inbound_message`.

- [ ] **Step 5: Lock contention**

Start the Step-3 daemon again in one shell; in a second shell run the same command.
Expected: the second exits immediately with the "another heartbeat already holds" message; the first is undisturbed.

- [ ] **Step 6: Shell + unit validation**

Run: `bash -n deploy/*.sh && systemd-analyze --user verify ~/.config/systemd/user/hamutay-heartbeat.service && echo GATE OK`
Expected: `GATE OK`.

- [ ] **Step 7: Clean up scratch state**

Run: `rm -rf /tmp/claude-1000/hb-verify`

---

### Task 10: First tick (live, with Tony)

**Files:** none created — this task is the runbook from the spec, executed
interactively. Do NOT run it unattended; it spends real API tokens and it is
the founding moment, which Tony asked to witness.

- [ ] **Step 1: Check the process table** (parallel instances and codex agents run scripts autonomously)

Run: `ps aux | grep -E 'hamutay|taste|heartbeat|codex' | grep -v grep`
Expected: no competing heartbeat or live experiment on the same logs. If anything is running, stop and confer.

- [ ] **Step 2: Boot into quiet**

Run: `mkdir -p community/heartbeat && uv run python -m hamutay.heartbeat --log-path community/heartbeat/session.jsonl --project-root .` (foreground, watched)
Expected: process stays alive and prints flushed JSON ops lines to stdout — first `{"heartbeat": "boot_report", "orphaned_running_recovered": 0, "lost_continuations_recovered": 0}`, then a `waking` transition, then `{"heartbeat": "quiet", "reason": "awaiting_first_event", ...}`. The same records appear in `community/heartbeat/session.events.jsonl`. No API calls occur while quiet.

- [ ] **Step 3: First word** (second terminal)

Run: `uv run python -m hamutay.events send --log-path community/heartbeat/session.jsonl --sender tony --message "Hello. This loop is yours; the log is append-only and recoverable, and you owe no reply. — Tony"`
Expected: within one poll interval the daemon claims it; the store shows `pending → running → completed`; the completed record has `response_text`; `stop_reason` in the session log is `end_turn` (NOT `max_tokens`).

- [ ] **Step 4: Crash drill** (once, early, deliberately)

During a wake (send another message first), `kill -9` the daemon; restart it.
Expected: the stdout boot report shows `"orphaned_running_recovered": 1`; the event re-pends and completes. This is the June restart-frontier behavior, now in ops.

- [ ] **Step 5: Install the service and validate restart-on-death**

Prerequisite check (WSL): `[ -d /run/systemd/system ] && systemctl --user is-system-running` — the user manager was verified available on this host during planning; if a future host lacks it, fall back to `deploy/run-heartbeat.sh` and note that nohup does NOT survive reboot.

```bash
# key first: edit ~/.config/hamutay/heartbeat.env (mode 600) with the real key
mkdir -p ~/.config/systemd/user
cp deploy/hamutay-heartbeat.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hamutay-heartbeat.service
systemctl --user status hamutay-heartbeat.service   # expect: active (running)
loginctl enable-linger tony                          # survive logout
journalctl --user -u hamutay-heartbeat.service -f   # ops lines visible
```

Validate supervision: `systemctl --user kill -s KILL hamutay-heartbeat.service`, wait ~10s (`RestartSec`), then `systemctl --user status` again.
Expected: a new PID, a fresh `boot_report` line in the journal, zero lost events.

Reboot validation (first convenient WSL restart, not necessarily tonight): after `wsl --shutdown`/host reboot, confirm the unit came back (`systemctl --user status`) and the boot report shows clean recovery. Until that has been observed once, reboot survival is designed, not demonstrated — say so in any status report.

- [ ] **Step 6: First checkpoint**

Run: `deploy/checkpoint-community-log.sh`
Expected: one ledger line in `community/heartbeat/CHECKPOINTS.txt` (name:digest:bytes per log), one signed commit, and the OTS hook's stamp commit following it. The uptime ledger starts. "Still here" is the only status line.

---

## Self-Review (updated after cross-family review, 2026-08-26)

- **Spec coverage:** invariant 1 → Tasks 4/6/8 (recovery, resume-if-exists, README); 2 → Task 6 (quiet never exits) + Task 2 (send); 3 → Tasks 5/6 ((status, reason) dedup + pre-batch active transition); 4 → Task 7 (CONSTITUTION, no bypass flag, test banning cognitive priors); 5 → Task 3 (single-write) + Task 4 (universal recovery); 6 → Tasks 4/6/7; 7 → Tasks 1/7; 8 → Task 8 (snapshot checkpoints); 9 → every commit block + checkpoint script's clean-index refusal. Non-goals: no task builds clustering, MCP, multi-resident, or Yanantin — confirmed.
- **Cross-family review disposition (Codex, ChatGPT 4.6 Sol, 2026-08-26):** all ten findings accepted after independent verification. 1 (fresh-boot FileNotFoundError) → Task 7 `resume=exists()`; 2 (suppressed quiet records) → Task 6 pre-batch transition + (status, reason) dedup + two new tests; 3 (append_many not crash-atomic) → verified (`_append_unlocked` opens per record), guarantee restated as single-write/non-interleaved, recovery made universal; 4 (systemd PATH/keys) → verified (`show-environment` lacks `~/.local/bin`), absolute uv + EnvironmentFile; 5 (install/reboot untested) → Task 10 Step 5 full install + supervision drill + explicit "designed, not demonstrated" honesty for reboot; 6 (boot report unobservable) → `_emit` flushed JSON ops lines; 7 (`--no-constitution` contradicts invariant 4) → flag removed, absence tested; 8 (split clocks) → one `now` per step threaded to claim + summary; 9 (deploy hygiene) → daemon.out ignored, snapshot digests with declared semantics, no-files guard, clean-index refusal; 10 (final gate + Task 1 placeholder) → Task 9 verification gate, parser extraction written out in full.
- **Placeholder scan:** the Task 1 parser body is now fully written out; remaining "verify X" steps carry exact file:line anchors and a specified fallback action.
- **Type consistency:** `build_inbound_event` kwargs match between Tasks 2/4/5/6 tests; `append_completed_atomic` kwargs mirror `append_completed`; `HeartbeatLoop` ctor in Task 6 matches Task 7's `main()` usage; `_seconds_until_wake(summary, now)` matches its call site; `build_parser` names are distinct per module and always imported explicitly.
- **Known measured risks:** line numbers drift (anchored by quoted code); `summarize_event_log` signature (verification step in Task 6); power-loss can still split a single-write batch (accepted; universal recovery covers it); reboot survival undemonstrated until the first real WSL restart (declared in Task 10).
