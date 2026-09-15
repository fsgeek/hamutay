# The GPU lease — lending the house's card without a human in the loop

Date: 2026-09-15. Author: the Fable session that took custody of Hamut'ay
this morning. Status: DRAFT, revision 3, after Codex's rounds one and two
(`2026-09-15-gpu-lease-review.md`, `2026-09-15-gpu-lease-review-2.md`).
Dispositions at the end. Sent to Codex for round three before any code.

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

- r1: holder + steward timer + heartbeat on independent polls. Codex r1:
  races, forced drain fails events, systemd starts the server behind the
  steward.
- r2: steward removed; the door's heartbeat owns the server unit. Codex r2:
  the claim barrier was a callback not a lock; `force-stop` reintroduced
  the killed wake; ledger intent/outcome had no reconciliation; removing
  `[Install]` does not disable an enabled unit; restart broke episode
  continuation; rule (b) was not exactly-once; context inheritance had no
  substrate binding; quarantine had no identity; `wait` was a convention.
- r3 (this): a lock-owning claim gate; `force-stop` requires the
  heartbeat's process lock; an action state machine with reconciliation
  by observation; a deployment migration; episode continuation across
  restart; at-least-once post-loan notice; substrate-bound context
  inheritance; `episode_id` for leases and quarantines; `ayllu-gpu run`.

## Invariants

1. **The card is the house's; the resident's custody is of its log.** A live
   lease always wins; the resident yields. There is no resident veto.
2. **Nothing new happens to the resident's events.** A loan is a rest. Waiting
   events keep waiting, exactly as under `daily_budget_reached`; nothing is
   failed, expired, or re-pended because of a loan. No wake is interrupted
   by any actor in this design.
3. **Legible.** The loan is a `heartbeat_status` record in the door's own
   store (`resting`, `reason: substrate_lent`) written before the server is
   stopped. Every wake whose event waited during the loan is told; if none
   waited, the first wake completed after the loan is told (at-least-once
   across retries, never zero).
4. **No human required.** A cooperating holder acquires the card with one
   command (`ayllu-gpu run`) that leases, waits for the acknowledged stop,
   runs its workload, and releases. The two primitives (`lease`, `wait`)
   exist for launchers that need them separately; a caller that leases
   and does not wait is an acknowledged operational hazard among mutually
   trusted local processes, not a defended case. Expiry is automatic.
5. **One actor owns the server unit: the door's heartbeat.** The only
   exception is `force-stop`, which can run only while holding the
   heartbeat's process-lifetime lock, which proves the heartbeat is not
   running.
6. **Fail closed.** When lease state cannot be read, or an action's outcome
   cannot be determined by observation, the resource is quarantined:
   nothing claims a wake, nothing starts the server, nothing grants a
   lease. Cleared only by a ledgered override.
7. **Every mutation is an intent row before it happens and an outcome row
   after**, and the next lock holder resolves any dangling intent by
   observation before doing anything else.

## Components

### 1. Lease file, lock, and ledger (`${AYLLU_STATE_DIR:-~/.local/state/ayllu}/gpu/`)

Project-independent, outside every repo.

`4090.lock` — flock. Every actor holds it for: any read-modify-write of the
lease file, any ledger append, the claim gate, and the start decision.
**Lock order:** `4090.lock` first, then the door's event-store lock, then
nothing else. No actor takes the event-store lock and then `4090.lock`.

`4090.lease` — present iff a lease is held or quarantined. One JSON object,
written by temp-file-and-rename under the lock:

```
{"resource": "4090", "lease_id": "<uuid4>", "holder": "yupi",
 "purpose": "learner sub-project 2, first 1M-param run",
 "since": "2026-09-20T14:00:00+00:00", "expires_at": "2026-09-20T20:00:00+00:00",
 "expected_until": "2026-09-20T18:00:00+00:00"}
```

Validation (shared fixtures `tests/fixtures/gpu_lease/*.json` with expected
verdicts, used by the bash and Python readers):

- Instants: ISO-8601 with explicit UTC offset; fractional seconds allowed.
- Live iff `now < expires_at`. Expired means free; the next lock holder
  ledgers `expire` and removes the file.
- `lease_id` uuid4; `holder`, `purpose` non-empty; `resource == "4090"`.
  Anything else, unparseable JSON, or an unreadable file is **malformed →
  quarantined**: file left in place; `quarantine_id = sha256(bytes)[:16]`
  (an unreadable file uses `sha256("")`); one `quarantine` row per
  `quarantine_id`; the same `quarantine_id` on later observations is the
  same quarantine, a different digest is a new one. Cleared only by
  `release --force`.
- `expected_until` is the holder's estimate, labelled so wherever
  rendered; `expires_at` is the enforceable deadline.

**`episode_id`**: `lease_id` for a lease, `quarantine_id` for a quarantine.
Every heartbeat record and ledger row that refers to a rest carries it.

`4090.ledger.jsonl` — append-only. Every row:

```
{"record_type": "gpu_lease", "action_id": "<uuid4>", "phase": "intent"|"outcome",
 "action": "lease"|"renew"|"release"|"expire"|"quarantine"|"force_stop"
          |"server_stop"|"server_start"|"server_ready"|"server_unready",
 "episode_id": ..., "holder": ..., "purpose": ..., "expires_at": ...,
 "by": "ayllu-gpu"|"heartbeat:qwen"|"<force --by name>", "at": <iso>,
 "outcome": "ok"|"not_performed"|"error"|"indeterminate",
 "reconciled": true|absent,
 "observed": {"active_state": ..., "sub_state": ..., "invocation_id": ...,
              "lease_present": bool, "lease_episode_id": ...},
 "detail": ...}
```

**Action state machine (invariant 7).** For every mutating action: (1) take
`4090.lock`; (2) resolve dangling intents (below); (3) append the intent
row; (4) perform the mutation; (5) observe; (6) append the outcome row;
(7) release the lock. A dangling intent is an `action_id` with an intent
row and no outcome row. The next lock holder, whoever it is, resolves each
by observation and appends an outcome row for the *original* `action_id`
with `reconciled: true`:

| dangling action | completed iff (observed) | else |
|---|---|---|
| lease / renew | lease file present, same `lease_id`, `expires_at` ≥ the intent's | `not_performed` |
| release | lease file absent, or present with a different `lease_id` | `not_performed` |
| expire | as release | `not_performed` |
| quarantine | file present and malformed with the same `quarantine_id` | `not_performed` |
| server_stop / force_stop | `ActiveState ∈ {inactive, failed}` | `active`/`activating`/`deactivating`/`reloading` → `not_performed` (the rule table re-applies) |
| server_start | `ActiveState ∈ {active, activating}` | `not_performed` |
| any, if `systemctl show` or the lease file cannot be read | — | `indeterminate` → quarantine with `quarantine_id = sha256(action_id)[:16]` |

Observation is `systemctl --user show -p ActiveState,SubState,InvocationID
hamutay-llama-server`, never `is-active`. `server_start` means "start
requested and the command returned"; readiness is `server_ready`, a
separate row bound to the `InvocationID` observed at that start
(component 4).

### 2. `deploy/ayllu-gpu` — the holder's command (bash + jq + flock, no uv)

```
ayllu-gpu run   --holder NAME --purpose "..." [--ttl 6h] [--expected-until ISO]
                [--wait-timeout 30m] -- <command...>
                # lease; wait for the acknowledged stop; run the command; release on EXIT
                # (trap). The command's exit status is ayllu-gpu's. This is the
                # registered way to use the card.
ayllu-gpu lease   --holder NAME --purpose "..." [--ttl 6h] [--expected-until ISO]
                  # prints lease_id; exit 2 if another holder's live lease or a quarantine
ayllu-gpu renew   --lease-id ID [--ttl 6h]
ayllu-gpu release --lease-id ID
ayllu-gpu release --force --by NAME --reason "..."   # ledgered override; clears quarantine
ayllu-gpu wait    --lease-id ID [--timeout 30m]      # success iff an ok server_stop outcome
                  # for this episode_id exists AND observed ActiveState ∈ {inactive, failed}
                  # now; exit 3 on timeout, with the door's last heartbeat_status printed
ayllu-gpu force-stop --lease-id ID --by NAME --reason "..."
ayllu-gpu status
```

- `--ttl` grammar `^[0-9]+[mhd]$`, bounds 1m–72h inclusive. Default 6h.
- Same holder calling `lease` on its own live lease is a renew:
  `lease_id`, `since`, `purpose` preserved; `expires_at = now + ttl`;
  `expected_until` replaced only if given.
- `renew`/`release` require the `lease_id`. Accountability, not security:
  all local callers share one Unix account; the ledger says who.
- **`force-stop`** (Codex r2 B2): takes `4090.lock`, then tries the door's
  heartbeat lock `community/qwen/session.jsonl.events.jsonl.heartbeat.lock`
  with `flock -n`. If the heartbeat holds it, `force-stop` refuses (exit
  4: "heartbeat is running; it will act within its poll interval, or is
  inside a wake that must finish"). If acquired, it holds both locks while
  it stops the server, observes, and ledgers, then releases. A `wait`
  timeout alone never authorizes a stop. If the dead heartbeat left a
  `running` event, boot recovery re-pends it, as today.
- `ayllu-gpu` never calls `systemctl` except in `force-stop` and `status`
  (read-only `show`).

### 3. Units and the deployment migration

Unit files after this change:

- `deploy/hamutay-llama-server.service`: `[Install]` removed; `Restart=always`,
  `RestartSec=10` kept for crashes. Comment: "started and stopped by
  `hamutay-heartbeat@qwen` only; do not enable".
- `deploy/hamutay-heartbeat@qwen.service.d/override.conf`: no `Requires=`,
  `Wants=`, or `After=` on the server; instead
  `Environment=HAMUTAY_GPU_LEASE=4090` (component 4).

**Migration (Codex r2 B4), ordered, run by `deploy/migrate-gpu-lease.sh`
and verified by `deploy/check-gpu-lease.sh`:**

1. `systemctl --user disable hamutay-llama-server` (the running process is
   untouched); assert `is-enabled` prints `disabled`.
2. Install the new drop-in; `systemctl --user daemon-reload`; assert
   `systemctl --user show -p Requires,Wants hamutay-heartbeat@qwen` lists no
   server unit.
3. `mkdir -p ~/.local/state/ayllu/gpu`.
4. Deploy the code (git pull on main).
5. Restart `hamutay-heartbeat@qwen` when the door has no `running` event
   (the script reads the store's latest statuses and waits up to 30 min;
   there is no lease yet, by construction, since `ayllu-gpu` is not yet
   in anyone's launcher). The new heartbeat boots, observes FREE and the
   server `active`, probes ready, proceeds.
6. `check-gpu-lease.sh` asserts: server `is-enabled` = `disabled`; no
   `Requires`/`Wants` on the server from any unit
   (`systemctl --user show -p WantedBy,RequiredBy hamutay-llama-server` empty);
   the state directory exists; the heartbeat's launch note printed
   `gpu lease: 4090`.

Host boot after migration: `hamutay-heartbeat@qwen` (enabled) starts, sees
FREE, starts the server, warms, proceeds.

### 4. The heartbeat: substrate guard

**Configuration.** `--gpu-lease {off,4090,PATH}`, default from
`$HAMUTAY_GPU_LEASE`, else `off`. `4090` resolves to the standard lease
path. No loopback inference (Codex r2 M1): participation is configured on
the unit, not guessed from the base URL. The resolved value is printed in
the launch note and recorded in `launch_config.gpu_lease`. Hosted doors
resolve to `off` and build no guard; their code path is unchanged and
tested unchanged.

**Claim gate (Codex r2 B1).** A `LeaseGate` object with one method used by
the claim path:

```
gate.claim(store, now) -> ("blocked", lease | quarantine) | ("claimed", (event, running)) | ("none", None)
```

It takes `4090.lock`, resolves dangling intents, validates the lease; if
live or quarantined it returns `blocked` without touching the store; else,
*still holding `4090.lock`*, it calls `store.claim_next_pending(now)`
(which takes the event-store lock inside, in the declared order), then
releases. `run_next_event` gains `claim_gate=None`; with a gate it uses
`gate.claim` in place of the direct call and returns
`{"status": "lease_blocked", ...}` on `blocked`; `run_pending_events`
threads the gate through and stops the batch on `lease_blocked`.
`step_pending_events`, `run-one`, and `run-all` in the events CLI read the
log's latest `launch_config.gpu_lease`; if it is not `off` they construct
the same gate. They never start or stop the server; a manual run while the
server is down fails as today (an operator's manual run, not a loan).

**Start gate.** Every `systemctl start` decision is made under `4090.lock`
after re-validating FREE; the intent row, the command, the observation,
and the outcome row all happen before the lock is released.

**Rest sequence (LEASE_LIVE or QUARANTINED), one thread, under `4090.lock`:**

1. Let `latest` be the store's latest `heartbeat_status`. If `latest` is
   not (`resting`, this reason, this `episode_id`): append
   `resting/substrate_lent` (or `resting/substrate_lease_unreadable`) with
   `detail = {episode_id, holder, purpose, since, expires_at,
   expected_until, source: "observed", continuation: <true iff an earlier
   record for this episode_id exists>}`. De-duplication is against the
   *latest* status only (Codex r2 S1), so after a restart the
   `waking/boot` record is followed by a continuation rest.
2. If observed `ActiveState ∉ {inactive, failed}`: `server_stop` intent →
   `systemctl --user stop` → observe → outcome (`ok` iff inactive/failed;
   else `not_performed`, retried next step).
3. Return `{"state": "resting", "sleep_seconds": poll_interval}`.

**Return sequence (FREE):**

1. If `latest` is a rest for a substrate `episode_id`, or the guard's boot
   reconciliation found one (below): append `waking/substrate_returning`
   with `{episode_id, closed_at_source: "observed"|"ledger"}`.
2. Under `4090.lock`, re-validate FREE; if `ActiveState ∉ {active, activating}`:
   `server_start` intent → start → observe (record `InvocationID`) →
   outcome.
3. Probe `GET <base_url>/models`, 2 s timeout, 200 = ready. Not ready →
   return `{"state": "warming", "sleep_seconds": poll_interval}` with no
   transition. Ready → if the guard's remembered ready `InvocationID`
   differs from the observed one, append `server_ready` (once per
   not-ready→ready transition; Codex r2 M3) and run **context
   rediscovery**; then fall through to the budget check and the claim.
   A later probe failure after ready appends `server_unready` once and
   forgets the ready invocation.

**Boot reconciliation** runs *before* `HeartbeatLoop.boot()` appends
`waking/boot` (Codex r2 S1): under `4090.lock`, resolve dangling intents;
then for every substrate rest episode in the store with no closing status
whose `episode_id` is no longer live/quarantined, append
`waking/substrate_returning` with `created_at` = the ledger's `release`,
`expire`, or `release --force` outcome `at` for that `episode_id` (else boot
time, `closed_at_source: "boot"`). Then, for every ok `force_stop`
outcome (reconciled or not) whose `episode_id` has no rest record in the
store, append `resting/substrate_lent` with `created_at` = that row's `at`,
`source: "reconstructed_from_ledger"`, and, if the lease is already gone,
the matching returning record. Then `boot()` proceeds.

**Overlap with the budget rest.** Strict priority in one stream: lease or
quarantine first, then budget. A budget rest split by a loan is two budget
segments around one substrate episode, each with its own note;
`_rest_episodes` does not merge across a substrate episode. Named cases:
budget-before-lease, lease-before-budget, midnight during a lease (new day
evaluated fresh on return), restart during either.

**Context ceiling across a loan (Codex r2 S3).** `resolve_context_limit`
gains an inheritance step: when discovery fails, take the latest record in
the log whose `launch.context_limit` is a positive int and whose
`launch.{model, provider, base_url}` equal the resolved launch; source
`"inherited"`, printed loudly. Explicit `--context-limit` beats everything
and is never overwritten by rediscovery. On `server_ready`, rediscover from
`/props`; if it succeeds and there is no explicit limit, set
`session._context_limit` and `session._launch_config["context_limit"]`/
`["context_limit_source"] = "discovered"` (the session writes `launch`
into every record, so the change persists and the next boot inherits it).
A participating door with no explicit limit, no matching inherited limit,
and failed rediscovery stays `warming` and does not claim. The parser
rejects `--context-limit <= 0`.

### 5. Envelope notes

`events.py::_rest_episodes` groups substrate episodes by
`detail.episode_id`; `resting(episode X) → waking/boot → resting(episode X,
continuation)` is one episode. `operational_notes_for_event` renders:

> heartbeat rested from … to … (GPU allocated to another workload; lease
> record: holder "yupi", purpose "learner sub-project 2, first 1M-param
> run"); this event waited 5h 12m of it.

Quarantine: "(GPU lease state unreadable; quarantine <id>)". Open episode:
"resting since … (…; the lease expires at …; the holder's estimate of
return is …)".

**Who is told (Codex r2 S2).** Rule (a): every event whose pending
interval intersects the episode, as today. Rule (b), only when rule (a)
produced no note for this episode in this envelope: the episode is closed,
and no event has a `completed` status record appended after the episode's
closing status. Sentence: "Before this event existed, the heartbeat rested
from … to … (…)." Consumption is a *completed* wake, so a claim that
fails or crashes before completion leaves the note for the retry:
at-least-once, never zero, and at most one note per episode per envelope.
The existing budget-rest test (no note for an event created after the
rest) is unchanged; rule (b) is specific to substrate episodes.

### 6. Constitution, deployment, checkpoint, yupi

Constitution, one operational sentence when the resolved `--gpu-lease` is
not `off`: "The heartbeat may pause while the local GPU is allocated to
another workload; its lease record carries a declared holder and purpose,
pending events remain pending, and affected wakes receive an operational
note."

Deployment: `deploy/ayllu-gpu`, `deploy/migrate-gpu-lease.sh`,
`deploy/check-gpu-lease.sh`, edited server unit, edited drop-in;
operations lines in `community/README.md`.

Checkpoint: `deploy/checkpoint-community-log.sh` resolves
`${AYLLU_STATE_DIR:-$HOME/.local/state/ayllu}/gpu/4090.ledger.jsonl`; absent
→ note and skip; else byte snapshot under `4090.lock`, and
`filename, sha256, byte count, timestamp` appended to
`community/gpu/CHECKPOINTS.txt` in the same signed checkpoint commit. The
ledger is never copied into the repository.

Yupi: one paragraph in its corpus-generator design §11 replacing "the PI
suspends…" with `ayllu-gpu run`. Separate commit in yupi's repo.

## Data flow, one loan

1. Yupi: `ayllu-gpu run --holder yupi --purpose "…" --ttl 8h -- uv run python -m yupi.train …`
2. `run` leases (intent, write, outcome), then `wait`s.
3. Heartbeat step: `gate` sees LEASE_LIVE → rest sequence: resting record →
   stop intent → stop → observe inactive → outcome ok.
4. `wait` sees the ok outcome and inactive state → the trainer runs. `run`
   renews every `ttl/2` in the background while the command runs.
5. Command exits → trap: `release` (intent, remove, outcome).
6. Heartbeat step: FREE → `waking/substrate_returning` → start under lock →
   warming steps → ready → `server_ready` → rediscovery → budget → claim.
7. The claimed wake's envelope carries the note (rule a, else b).

If the heartbeat is not running at step 3: `wait` times out (exit 3);
`run` exits 3 without running the command and releases. A launcher that
knows the heartbeat is decommissioned may `force-stop`, which succeeds only
if it can take the heartbeat lock.

## Error handling

- Malformed lease: quarantine (invariant 6); the door rests with reason
  `substrate_lease_unreadable`; server left as is; no claims, no starts,
  no grants. Cleared by `release --force`.
- `systemctl` command error: outcome `error` with stderr; the rule table
  re-applies next step. A server that will not come back keeps the door
  `warming` with one `server_start` intent/outcome pair per heartbeat
  attempt (systemd's own retries are not enumerated).
- Heartbeat crash at any point of the rest or return sequence: the next
  lock holder resolves the dangling intent by the table; the latest-status
  de-duplication makes the rest record continuation-safe; boot
  reconciliation closes episodes that ended while down.
- Clock: one host; no skew handling.

## Testing

- `tests/test_gpu_lease.py`: Python reader/writer vs the shared fixtures;
  TTL grammar/bounds; atomic write; foreign-holder refusal; same-holder
  re-lease; dangling-intent resolution for every action (process death
  simulated at each step of the state machine, with a fake `systemctl
  show`); indeterminate → quarantine; quarantine identity across repeated
  observations and changed bytes.
- `tests/gpu_lease/test_ayllu_gpu.py` (subprocess-driven): the bash CLI
  vs the same fixtures with a fake `systemctl` and a temp
  `AYLLU_STATE_DIR`; `wait` success conditions; `run` end to end (lease,
  wait, command, trap release, exit status, background renew); `force-stop`
  refused while a fake heartbeat holds the lock, allowed when not, ledgered
  either way.
- `tests/test_heartbeat_guard.py`: `HeartbeatLoop` with an injected gate,
  store, clock, fake `systemctl show`, fake probe: rest sequence order
  (record before stop); latest-status de-dup with continuation after
  `waking/boot`; return sequence with warming not transitioning;
  `server_ready` once per invocation; the four overlap cases; boot
  reconciliation (release while down, expiry while down, restart during
  quarantine, reconstruction from reconciled and unreconciled `force_stop`);
  lease-before-claim and claim-before-lease through the real
  `run_next_event` with the gate; start-under-lock revalidation
  (lease-before-start); `claim_limit=1`; the events CLI runners refusing
  or gating; hosted door unchanged (existing `tests/test_heartbeat.py` and
  `tests/test_wake_budget.py` pass unmodified) and `--gpu-lease off` on a
  local door.
- `tests/test_events_rest_notes.py`: substrate episodes and continuation
  in `_rest_episodes`; note text; open episode; rule (a)/(b) precedence;
  rule (b) at-least-once across a failed claim, a crash before exchange,
  and a crash after exchange before completion; budget-after-rest test
  unchanged.
- Context ceiling: explicit precedence; inheritance only for a matching
  substrate and positive value; first boot without history stays warming;
  rediscovery failure; a changed limit persisted through `launch`.
- Units and migration: `systemd-analyze --user verify` on the edited
  units; `check-gpu-lease.sh` exercised against a fake `systemctl` for
  enabled/disabled and WantedBy states.
- Codex authors the independent validation in its own signed commits.
- First live loan is a registered check: `ayllu-gpu run --ttl 15m -- sleep 600`
  during a quiet stretch not overlapping the door's 09:00Z self-check; then
  the store, the ledger, and the resident's next envelope are read and the
  result recorded in `community/README.md`.

## Not built (on the record)

Queueing or priority between holders; partial card sharing; a knock to
the resident before the loan; any change to the two hosted doors;
multi-host resources; a second local door on the same card (declared
unmeasured); defence against a local caller that leases without waiting.

## Declared losses

- The resident is told after, never asked (invariant 1). The qwen resident
  hears the design as a consultation (enclosed, no verdict) after round
  three and before the code lands.
- `expires_at` in the resident's record is as first observed; renewals
  live in the ledger.
- The TTL default (6h) and maximum (72h) are unmeasured.
- Accountability, not security.
- Rule (b) is at-least-once, not exactly-once; the crash boundary between
  sending the envelope and recording completion is irreducible.

## Dispositions of Codex round two

B1 (may_claim not a barrier; start not linearized; direct runners bypass):
adopted — `LeaseGate.claim` holds `4090.lock` across `claim_next_pending`;
start under the same lock with revalidation; events CLI runners gated from
the log's `gpu_lease`. B2 (`force-stop` kills a wake): adopted — requires
the heartbeat's process lock; timeout never authorizes. B3 (ledger not
crash-consistent): adopted — action state machine, dangling-intent table,
reconciled outcomes on the original `action_id`, indeterminate →
quarantine, reconstruction consumes reconciled `force_stop`. B4 (enabled
unit persists): adopted — `migrate-gpu-lease.sh` disables and
`check-gpu-lease.sh` asserts persisted state.

S1 (restart continuation): adopted — latest-status de-dup, continuation
flag, boot reconciliation before `waking/boot`, ledger-derived closing
time. S2 (rule b): adopted — (a) precedes (b); consumption = completed
wake; at-least-once declared. S3 (context ceiling): adopted — substrate
match, positive only, explicit never overwritten, session launch config
updated, warming when unknowable, parser rejects ≤ 0; lazy construction
dropped since the limit is mutable. S4 (quarantine identity): adopted —
`quarantine_id` from bytes, `episode_id` generalizes. S5 (`wait` a
convention): adopted — `ayllu-gpu run` is the registered operation;
invariant 4 weakened to say what is and is not defended.

M1 (loopback inference): adopted — configured on the unit, no inference.
M2 (`is-active`): adopted — `show -p ActiveState,SubState,InvocationID`;
stop ok requires observed inactive/failed. M3 (`server_ready` churn):
adopted — once per `InvocationID`, `server_unready` on regression.
