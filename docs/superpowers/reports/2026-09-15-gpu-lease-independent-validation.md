# GPU lease independent validation

Date: 2026-09-15

Role: independent black-box validator. The implementation and its tests were not modified.

## Independence record

Before the validation suite was frozen, I read only:

- `CLAUDE.md`.
- `docs/superpowers/specs/2026-09-15-gpu-lease-design.md`, revision 7, including the "Implementation notes (2026-09-15)" section.
- The six adjacent review files: `2026-09-15-gpu-lease-review.md` through `2026-09-15-gpu-lease-review-6.md`.
- The public declarations reported by `grep -n "^def \|^class \|^    def " src/hamutay/gpu_lease/*.py` and their docstrings only.
- `tests/gpu_lease/conftest.py`, solely for the `FakeSystemd` fixture shape.

I did not read implementation bodies, heartbeat guard code, or the implementer's GPU lease tests before freeze. The suite was frozen before its first execution in signed commit `d2b63ff` (`validation: Codex's independent black-box tests for the GPU lease (frozen before first run)`).

All validation cases use temporary state directories and fake clocks/systemd. They do not invoke real `systemctl` or `systemd-run`, and do not touch the community tree or user configuration.

## Runs

The prescribed command was used throughout:

```text
uv run pytest tests/gpu_lease_validation -q -W error
```

Results:

| Suite state | Passed | Failed | Total |
| --- | ---: | ---: | ---: |
| Frozen commit `d2b63ff`, first execution | 4 | 55 | 59 |
| After correction `3e0f45e` | 44 | 15 | 59 |
| After correction `aa5bd8d` | 47 | 16 | 63 |
| After correction `35b45a5` | 48 | 15 | 63 |
| After correction `2d15c1e`, final suite | 49 | 14 | 63 |

The increase to 63 cases came from splitting parameterized surfaces so that the exact guarded runners and launch boundary were independently exercised. The final 14 failures consistently reduce to the five implementation defects below; all other invariants, including the migration-script cases, pass against the unmodified implementation.

## Implementation defects

### 1. A malformed lease blocks a claim but does not enter quarantine

`LeaseGate.claim` reads the malformed lease through `_free_info` and returns `blocked` without running the quarantine-enter action (`src/hamutay/gpu_lease/gate.py:84`, particularly lines 98-103). The black-box assertion is `tests/gpu_lease_validation/test_fail_closed.py:41`.

This violates fail-closed invariant 6: malformed durable state must produce a quarantine file, not merely decline the current claim. Without the quarantine transition, the condition is not durably fenced or ledgered.

### 2. An indeterminate systemd action is not immediately quarantined

The common action runner converts `SystemdUnavailable` into an `indeterminate` outcome and returns it, but does not enter quarantine (`src/hamutay/gpu_lease/actions.py:98`, particularly lines 110-117). The seven failing cases are `ensure_stopped`, `server_stop`, `force_stop`, `server_start`, `workload_killed`, `release`, and `expire`, asserted at `tests/gpu_lease_validation/test_fail_closed.py:88-93`.

This violates fail-closed invariant 6 and the same-lock-holder requirement in invariant 7. Every action that cannot establish systemd truth must record `indeterminate` and immediately write a causally linked `quarantine_enter`, before releasing the lock.

### 3. Batch runners turn a missing participation gate into an ordinary failed result

`run_pending_events` catches every exception from `run_next_event`, including `LeaseGateRequired`, and returns a result whose status is `failed` (`src/hamutay/events.py:2138`, particularly lines 2148-2157). The scheduler surface follows that behavior, and CLI `run-all` prints the result and exits successfully (`src/hamutay/events.py:2462-2471`). The failing library assertions are at `tests/gpu_lease_validation/test_participation_lock_and_wake.py:66`; the CLI assertion is at lines 95-96.

This violates invariant 8, participation is configuration. A store bound by `door.json` must refuse every unguarded claim surface. Converting the configuration refusal into event failure is especially harmful because it misclassifies the event and lets `run-all` report process success.

### 4. The heartbeat stops the server before an already-running wake completes

The guard observes a live lease and calls `ensure_stopped` immediately (`src/hamutay/heartbeat.py:496`, particularly lines 501-523). `HeartbeatLoop.step` invokes that guard and returns before its injected `run_pending` can advance the running event (`src/hamutay/heartbeat.py:536-543`). The failing assertion is `tests/gpu_lease_validation/test_participation_lock_and_wake.py:185`.

This violates invariant 2, no interrupted wake. A wake already recorded as `running` must be allowed to reach completion before the server is stopped for a newly observed live lease.

### 5. Dangling `server_stop` intents have no reconciler

The action registry omits `server_stop` (`src/hamutay/gpu_lease/actions.py:594-604`). Consequently, `resolve_dangling` takes its unknown-action branch and writes `indeterminate` (`src/hamutay/gpu_lease/actions.py:132-136`), regardless of whether the stop side effect occurred. The before/after boundary assertions fail at `tests/gpu_lease_validation/test_reconciliation.py:202`.

This violates invariant 7, every mutation is reconcilable. A crash before or after the systemd stop boundary must resolve by the action's completion predicate rather than becoming an unsupported action.

## Corrections to the validation suite

- `3e0f45e` — corrected frozen-suite assumptions about public API shapes: `Paths` members are properties, `Ctx` exposes `paths`, envelope helpers require `now`, the heartbeat constructor has an exact injected-interface shape, and migration scripts expose explicit fake-command/unit-directory flags. These were harness errors, not product failures.
- `aa5bd8d` — exercised the exact guarded library and CLI runner surfaces, placed the fake clock precisely at the six-minute launch boundary, drove the heartbeat record-before-stop path, closed subprocess pipes, made the interruption fixture model an active server, and used the production registry for reconciliation. This removed accidental masking and made each assertion correspond to the specified public boundary.
- `35b45a5` — corrected the quarantine observation tuple expectation and supplied the CLI session fixture required by the public runner. These failures occurred before the invariant under test was reached.
- `2d15c1e` — seeded the CLI session log with the minimal state-bearing record required to resume a session. This allowed the CLI participation test to reach the lease-gate boundary rather than fail during unrelated session loading.

defects found
