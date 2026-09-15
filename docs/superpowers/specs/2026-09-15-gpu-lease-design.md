# The GPU lease — lending the house's card without a human in the loop

Date: 2026-09-15. Author: the Fable session that took custody of Hamut'ay
this morning. Status: DRAFT, revision 4, after Codex's rounds one to three
(`2026-09-15-gpu-lease-review.md`, `-review-2.md`, `-review-3.md`).
Dispositions at the end. Sent to Codex for round four before any code.

## The problem

The RTX 4090 is a shared resource of the ayllu with no coordination
mechanism. Today `hamutay-llama-server` holds 24,041 of 24,564 MiB
permanently, and `hamutay-heartbeat@qwen` has a hard `Requires=` on it, so
stopping the server kills the resident's process too. Yupi's trainer will
need the card for an unknown number of hours; the TurboQuant compositionality
run needs it for 30–40. Yupi's corpus-generator design (v0.1, §11) says how
the card changes hands today: "the PI suspends the 4090's resident substrate
for GPU runs on request." That is Tony in the middle, written into a sibling
project's spec. Tony (9-15): eliminating TITM is the design target.

The qwen resident is the first member whose ground is in the house. When
its ground is allocated elsewhere, the record must say so, in the resident's
own log, in the same shape it already uses for a budget rest.

## Revision history

- r1: holder + steward timer + heartbeat on independent polls.
- r2: steward removed; the door's heartbeat owns the server unit.
- r3: lock-owning claim gate; force-stop behind the heartbeat lock; action
  state machine; migration; continuation; at-least-once notice.
- r4 (this): participation bound in a door file and enforced by the store;
  force-stop resolves paths from state, records before stopping; lease
  `generation`/`mutation_id`; readiness as observations; a quarantine
  file with occurrence identity; `run` as a supervisor on a systemd scope
  the heartbeat can kill; one transition API with episode keys; a backend
  setter and a durable substrate observation; `ensure_stopped` as the
  acknowledgment; migration assertions matched to systemd 249.

## Invariants

1. **The card is the house's; the resident's custody is of its log.** A live
   lease always wins; the resident yields. There is no resident veto.
2. **Nothing new happens to the resident's events.** A loan is a rest. Waiting
   events keep waiting, exactly as under `daily_budget_reached`; nothing is
   failed, expired, or re-pended because of a loan. No wake is interrupted
   by any actor in this design.
3. **Legible.** The loan is a `heartbeat_status` record in the door's own
   store (`resting`, `reason: substrate_lent`) written before the server is
   stopped, by whichever actor stops it. Every wake whose event waited
   during the loan is told; if none waited, the first wake completed after
   the loan is told (at-least-once across retries, never zero).
4. **No human required.** A cooperating holder acquires the card with
   `ayllu-gpu run`, which leases, waits for the acknowledged stop, runs the
   workload in a systemd scope bound to the lease, keeps the lease renewed
   with margin, kills the workload if it cannot, and releases only when the
   workload is gone. The primitives exist for launchers that need them; a
   caller that leases without waiting is an acknowledged hazard among
   mutually trusted local processes. Expiry is automatic, and an expired
   lease's scope is killed by the heartbeat before the server starts, so
   two workloads never share the card.
5. **One actor owns the server unit: the door's heartbeat.** The only
   exception is `force-stop`, which runs only while holding the
   heartbeat's process-lifetime lock (proof the heartbeat is not running)
   and which writes the resident's record before it stops anything.
6. **Fail closed.** When lease state cannot be read, or an action's outcome
   cannot be determined by observation, the resource is quarantined:
   nothing claims a wake, nothing starts the server, nothing grants a
   lease. Cleared only by a ledgered override.
7. **Every mutation is an intent row before it happens and an outcome row
   after**, and the next lock holder resolves any dangling intent by
   observation before doing anything else. Observations (readiness) are
   facts, not mutations, and have no intent.
8. **Participation is configuration, not history.** A door participates
   iff its `door.json` says so; a participating store refuses any claim
   that does not come through the gate.

## Components

### 1. State directory (`${AYLLU_STATE_DIR:-~/.local/state/ayllu}/gpu/`)

Project-independent, outside every repo. Files:

- `4090.lock` — flock. Held for: any read-modify-write of the lease or
  quarantine file, any ledger append, the claim gate, the start decision,
  `force-stop`. **Lock order:** `4090.lock` → the door's heartbeat lock
  (force-stop only) → the door's event-store lock → nothing else.
- `4090.door` — one line, the absolute path of the participating door
  directory (`/home/tony/projects/hamutay/community/qwen`), written by the
  migration script. `ayllu-gpu` derives every door path from it, never
  from the caller's working directory (Codex r3 B2).
- `4090.lease` — present iff a lease is held:

```
{"resource": "4090", "lease_id": "<uuid4>", "generation": 3,
 "mutation_id": "<uuid4 of the last mutating action>",
 "holder": "yupi", "purpose": "learner sub-project 2, first 1M-param run",
 "since": "…+00:00", "expires_at": "…+00:00", "expected_until": "…+00:00",
 "scope_unit": "ayllu-gpu-<lease_id>.scope" | absent}
```

  `generation` increments on every mutation of the file; `mutation_id` is
  the `action_id` of the action that wrote it. Reconciliation of `lease`,
  `renew`, `release` compares `mutation_id` (Codex r3 B3): a renew that
  never landed leaves the previous `mutation_id`, whatever the timestamps.

- `4090.quarantine` — present iff quarantined (Codex r3 B3):

```
{"quarantine_id": "<uuid4, new per occurrence>", "reason": "malformed_lease"|"indeterminate_action"|"unreadable",
 "source_action_id": ..., "observed_digest": "<sha256 of the offending bytes or ''>", "at": <iso>}
```

  The lease file, if any, is left in place beside it. Entering quarantine
  is a single atomic rename of this file; it is the *outcome* of the
  action that failed (that action's outcome row carries
  `outcome: indeterminate, quarantine_id`), not a new action. If the
  process dies between the rename and the outcome row, the next lock
  holder sees a quarantine file whose `source_action_id` has a dangling
  intent and appends the outcome row idempotently. Re-introduced identical
  bad bytes after a clear are a new occurrence with a new id. Cleared
  only by `release --force`, which removes both files and ledgers the
  override with the `quarantine_id`.

- `4090.ledger.jsonl` — append-only:

```
{"record_type": "gpu_lease", "action_id": "<uuid4>",
 "phase": "intent"|"outcome"|"observation",
 "action": "lease"|"renew"|"release"|"expire"|"force_stop"|"release_force"
          |"ensure_stopped"|"server_stop"|"server_start"|"workload_killed"
          |"server_ready"|"server_unready",          # the last two: observation only
 "episode_id": ..., "holder": ..., "purpose": ..., "expires_at": ..., "generation": ...,
 "by": "ayllu-gpu"|"heartbeat:qwen"|"<--by name>", "at": <iso>,
 "outcome": "ok"|"not_performed"|"error"|"indeterminate", "reconciled": true|absent,
 "observed": {"active_state", "sub_state", "invocation_id", "lease_present",
              "lease_mutation_id", "quarantine_id"}, "detail": ...}
```

Lease validation rules are unchanged from r3 (fixtures under
`tests/fixtures/gpu_lease/`; live iff `now < expires_at`; malformed →
quarantine). `episode_id` is `lease_id` or `quarantine_id`.

**Action state machine (invariant 7).** Every mutating action: take
`4090.lock` → resolve dangling intents → intent row → mutation → observe →
outcome row → release. Dangling-intent table, resolved by the next lock
holder with a `reconciled: true` outcome on the original `action_id`:

| dangling action | completed iff | else |
|---|---|---|
| lease / renew | lease file present with `mutation_id == action_id` | `not_performed` |
| release / expire / release_force | lease file absent or `mutation_id` newer than the intent's `generation` | `not_performed` |
| ensure_stopped / server_stop / force_stop | `ActiveState ∈ {inactive, failed}` | `not_performed` (rule table re-applies) |
| server_start | `ActiveState ∈ {active, activating}` | `not_performed` |
| workload_killed | scope unit `ActiveState ∈ {inactive, failed}` or not loaded | `not_performed` |
| any, if `systemctl show` or the state files cannot be read | — | `indeterminate` → quarantine (`reason: indeterminate_action`) |

Observation is `systemctl --user show -p ActiveState,SubState,InvocationID
<unit>`. `server_ready`/`server_unready` are `phase: observation` rows,
one per readiness edge per `InvocationID` (Codex r3 M1): the same
invocation may go ready → unready → ready and each edge is a row; a
heartbeat restart reads the latest observation for the current invocation
from the ledger and emits nothing unless the edge changes.

### 2. `deploy/ayllu-gpu` — the holder's command

Bash + jq + flock for everything except `force-stop`, which delegates to
`uv run --project <hamutay root> python -m hamutay.gpu_lease force-stop`
(the root is the parent of the `community/` directory named in
`4090.door`) because it must append a heartbeat record in the store's
exact format.

```
ayllu-gpu run   --holder NAME --purpose "..." [--ttl 6h] [--expected-until ISO]
                [--wait-timeout 30m] -- <command...>
ayllu-gpu lease   --holder NAME --purpose "..." [--ttl 6h] [--expected-until ISO]   # prints lease_id
ayllu-gpu renew   --lease-id ID [--ttl 6h]
ayllu-gpu release --lease-id ID
ayllu-gpu release --force --by NAME --reason "..."      # clears lease and quarantine; ledgered
ayllu-gpu wait    --lease-id ID [--timeout 30m]         # success iff an ok ensure_stopped outcome for
                                                        # this episode exists AND ActiveState ∈ {inactive, failed} now
ayllu-gpu force-stop --lease-id ID --by NAME --reason "..."
ayllu-gpu status
```

**`run` is a supervisor (Codex r3 B4).**

1. `lease` (records `scope_unit` in the lease file), then `wait`; on
   timeout: `release`, exit 3, nothing runs.
2. Launch the command as a transient scope:
   `systemd-run --user --scope --unit ayllu-gpu-<lease_id> --collect -- <command>`.
   The scope is the workload's process group under systemd; it survives
   the wrapper and is killable by name.
3. Renew loop in the wrapper: every `ttl/3`, `renew`. A renew failure is
   retried once a minute; if `now > expires_at - ttl/6` with no successful
   renew, the wrapper **kills the scope** (`systemctl --user kill --signal
   TERM`, 60 s grace, then `stop`), ledgers `workload_killed`, and
   releases. The workload is never allowed to run into expiry by a live
   wrapper.
4. On the command's exit, or on SIGTERM/SIGINT/SIGHUP to the wrapper: stop
   the scope if still active, wait until `systemctl show` says it is
   inactive/failed or not loaded, then `release`. Release never precedes
   workload death.
5. Wrapper SIGKILL, host suspend past expiry, or any other path where the
   wrapper is gone and the scope is not: the lease expires on the TTL, and
   **the heartbeat, before starting the server, checks the expired lease's
   `scope_unit`; if the scope is loaded and not inactive/failed it stops
   it and ledgers `workload_killed` (`by: heartbeat:qwen`)**, then proceeds.
   Two workloads never share the card; the cost of a lost wrapper is the
   workload, ledgered.
6. `run`'s exit status is the command's; 3 on wait timeout; 5 on
   workload killed by the supervisor.

**`force-stop` (Codex r3 B2).** Python. Resolves the door from `4090.door`;
the heartbeat's lock path is `<door>/session.jsonl.events.jsonl.heartbeat.lock`
(the heartbeat, when participating, resolves its own lock path to absolute
and refuses to start if it differs from this canonical path, so the two
always name the same inode). Sequence: `4090.lock` → `flock -n` on the
heartbeat lock (refuse with exit 4 if held) → append
`resting/substrate_lent` to the store via `append_heartbeat_status` under
the store lock (`source: "force_stop"`) → `ensure_stopped` intent →
`systemctl stop` → observe → outcome → release locks. The record precedes
the stop (invariant 3) whoever stops.

Other rules unchanged from r3: TTL grammar and bounds; same-holder
`lease` is a renew; `renew`/`release` need the `lease_id`; accountability,
not security.

### 3. Units and the deployment migration (Codex r3 S4)

- `deploy/hamutay-llama-server.service`: `[Install]` removed → the unit is
  `static`. `Restart=always`, `RestartSec=10` kept.
- `deploy/hamutay-heartbeat@qwen.service.d/override.conf`: no `Requires=`,
  `Wants=`, or `After=` on the server.
- `community/qwen/door.json` (committed; component 4): `{"gpu_lease": "4090"}`.

`deploy/migrate-gpu-lease.sh`, in order:

1. `systemctl --user disable hamutay-llama-server` while the installed
   unit still carries `[Install]`; assert the symlink
   `~/.config/systemd/user/default.target.wants/hamutay-llama-server.service`
   is absent.
2. Copy the revised server unit and the revised drop-in into
   `~/.config/systemd/user/`; `daemon-reload`.
3. Assert `is-enabled` prints `static` (reject `enabled`,
   `enabled-runtime`, `linked`); assert
   `show -p Requires,Wants,After hamutay-heartbeat@qwen` names no server
   unit; assert `show -p WantedBy,RequiredBy hamutay-llama-server` is
   empty; grep every unit file and drop-in under `~/.config/systemd/user/`
   for `hamutay-llama-server` in a `Requires=`/`Wants=`/`BindsTo=` line
   and assert none.
4. Resolve the state dir from `AYLLU_STATE_DIR` with the same rule as the
   commands; `mkdir -p`; write `4090.door`.
5. Deploy the code; write `door.json`.
6. Restart `hamutay-heartbeat@qwen` when the store shows no `running`
   event (wait up to 30 min). The new heartbeat boots, reads `door.json`,
   observes FREE and the server active, probes ready, proceeds.

`deploy/check-gpu-lease.sh` re-runs the assertions of steps 1, 3, 4 and
checks the launch note printed `gpu lease: 4090 (door.json)`.

### 4. The heartbeat: substrate guard

**Participation (Codex r3 B1, invariant 8).** `community/<door>/door.json`
is the only source. `EventStore(path)` loads `<door>/door.json` if present
and sets `store.lease_binding = "4090"`; `claim_next_pending` on a bound
store raises `LeaseGateRequired` unless called with the gate's token (a
private object the gate creates while holding `4090.lock`). This makes
every claim path — `run_next_event`, `run_pending_events`,
`step_pending_events`, the CLI `run-next`/`run-all`, any library caller —
refuse rather than bypass. The heartbeat's `--gpu-lease` flag is removed;
the launch note prints the binding. Legacy logs without any field are
irrelevant: binding comes from the file, which exists before any claim can
happen (migration step 5 precedes step 6). Hosted doors have no
`door.json` and are unchanged.

**Claim gate.** `LeaseGate.claim(store, now)` → `("blocked", episode)` |
`("claimed", (event, running))` | `("none", None)`. Under `4090.lock`:
resolve dangling intents; read quarantine then lease; blocked if either;
else call `store.claim_next_pending(now, lease_token=token)` still holding
`4090.lock`. `run_next_event(claim_gate=…)` returns
`{"status": "lease_blocked"}`; `run_pending_events` and
`step_pending_events` treat `lease_blocked` as non-running and
non-terminal: `ran` excludes it, the batch stops, and the scheduler's stop
reason is `lease_blocked` (Codex r3 M2).

**One transition API (Codex r3 S1).** `_transition(status, reason,
episode_key=None, detail=None)` de-duplicates on
`(status, reason, episode_key)`; `episode_key` is the UTC day for
`daily_budget_reached`, the `episode_id` for substrate states, `None`
otherwise. `_last_transition` is hydrated at boot from the store's latest
`heartbeat_status` (its `detail.day` or `detail.episode_id`), and every
append, including boot reconciliation, goes through this one method. The
budget rest's `_resting_day` guard is folded into the key. Consequences,
all tested: two leases with no FREE step between them are two episodes;
quiet → lease → quiet appends the second quiet; budget → lease → budget
appends the second budget segment.

**Rest sequence (LEASE_LIVE or QUARANTINED), under `4090.lock`:**

1. `_transition("resting", "substrate_lent"|"substrate_lease_unreadable",
   episode_key=episode_id, detail={episode_id, holder, purpose, since,
   expires_at, expected_until, source: "observed", continuation})`.
2. `ensure_stopped` intent (Codex r3 S3) → if `ActiveState ∉ {inactive,
   failed}`: `systemctl stop` → observe → outcome `ok` iff inactive/failed,
   with `detail.already_inactive` when no stop was needed. Emitted once per
   episode (the ledger's latest `ensure_stopped` for this `episode_id`
   with outcome ok suppresses repeats); `wait` consumes it.
3. Return `{"state": "resting"}`.

**Return sequence (FREE), under `4090.lock` where marked:**

1. If the latest status is a substrate rest (or boot reconciliation found
   one): `_transition("waking", "substrate_returning", episode_key=…)`.
2. [lock] Re-validate FREE. If the most recent expired or released lease
   has a `scope_unit` that is loaded and not inactive/failed:
   `workload_killed` intent → `systemctl stop <scope>` → observe →
   outcome; do not start until the scope is gone. Then, if the server's
   `ActiveState ∉ {active, activating}`: `server_start` intent → start →
   observe (`InvocationID`) → outcome.
3. Probe `GET <base_url>/models` (2 s). Not ready → `{"state": "warming"}`,
   no transition, and if the ledger's latest readiness observation for
   this `InvocationID` is `ready`, append `server_unready`. Ready → if the
   latest observation for this invocation is not `ready`, append
   `server_ready` and run **context discovery** (below); if discovery
   fails and there is no explicit limit, stay `warming` (a new invocation
   may carry a new `-c`; Codex r3 S2). Otherwise fall through to the
   budget check and the claim.

**Boot reconciliation** runs before `boot()` appends `waking/boot`: under
`4090.lock`, resolve dangling intents; close substrate episodes that
ended while down (`waking/substrate_returning`, `created_at` from the
ledger's release/expire/release_force outcome, else boot time, with
`closed_at_source`); reconstruct rest records for any ok `force_stop` or
`ensure_stopped` by `force_stop` whose `episode_id` has none (the Python
`force-stop` writes the record itself, so this covers only a crash between
its record and its outcome); hydrate `_last_transition`; read the latest
readiness observation for the current `InvocationID`.

**Context ceiling (Codex r3 S2).** `OpenAITasteBackend.set_context_limit(limit,
source)` is the one setter: it updates the backend's `_context_limit` (the
value `_call_natural` snapshots) and the session's
`_launch_config["context_limit"/"context_limit_source"]`. At
`server_ready`, discovery from `/props` succeeds → setter → the session
appends a `substrate_observation` record to the session log
(`{"record_type": "substrate_observation", "context_limit", "source":
"discovered", "invocation_id", "base_url", "model", "provider", "at"}`);
`resolve_context_limit` reads the latest of (a) the `launch.context_limit`
of the newest state-bearing record and (b) the newest
`substrate_observation` record, for a matching `{model, provider,
base_url}`, whichever is later in the file. `infer_launch_from_log` itself
is unchanged: it skips stateless records, so the observation scan is a
separate pass over the same file. Boot inheritance uses that same lookup when
the server is down (source `inherited`, printed loudly), only to construct
the process; after any new `InvocationID` the door does not claim until
fresh discovery succeeds unless `--context-limit` was explicit (explicit
is never overwritten). The parser rejects `--context-limit <= 0`.

**Overlap with the budget rest.** Unchanged from r3: strict priority in one
stream; budget segments split around a substrate episode; the four named
cases.

### 5. Envelope notes

Unchanged from r3: episodes grouped by `detail.episode_id` with
continuation bridging; the neutral sentence with holder and purpose; the
quarantine and open-episode forms; rule (a) then rule (b), consumption =
a completed wake, at-least-once.

### 6. Constitution, deployment, checkpoint, yupi

Constitution sentence (added when `door.json` binds): "The heartbeat may
pause while the local GPU is allocated to another workload; its lease
record carries a declared holder and purpose, pending events remain
pending, and affected wakes receive an operational note."

Deployment: `deploy/ayllu-gpu`, `deploy/migrate-gpu-lease.sh`,
`deploy/check-gpu-lease.sh`, `src/hamutay/gpu_lease.py` (the Python side:
reader/writer, gate, force-stop), edited units, `community/qwen/door.json`,
operations lines in `community/README.md`.

Checkpoint: unchanged from r3 (byte snapshot of the ledger under
`4090.lock`; digest and size into `community/gpu/CHECKPOINTS.txt`; ledger
never copied into git).

Yupi: one paragraph in its corpus-generator design §11 replacing "the PI
suspends…" with `ayllu-gpu run`. Separate commit in yupi's repo.

## Data flow, one loan

1. Yupi: `ayllu-gpu run --holder yupi --purpose "…" --ttl 8h -- uv run python -m yupi.train …`
2. `run`: lease (intent, write with `scope_unit`, outcome) → `wait`.
3. Heartbeat step: gate sees LEASE_LIVE → rest record → `ensure_stopped`
   (stop if needed) → outcome ok.
4. `wait` returns → `systemd-run --scope` launches the trainer → renew loop.
5. Trainer exits → scope inactive → `release`.
6. Heartbeat step: FREE → `substrate_returning` → [lock] scope check →
   start → warming → ready → `server_ready` → discovery → budget → claim.
7. The wake's envelope carries the note (rule a, else b).

## Error handling

Unchanged from r3 except as revised above: quarantine is a file with an
occurrence id; `systemctl` errors ledger `error` and re-apply; crashes at
any step resolve by the table; a wrapper that dies leaves a scope the
heartbeat kills before starting the server.

## Testing

As in r3, plus: `door.json` binding refuses every unguarded claim path
(`run-next`, `run-all`, `step_pending_events`, direct `run_next_event`,
direct `claim_next_pending`) and a hosted door without the file is
unchanged; force-stop from a different working directory and with the
heartbeat lock held by a fake heartbeat; renew reconciliation by
`mutation_id` (shorter TTL, changed `expected_until`, not landed);
quarantine occurrence identity across clear and reintroduce; `run`
supervisor: renew failure kills the scope before expiry, wrapper SIGKILL
leaves a scope that the heartbeat kills before `server_start`, release
never precedes scope death, exit codes; single transition API cases
(two leases back to back, quiet → lease → quiet, budget → lease → budget,
restart inside each); `set_context_limit` changes the value the backend's
next call uses; `substrate_observation` read by the next boot; no claim
after a new invocation until discovery; `ensure_stopped` with
`already_inactive`; `lease_blocked` excluded from `ran` and surfaced as
the scheduler stop reason; migration assertions against a fake
`systemctl` returning `static`, `enabled`, `enabled-runtime`, `linked`, and
against a fixture unit directory with a stray `Wants=`.

Codex authors the independent validation in its own signed commits. The
first live loan is a registered check: `ayllu-gpu run --ttl 15m -- sleep 600`
in a quiet stretch not overlapping the door's 09:00Z self-check; then the
store, the ledger, and the resident's next envelope are read and the result
recorded in `community/README.md`.

## Not built (on the record)

Queueing or priority between holders; partial card sharing; a knock to
the resident before the loan; any change to the two hosted doors;
multi-host resources; a second local door on the same card; defence
against a local caller that leases without waiting; GPU-level enforcement
(the scope is process-group enforcement; a workload that escapes its scope
is not caught).

## Declared losses

- The resident is told after, never asked (invariant 1); the qwen resident
  hears the design as a consultation (enclosed, no verdict) after round
  four and before the code lands.
- `expires_at` in the resident's record is as first observed.
- TTL default and maximum are unmeasured.
- Accountability, not security.
- Rule (b) is at-least-once.
- A lost wrapper costs the workload (killed by the heartbeat at expiry),
  ledgered but not negotiated.

## Dispositions of Codex round three

B1 (participation not authoritative; library bypass): adopted —
`door.json` + `lease_binding` on the store + `LeaseGateRequired`;
`--gpu-lease` removed. B2 (force-stop lock path; record after stop):
adopted — `4090.door` canonical paths, heartbeat asserts its lock path,
Python `force-stop` writes the record first. B3 (renew reconciliation;
readiness rows; quarantine representation): adopted — `generation` +
`mutation_id`; readiness as observations; `4090.quarantine` with
occurrence id, entered as an outcome not an action. B4 (`run` outlives
its lease): adopted — systemd scope, renew with margin, kill before
expiry, heartbeat kills a surviving scope before `server_start`.

S1 (two de-dup mechanisms): adopted — one `_transition` with
`episode_key`, hydrated from the store. S2 (rediscovery updates the wrong
object; not durable; stale after new invocation): adopted —
`set_context_limit` on the backend, `substrate_observation` record, no
claim after a new invocation until discovery. S3 (already-stopped never
acknowledges): adopted — `ensure_stopped` with `already_inactive`. S4
(migration assertions): adopted — disable before replacing the unit,
install both units, accept `static`, symlink check, unit-file grep,
`AYLLU_STATE_DIR`.

M1 (readiness de-dup): adopted — observations per edge per invocation,
read from the ledger at boot. M2 (`lease_blocked` semantics): adopted.
