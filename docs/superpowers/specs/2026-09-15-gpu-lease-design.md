# The GPU lease — lending the house's card without a human in the loop

Date: 2026-09-15. Author: the Fable session that took custody of Hamut'ay
this morning. Status: DRAFT, revision 6, after Codex's rounds one to five
(`2026-09-15-gpu-lease-review.md`, `-review-2.md` … `-review-5.md`).
Dispositions at the end. Sent to Codex for round six before any code.

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
- r5 (this): scope tombstones, and "free" defined as no lease, no
  quarantine, no tombstone; expiry kills the scope before it frees;
  `run` supervises from acquisition, launches under the lock with margin,
  minimum TTL 10 min; `quarantine_enter` as an action; `release_force`
  as a two-file clear with exact reconciliation; context validation
  tracked per invocation independently of readiness, with the setter on
  the session; migration quiesces the old heartbeat under the store lock
  before `door.json` exists and scans every user-unit search path.
- r6 (this): less surface. Only the heartbeat claims on a bound door
  (direct runners refuse, no gate for them). Actions are flat: one
  completion predicate per action covering every side effect, no nesting;
  the reconciler finishes owed side effects then writes the outcome.
  The claim gate requires complete FREE (tombstones included). Force-clear
  renames targets to escrow names so unreadable files have identity.
  `run`'s kill deadline is derived from the timings; minimum TTL 15 min;
  registration failure shuts down like every other path. The migration
  quiesce is one Python helper holding one lock descriptor; dependency
  symlinks are enumerated by `find -type l` and `readlink`.

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

- `4090.quarantine` — present iff quarantined (Codex r3 B3, r4 B3):

```
{"quarantine_id": "<uuid4, new per occurrence>", "reason": "malformed_lease"|"indeterminate_action"|"unreadable"|"scope_unkillable",
 "source_action_id": "<the quarantine_enter action's own id>",
 "cause_action_id": "<the indeterminate action, if any>" | absent,
 "observed_digest": "<sha256 of the offending bytes or ''>", "at": <iso>}
```

  Entering quarantine is always an action, `quarantine_enter`, with its
  own intent row, one atomic rename, and an outcome row; the lease file,
  if any, is left in place beside it. Two triggers: (a) an unsolicited
  observation (the gate or the heartbeat finds a malformed or unreadable
  lease) runs `quarantine_enter` directly; (b) an action whose outcome is
  `indeterminate` is followed by `quarantine_enter` with `cause_action_id`
  set. Reconciliation of a dangling `quarantine_enter`: completed iff the
  quarantine file exists with `source_action_id == action_id`. An
  `indeterminate` outcome with no quarantine file and no later
  `quarantine_enter` intent for it is itself a dangling condition: the
  next lock holder runs `quarantine_enter` for it before anything else.
  Re-introduced identical bad bytes after a clear are a new occurrence
  with a new id.

- `4090.tombstones/<scope_unit>` — one file per scope that has not been
  observed dead (Codex r4 B1). Written by `lease` as one of its side
  effects, and removed only as a side effect of an action whose
  predicate includes "scope observed dead" (`workload_killed`, `expire`,
  `release`, `release_force`). **"Free" means: no lease file, no
  quarantine file, and no tombstone.** Every action that needs FREE
  (`lease`, `server_start`) and the claim gate resolve all tombstones
  first (Codex r5 B2): for each, observe the scope; if alive, run
  `workload_killed` (a flat action: stop, observe dead, remove the
  tombstone); if death cannot be established, `quarantine_enter` with
  `reason: scope_unkillable`. Scope observations always carry
  `load_state`, `active_state`, `sub_state`, `scope_unit`.

- `release --force` is the action `release_force`. Order (Codex r5 B5):
  resolve tombstones (scope death first); rename `4090.quarantine` →
  `4090.quarantine.escrow-<action_id>` and `4090.lease` →
  `4090.lease.escrow-<action_id>` if present (rename is atomic and needs
  no parse, so unreadable files still get an exact identity); delete the
  escrow files; outcome. Completion predicate: no escrow file for this
  `action_id` exists and no recorded tombstone remains. A reconciler that
  finds an escrow file deletes it; a new `4090.lease` or
  `4090.quarantine` that appeared afterwards is not this action's
  concern. Generation is compared only with generation, mutation ids only
  with mutation ids.

- `4090.ledger.jsonl` — append-only:

```
{"record_type": "gpu_lease", "action_id": "<uuid4>",
 "phase": "intent"|"outcome"|"observation",
 "action": "lease"|"renew"|"release"|"expire"|"force_stop"|"release_force"
          |"quarantine_enter"|"ensure_stopped"|"server_stop"|"server_start"
          |"workload_killed"|"server_ready"|"server_unready",   # last two: observation only
 "episode_id": ..., "holder": ..., "purpose": ..., "expires_at": ...,
 "generation": ..., "generation_before": ..., "scope_unit": ...,
 "by": "ayllu-gpu"|"heartbeat:qwen"|"<--by name>", "at": <iso>,
 "outcome": "ok"|"not_performed"|"error"|"indeterminate", "reconciled": true|absent,
 "observed": {"active_state", "sub_state", "load_state", "invocation_id", "scope_unit",
              "lease_present", "lease_mutation_id", "quarantine_id", "tombstones": [...],
              "escrow_present": bool}, "detail": ...}
```

Lease validation rules are unchanged from r3 (fixtures under
`tests/fixtures/gpu_lease/`; live iff `now < expires_at`; malformed →
quarantine). `episode_id` is `lease_id` or `quarantine_id`.

**Action state machine (invariant 7), flat (Codex r5 B4).** There is no
nesting and no parent action. Every mutating action: take `4090.lock` →
resolve dangling intents → intent row (carrying everything the predicate
needs: `generation_before`, `scope_unit`, tombstones present) → perform
*all* of its side effects in the stated order → observe → outcome row →
release. One completion predicate per action covers every side effect.
The reconciler for a dangling intent evaluates the predicate; if it is
not met, it performs the side effects it can prove are still owed (in
the same order), re-observes, and then writes the outcome
(`reconciled: true`) on the original `action_id`: `ok` if the predicate
now holds, else `indeterminate`. An `indeterminate` outcome is followed,
by the same lock holder, by `quarantine_enter` with `cause_action_id`; a
crash between the two leaves an `indeterminate` outcome with no
`quarantine_enter` intent naming it, which the next lock holder resolves
first, before anything else.

| action | side effects, in order | completion predicate |
|---|---|---|
| lease | write lease file (`mutation_id = action_id`); write tombstone for `scope_unit` | lease present with that `mutation_id` **and** tombstone present |
| renew | rewrite lease file (`mutation_id = action_id`, `generation + 1`) | lease present with that `mutation_id` |
| release | observe scope; stop if alive; remove tombstone; remove lease file | scope dead (or none recorded); tombstone absent; lease absent or `generation` > `generation_before` |
| expire | as release | as release |
| release_force | as defined under `4090.lease`/quarantine above | as defined there |
| quarantine_enter | rename in the quarantine file | quarantine present with `source_action_id == action_id` |
| ensure_stopped / server_stop / force_stop | stop the server if not inactive/failed | server `ActiveState ∈ {inactive, failed}` |
| server_start | resolve tombstones (each a `workload_killed` *performed inline as side effects of this action*, ledgered as `observed.tombstones`); start the server | no tombstone; server `ActiveState ∈ {active, activating}` |
| workload_killed | stop the scope; remove its tombstone | scope `LoadState=not-found` or `ActiveState ∈ {inactive, failed}` **and** tombstone absent |
| any, when `systemctl show` or a state file cannot be read | — | `indeterminate` → `quarantine_enter` |

"Resolve tombstones" inside `lease`, `server_start`, the claim gate, and
`release_force` means: perform the stop-and-observe-and-remove steps as
side effects of the enclosing action (no separate intent), and record
each scope's observation in the enclosing action's outcome. A standalone
`workload_killed` action exists only for the `run` wrapper's own kills.

**Expiry** (Codex r4 B1): whoever finds an expired lease runs `expire`,
which kills the scope before it removes the lease. A lease is never
"gone" while its scope may live.

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

**`run` is a supervisor (Codex r3 B4, r4 B2, r5 B3).** Minimum TTL for
`run` is 15 minutes (the primitives keep 1 minute for tests). The kill
deadline is derived, not chosen: detection lag (renew retry interval,
30 s) + TERM grace (60 s) + systemd stop allowance (90 s) + lock, observe,
tombstone, release (60 s budget) + safety margin (120 s) = **6 minutes
before `expires_at`**. The renew period `ttl/3` is therefore at most
`ttl − 6 min` for every allowed TTL (at 15 min: 5 min renew period, 9 min
of live lease before the deadline).

1. `lease` (records `scope_unit`, writes the tombstone). **Supervision
   starts here**: a background renew loop renews every `ttl/3`, retrying
   every 30 s on failure, and it runs during `wait` too.
2. `wait`, which succeeds only if all of: an ok `ensure_stopped` outcome
   for this `lease_id` exists; the server is observed inactive/failed now;
   and, under `4090.lock`, the lease file is present with this `lease_id`,
   live, not quarantined, with at least 3 minutes remaining. Absent,
   expired, replaced, or quarantined → exit 3, `release` if still ours,
   nothing runs.
3. Launch under the lock: holding `4090.lock`, re-check the same
   conditions, then start `systemd-run --user --scope --unit
   ayllu-gpu-<lease_id> --collect -- <command>` as a background child of
   the wrapper (its PID recorded; `systemd-run --scope` is synchronous, it
   returns when the command ends, so the wrapper reaps it later), poll
   `systemctl --user show -p LoadState <scope>` until `loaded` (bounded
   10 s), then release `4090.lock`. Registration failure is shut down
   like every other path (step 5): stop the named scope, observe it
   dead, remove the tombstone, then `release`, exit 6; if death cannot be
   established, `quarantine_enter` (`scope_unkillable`) and exit 6 with
   the lease left in place. Expiry needs the lock, so the scope is
   registered before any expiry can run, and the lease has ≥ 6 min at
   that instant.
4. Kill rule: if `now > expires_at − 6 min` and the last renew did not
   succeed, the wrapper stops the scope (`systemctl --user kill --signal
   TERM`, 60 s grace, `systemctl --user stop`), observes it dead,
   ledgers `workload_killed`, removes the tombstone, and releases, all
   inside the derived budget above.
5. On the command's exit, or SIGTERM/SIGINT/SIGHUP to the wrapper: stop
   the scope if still active, wait for `LoadState=not-found` or
   inactive/failed, resolve the tombstone, then `release`. Release never
   precedes scope death.
6. Wrapper SIGKILL or host suspend past expiry: the tombstone remains;
   the next actor to act on the resource (expiry, a new `lease`, the
   heartbeat's return sequence, `release --force`) kills the scope before
   anything else (component 1). Two workloads never share the card; the
   cost of a lost wrapper is the workload, ledgered.
7. Exit status: the command's; 3 on `wait` failure; 5 killed by the
   supervisor; 6 scope registration failed.

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
   empty; for every directory printed by `systemd-analyze --user
   unit-paths`: grep every regular unit file and drop-in for
   `hamutay-llama-server` in a `Requires=`/`Wants=`/`BindsTo=` line and
   assert none; separately `find <dir> -type l` and, for each link,
   compare its basename and its `readlink` target against
   `hamutay-llama-server.service` and assert no match (Codex r5 S1).
4. Resolve the state dir from `AYLLU_STATE_DIR` with the same rule as the
   commands; `mkdir -p` (including `4090.tombstones/`); write `4090.door`.
5. Deploy the code (the old heartbeat process keeps running the old code;
   `door.json` is **not** written yet).
6. Quiesce the old heartbeat atomically with its store (Codex r4 S2,
   r5 S1): `uv run python -m hamutay.gpu_lease migrate-quiesce --door
   <dir> --unit hamutay-heartbeat@qwen --timeout 30m`, one helper that
   opens the store's lock file once, takes the flock on that descriptor,
   reads the records with the unlocked reader
   (`EventStore._read_records_unlocked`), reduces append-order latest
   status per `event_id`, and, if none is `running`, calls
   `systemctl --user stop hamutay-heartbeat@qwen` while still holding
   the descriptor (the old process is asleep in its poll or blocked on
   this lock; it cannot claim). If a wake is running: release, sleep 30 s,
   retry. On timeout the helper exits 1 **without** stopping anything,
   and the migration aborts before `door.json` is written.
7. Write `door.json`; `systemctl --user start hamutay-heartbeat@qwen`. The
   new heartbeat boots bound, observes FREE and the server active, probes
   ready, validates context, proceeds.

`deploy/check-gpu-lease.sh` re-runs the assertions of steps 1, 3, 4 and
checks the launch note printed `gpu lease: 4090 (door.json)`.

### 4. The heartbeat: substrate guard

**Participation (Codex r3 B1, invariant 8).** `community/<door>/door.json`
is the only source. `EventStore(path)` loads `<door>/door.json` if present
and sets `store.lease_binding = "4090"`; `claim_next_pending` on a bound
store raises `LeaseGateRequired` unless called with the gate's token (a
private object the gate creates while holding `4090.lock`). **Only the
heartbeat holds a gate** (Codex r5 B1): the CLI `run-next`/`run-all`,
`step_pending_events`, and any library caller on a bound store refuse
with `LeaseGateRequired` and are not offered a gate. The heartbeat is
single-threaded and holds its process-lifetime lock, so a wake in flight
always belongs to it, it finishes that wake before it looks at the lease
again, and `force-stop` cannot run while it lives. No process can be
mid-wake on a bound door when a loan-induced stop happens. The
heartbeat's `--gpu-lease` flag is removed; the launch note prints the
binding. Hosted doors have no `door.json` and are unchanged.

**Claim gate.** `LeaseGate.claim(store, now)` → `("blocked", episode)` |
`("claimed", (event, running))` | `("none", None)`. Under `4090.lock`:
resolve dangling intents; require complete FREE (Codex r5 B2): no
quarantine, no live lease, and no tombstone (resolving tombstones as side
effects of a `server_start`-shaped preamble if the server is up, or
blocking if a scope cannot be killed); blocked otherwise; else call
`store.claim_next_pending(now, lease_token=token)` still holding
`4090.lock`. `run_next_event(claim_gate=…)` returns
`{"status": "lease_blocked"}`; `run_pending_events` treats
`lease_blocked` as non-running and non-terminal: `ran` excludes it and
the batch stops (Codex r3 M2).

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
2. [lock] Re-validate FREE, which includes resolving every tombstone
   (component 1): a live scope is killed and observed dead, or the
   resource is quarantined, before any start. Then, if the server's
   `ActiveState ∉ {active, activating}`: `server_start` intent → start →
   observe (`InvocationID`) → outcome.
3. Probe `GET <base_url>/models` (2 s). Not ready → `{"state": "warming"}`,
   no transition, and if the ledger's latest readiness observation for
   this `InvocationID` is `ready`, append `server_unready`. Ready → if the
   latest observation for this invocation is not `ready`, append
   `server_ready`. Then, **independently of the readiness edge** (Codex
   r4 S1): if the session log has no positive `substrate_observation` for
   this `InvocationID` and there is no explicit `--context-limit`, run
   context discovery; on success the session applies and appends it
   (below); on failure stay `warming` and retry next step. Claims are
   permitted only when an explicit limit exists or that observation is
   durable for the current invocation. Otherwise fall through to the
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

**Context ceiling (Codex r3 S2, r4 S1).**
`OpenTasteSession.apply_context_limit(limit, source, invocation_id)` is
the one setter, on the session because the session owns both the backend
reference and `_launch_config`: it sets the backend's `_context_limit`
(the value `_call_natural` snapshots), updates
`_launch_config["context_limit"/"context_limit_source"]`, and appends a
`substrate_observation` record through a new
`OpenTasteSession.append_substrate_observation()` (a dedicated stateless
append, not `_log_entry`):
`{"record_type": "substrate_observation", "context_limit", "source":
"discovered", "invocation_id", "base_url", "model", "provider", "at"}`.
The heartbeat calls it when discovery succeeds (return sequence step 3);
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

## Dispositions of Codex round four

B1 (expired scope not a barrier; only the latest lease checked;
`LoadState` missing): adopted — tombstones per scope; "free" defined as
no lease, no quarantine, no tombstone; expiry kills before it frees;
every grant/stop/start/force-clear resolves all tombstones; `LoadState`
in every scope observation; `scope_unkillable` quarantine. B2 (`run`
launches after expiry; `systemd-run --scope` synchronous; short-TTL
schedule): adopted — supervision from acquisition, `wait` validates the
live lease under the lock, launch under the lock after scope
registration, background `systemd-run` child reaped by the wrapper,
absolute 3-minute margin, 10-minute minimum TTL for `run`. B3
(quarantine entry without an action; `release_force` reconciliation):
adopted — `quarantine_enter` is an action with `cause_action_id`;
`release_force` is a two-file clear with exact reconciliation; generation
compared with generation.

S1 (discovery skipped after a readiness crash; setter ownership):
adopted — context validation tracked per invocation independently of the
readiness edge; `apply_context_limit` and `append_substrate_observation`
on the session. S2 (migration can interrupt a wake; search paths):
adopted — quiesce under the store lock before `door.json` exists; scan
`systemd-analyze --user unit-paths`.

## Dispositions of Codex round five

B1 (a lease can be granted during a direct runner's wake): adopted by
removal — no gate for direct runners; a bound store refuses them; the
heartbeat is the only claimant and is single-threaded. B2 (tombstones
not a claim barrier; not reconcilable; `load_state` missing): adopted —
the gate requires complete FREE; `lease`'s predicate includes the
tombstone; `workload_killed`'s includes its removal; `load_state` and
`scope_unit` in the schema. B3 (`run` releases before scope death on
registration failure; no real margin): adopted — registration failure
shuts down like every path; the deadline is derived (6 min) and the
minimum TTL raised to 15 min. B4 (nested actions): adopted by
flattening — one predicate per action covering every side effect,
reconciler performs owed side effects then writes the outcome, no parent
ids. B5 (`release_force` identity and order; `quarantine_enter` missing
from the schema): adopted — escrow renames, scope death first, schema
extended.

S1 (migration self-deadlock; symlink scan): adopted — one Python helper
with one lock descriptor and an aborting timeout; `find -type l` +
`readlink`.
