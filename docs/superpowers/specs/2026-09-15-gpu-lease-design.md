# The GPU lease — lending the house's card without a human in the loop

Date: 2026-09-15. Author: the Fable session that took custody of Hamut'ay
this morning. Status: DRAFT, revision 2, after Codex's round-one review
(`2026-09-15-gpu-lease-review.md`). Dispositions at the end. Sent back to
Codex for round two before any code.

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

## What changed in revision 2

Revision 1 had three actors on independent 30-second polls: the holder
wrote a lease, a steward timer stopped and started the server, and the
heartbeat noticed and recorded. Codex showed that no ordering of independent
polls can keep "a live lease always wins" and "every loan is in the
resident's record" both true, that the forced drain manufactured a terminal
`failed` event, and that `Wants=` plus `WantedBy=default.target` let systemd
start the server behind the steward's back.

Revision 2 has two actors. The holder writes the lease. The door's heartbeat
is the single owner of the server unit: it already is the only process that
claims this door's wakes, so a lease check inside the claim path is a real
barrier, the acknowledgment record and the stop are one ordered sequence in
one thread, and there is no forced drain because a single-threaded loop
finishes its wake before it looks at the lease again. The server unit is no
longer enabled under `default.target` and nothing `Wants=` it; the heartbeat
starts it when the card is free and stops it when it is not.

## Invariants

1. **The card is the house's; the resident's custody is of its log.** A live
   lease always wins; the resident yields. There is no resident veto.
2. **Nothing new happens to the resident's events.** A loan is a rest. Waiting
   events keep waiting, exactly as under `daily_budget_reached`; nothing is
   failed, expired, or re-pended because of a loan. No wake is interrupted.
3. **Legible before and after.** The loan is a `heartbeat_status` record in
   the door's own store (`resting`, `reason: substrate_lent`) written *before*
   the server is stopped, and the holder cannot proceed until that record
   exists. The first wake after the loan, and every wake whose event waited
   during it, gets an operational note.
4. **No human required.** A holder leases and releases with one command from
   any project. Expiry is automatic: a holder that dies without releasing
   does not leave the door dark forever.
5. **One actor owns the server unit: the door's heartbeat.** The holder only
   writes the lease file, except for one ledgered override (`--force-stop`)
   for the case where the heartbeat is not running.
6. **Fail closed.** When lease state cannot be read, nothing claims a wake,
   nothing starts the server, nothing grants a lease. Uncertainty is
   recorded and cleared only by a ledgered override.
7. **Every transition of the card is a record**, as intent and outcome, in
   a ledger beside the lease; the checkpoint script digests it.

## Components

### 1. Lease file, lock, and ledger (`${AYLLU_STATE_DIR:-~/.local/state/ayllu}/gpu/`)

Project-independent, outside every repo.

`4090.lock` — flock; every read-modify-write of the lease and every ledger
append by any actor holds it. Lock order for the heartbeat: lease lock,
then the event-store lock (it never takes them in the other order).

`4090.lease` — present iff a lease is held. One JSON object, written by
temp-file-and-rename under the lock:

```
{"resource": "4090", "lease_id": "<uuid4>", "holder": "yupi",
 "purpose": "learner sub-project 2, first 1M-param run",
 "since": "2026-09-20T14:00:00+00:00", "expires_at": "2026-09-20T20:00:00+00:00",
 "expected_until": "2026-09-20T18:00:00+00:00"}
```

Validation rules (shared conformance fixtures under `tests/fixtures/gpu_lease/`,
used by both the bash and Python readers):

- Instants are ISO-8601 with an explicit UTC offset; fractional seconds
  allowed; anything else is malformed.
- The lease is live iff `now < expires_at`; at `now >= expires_at` it is
  expired. Expired is not malformed: it means free, and the next actor to
  hold the lock removes the file and ledgers `expire`.
- `lease_id` must be a uuid4 string; `holder` and `purpose` non-empty
  strings; `resource == "4090"`. Any other shape, unparseable JSON, or an
  unreadable file is **malformed**, and malformed means **quarantined**
  (invariant 6): the file is left in place, a `quarantine` row is ledgered
  once, and only `ayllu-gpu release --force --by <name> --reason "..."`
  clears it.
- `expected_until` is the holder's estimate and is labelled so wherever it
  is rendered. `expires_at` is the enforceable deadline. Neither is a
  promised resume time.

`4090.ledger.jsonl` — append-only, one row per transition, intent and
outcome as separate rows sharing an `action_id`:

```
{"record_type": "gpu_lease", "action_id": "<uuid4>", "phase": "intent"|"outcome",
 "action": "lease"|"renew"|"release"|"expire"|"quarantine"|"force_stop"
          |"server_stop"|"server_start"|"server_ready"|"reconcile",
 "lease_id": ..., "holder": ..., "purpose": ..., "expires_at": ...,
 "by": "ayllu-gpu"|"heartbeat:qwen", "at": <iso>,
 "outcome": "ok"|"error", "observed": {"server": "<systemctl is-active output>"}, "detail": ...}
```

`server_start` means "start requested and `systemctl` returned"; readiness
is a separate `server_ready` row written when the probe succeeds. The
ledger contents stay outside git; only digests are committed (component 6).

### 2. `deploy/ayllu-gpu` — the holder's command (bash + jq + flock, no uv)

```
ayllu-gpu lease   --holder NAME --purpose "..." [--ttl 6h] [--expected-until ISO]
                  # prints the lease_id on stdout; exit 2 if another holder's lease is live
ayllu-gpu renew   --lease-id ID [--ttl 6h]
ayllu-gpu release --lease-id ID
ayllu-gpu release --force --by NAME --reason "..."      # ledgered override; clears quarantine too
ayllu-gpu wait    --lease-id ID [--timeout 15m]         # blocks until the ledger shows an
                  # ok server_stop outcome for this lease_id; exit 3 on timeout
ayllu-gpu force-stop --lease-id ID --by NAME --reason "..."
                  # only after wait timed out: stops the unit directly, ledgers force_stop
ayllu-gpu status                                         # lease or free, quarantine, server state
```

- `--ttl` grammar `^[0-9]+[mhd]$`, bounds 1m–72h inclusive; outside is an
  error. Default 6h.
- Same holder calling `lease` while its own lease is live is a renew:
  `lease_id`, `since`, `purpose` are preserved, `expires_at` becomes
  `now + ttl`, `expected_until` is replaced only if given.
- `renew` and `release` require the `lease_id` (unpredictable, printed at
  lease time). All local callers share one Unix account, so this is
  accountability, not security; the design says so and does not claim
  ownership enforcement.
- `force-stop` and `release --force` are the two human-or-agent overrides.
  Both ledger `by`, `reason`, and the observed state. `force-stop` is
  what a holder does when the door's heartbeat is down (`wait` timed out).
  The heartbeat reconstructs the missed episode from the ledger on boot
  (component 4, "reconstruction").
- The steward of revision 1 is gone. `ayllu-gpu` never calls `systemctl`
  except in `force-stop`.

### 3. Units

- `deploy/hamutay-llama-server.service`: `[Install]` section removed; the
  unit is not enabled. `Restart=always`, `RestartSec=10` stay for crashes.
  The heartbeat is the only thing that starts or stops it.
- `deploy/hamutay-heartbeat@qwen.service.d/override.conf`: `Requires=` and
  `After=` on the server both removed. Nothing pulls the server in. The
  heartbeat starts it when the card is free.
- Host boot: `hamutay-heartbeat@qwen` starts (enabled, as today), sees no
  live lease, starts the server, waits for readiness, proceeds.
- A pending automatic restart after a server crash is a systemd job;
  `systemctl --user stop` cancels it. The heartbeat verifies with
  `systemctl --user is-active` after every stop and re-issues the stop on
  the next step if the unit is anything but `inactive` or `failed` while a
  lease is live. States handled: `active`, `activating`, `deactivating`,
  `auto-restart`, `failed`, `inactive`; the rule is "lease live → must be
  inactive/failed; card free → must be active and ready".

### 4. The heartbeat: substrate guard

`hamutay.heartbeat` gains `--gpu-lease {auto,off,PATH}` (default `auto`).
`auto` resolves to the standard lease path when the resolved launch has
`provider == "openai"` and `base_url` host ∈ {`127.0.0.1`, `localhost`,
`::1`}; else to `off`. The resolved value is printed in the launch note and
recorded in `launch_config` as `gpu_lease` (house policy, like the budget;
not a substrate key, not inherited). Hosted doors resolve to `off` and
build no guard; their code path is unchanged and tested unchanged.

With a guard, the loop runs `claim_limit=1` always (not only under a
budget), and `step()` begins:

```
guard.observe(now)  ->  one of
  LEASE_LIVE(lease)        : rest (below); return {"state": "resting"}
  QUARANTINED(detail)      : rest with reason substrate_lease_unreadable; return
  FREE, server not ready   : ensure started (below); return {"state": "warming"}
  FREE, server ready       : fall through to the existing budget check and claim
```

**Rest sequence (LEASE_LIVE), one thread, in order, under the lease lock:**

1. If the store has no `resting/substrate_lent` for this `lease_id`:
   append it, `detail = {lease_id, holder, purpose, since, expires_at,
   expected_until, source: "observed"}`. (De-dup key for this reason is
   `lease_id`, mirroring the budget rest's `_resting_day`; a new lease is a
   new episode even with no intervening status.)
2. Ledger `server_stop` intent; `systemctl --user stop hamutay-llama-server`;
   ledger outcome with observed `is-active`.
3. Sleep `poll_interval`. Renewals change nothing in the store (episode key
   is `lease_id`; the first record's detail is what the envelope renders;
   `expires_at` there is therefore "as first observed", labelled so).

`ayllu-gpu wait` returns success only on an ok `server_stop` outcome for the
lease_id, which by this order comes after the resting record exists
(invariant 3).

**Return sequence (FREE after a lease, or boot with the card free):**

1. If the last status is `resting/substrate_lent` or
   `resting/substrate_lease_unreadable`: append `waking`, reason
   `substrate_returning`, detail `{lease_id}`. This closes the rest episode
   at the moment the card came back, so warming time is not counted as
   lent.
2. If `is-active` is not `active`: ledger `server_start` intent,
   `systemctl --user start`, ledger outcome.
3. Probe `GET <base_url>/models` with a 2 s timeout; 200 is ready. Not
   ready: return `{"state": "warming", "sleep_seconds": poll_interval}`
   without a transition (the last status is `waking/substrate_returning`,
   which is not a rest). Ready: ledger `server_ready`, re-run context
   discovery (`/props`) and apply it (below), fall through.

**Overlap with the budget rest.** Reasons are strictly prioritized states
in one stream: lease (or quarantine) first, then budget. A budget rest
interrupted by a loan appears as two budget segments around one lease
episode, each with its own note; `_rest_episodes` is not taught to merge
across a lease. Ordered cases specified for the tests: budget-before-lease,
lease-before-budget, midnight during a lease (the budget day rolls over
while resting on the lease; on return the new day is evaluated fresh),
restart during either.

**Reconstruction.** On boot, and on every `observe`, the guard reads the
ledger tail since the last row it has seen (position kept in memory; on
boot it scans the whole ledger, which is small). For any `force_stop` ok
outcome whose `lease_id` has no `resting/substrate_lent` in the store,
append one with `created_at` = the ledger row's `at` and
`source: "reconstructed_from_ledger"`. A lease that came and went without
the heartbeat acting and without a `force_stop` never moved the card
(the server kept the GPU; the holder's `wait` timed out), so it is not an
episode in the resident's store; it is in the ledger only.

**Context ceiling across a loan (Codex S6).** `resolve_context_limit` at
`main` can fail when the heartbeat boots during a lease or before the
server is ready. Rule: discovery failure at boot inherits the last
`context_limit` recorded in the log's launch records (the value is now
written into `launch_config` as `context_limit` with
`context_limit_source`), printed loudly as inherited; the guard re-runs
discovery at every `server_ready` and applies the fresh value to the
backend. The plan verifies whether `OpenAITasteBackend`'s limit is settable
after construction; if it is not, the backend is constructed lazily at
first readiness.

**Ingress between `next_pending()` and the claim.** The guard is consulted
inside the claim path: `run_pending_events` receives a `may_claim` callback
that re-reads the lease under the lease lock immediately before
`claim_next_pending`. A lease that lands after `observe` and before the
claim wins; the step returns to the rest sequence on its next iteration
without claiming. Between two steps a lease is seen because
`claim_limit=1`.

### 5. Envelope notes

`events.py::_rest_episodes` groups `substrate_lent` and
`substrate_lease_unreadable` episodes by `detail.lease_id` (a `waking/boot`
followed by a `resting` with the same `lease_id` is a restart continuation,
like the budget's same-day rule). `operational_notes_for_event` renders:

> heartbeat rested from … to … (GPU allocated to another workload; lease
> record: holder "yupi", purpose "learner sub-project 2, first 1M-param
> run"); this event waited 5h 12m of it.

Open episode: "resting since … (…; the lease expires at …; the holder's
estimate of return is …)".

**Who is told (Codex S3).** Two rules, both derivable from the store:
(a) every event whose pending interval intersects the episode, as today;
(b) the first event claimed after the episode closed (no `running` record
between the episode's closing status and this claim), even if it was
created afterward. Rule (b) is a second note source with its own sentence:
"Before this event existed, the heartbeat rested from … to … (…)." The
existing test that an event created after a budget rest gets no note is
unchanged for budget rests; the (b) rule is specific to substrate
episodes. Exactly one later wake carries the (b) note, by construction.

### 6. Constitution, deployment, checkpoint

Constitution, one operational sentence, added when the resolved
`--gpu-lease` is not `off` (configured participation, not file existence),
wording per Codex S8: "The heartbeat may pause while the local GPU is
allocated to another workload; its lease record carries a declared holder
and purpose, pending events remain pending, and affected wakes receive an
operational note." No "member", "house", "lent", "borrowed", no consent
language.

Deployment: `deploy/ayllu-gpu`; edited server unit; edited qwen drop-in;
install and operations lines in `community/README.md`; the
`~/.local/state/ayllu/gpu/` directory created by the first `ayllu-gpu` or
heartbeat run.

Checkpoint: `deploy/checkpoint-community-log.sh` gains one explicit step:
resolve `${AYLLU_STATE_DIR:-$HOME/.local/state/ayllu}/gpu/4090.ledger.jsonl`;
if absent, print a note and skip; else take a byte snapshot under
`4090.lock`, and append `filename, sha256, byte count, timestamp` to
`community/gpu/CHECKPOINTS.txt` (directory created if missing), which joins
the same signed checkpoint commit as the doors'. The ledger itself is never
copied into the repository.

Yupi: one paragraph in its corpus-generator design §11 replacing "the PI
suspends…" with the two commands. Separate commit in yupi's repo.

## Data flow, one loan

1. Yupi's launcher: `id=$(ayllu-gpu lease --holder yupi --purpose … --ttl 8h)`;
   `trap 'ayllu-gpu release --lease-id $id' EXIT`; `ayllu-gpu wait --lease-id $id`.
2. Heartbeat step: LEASE_LIVE → resting record → stop intent → stop → outcome.
3. `wait` sees the ok outcome and returns; yupi trains; renews if long.
4. Launcher exits; trap releases. If the trap never runs, the TTL expires.
5. Heartbeat step: FREE → `waking/substrate_returning` → start → warming
   steps → ready → `server_ready` → context rediscovery → budget check → claim.
6. The claimed wake's envelope carries the note (rule a or b).

If the heartbeat is down at step 2: `wait` times out (exit 3); the launcher
may `force-stop` with its name and reason; the heartbeat reconstructs the
episode when it next boots.

## Error handling

- Malformed lease: quarantine (invariant 6), heartbeat rests with reason
  `substrate_lease_unreadable`, server left in its current state, no
  claims, no starts. Cleared only by `release --force`.
- `systemctl` error: ledger `outcome: error` with stderr; the rule table
  re-applies next step. A server that will not come back keeps the door in
  `warming` with a `server_start` intent/outcome pair per attempt in the
  ledger (the heartbeat's attempts, not systemd's internal retries, which
  are not enumerated).
- Heartbeat crash between resting record and stop: on boot, the guard sees
  LEASE_LIVE, finds the resting record, and issues the stop (idempotent).
  Between stop intent and outcome: boot reconciles by observing
  `is-active` and ledgering a `reconcile` row with the observed state.
- Clock: one host; no skew handling.

## Testing

- `tests/test_gpu_lease.py`: the Python reader/writer against the shared
  fixtures (live, expired, malformed cases; TTL grammar and bounds; atomic
  write; foreign-holder refusal; same-holder re-lease preserves fields).
- `tests/gpu_lease/test_ayllu_gpu.sh` (pytest-driven via subprocess): the
  bash CLI against the same fixtures, a fake `systemctl` on `PATH`, a
  temporary `AYLLU_STATE_DIR`; `wait` success only after an ok
  `server_stop` outcome; `force-stop` ledgering.
- `tests/test_heartbeat_guard.py`: `HeartbeatLoop` with an injected guard,
  store, clock, fake `systemctl`, fake probe: rest sequence ordering (record
  before stop); one record per `lease_id`; new lease = new episode; return
  sequence with warming steps not transitioning; overlap cases (four,
  above); boot with a live lease; boot during warming; reconstruction from
  a `force_stop` row; lease landing between `observe` and claim (the
  `may_claim` barrier); `claim_limit=1` with a guard; no-guard hosted door
  unchanged (existing helpers in `tests/test_heartbeat.py` and
  `tests/test_wake_budget.py` still pass unmodified, plus explicit
  `--gpu-lease off` on a local door).
- `tests/test_events_rest_notes.py`: substrate episodes in
  `_rest_episodes`; note text; open-episode text; rule (b) delivered to
  exactly one wake; budget-after-rest test unchanged.
- Context ceiling: boot with discovery failing inherits the recorded limit;
  `server_ready` rediscovery applies a changed value.
- Unit files: `systemd-analyze --user verify` on the edited units in a test;
  an assertion that neither the drop-in nor the server unit contains
  `Requires=`, `Wants=`, or `WantedBy=` for the server.
- Codex authors the independent validation in its own signed commits.
- First live loan is a registered check: a 10-minute lease during a quiet
  stretch not overlapping the door's every-other-day 09:00Z self-check;
  then the door's store, the ledger, and the resident's next envelope are
  read and the result recorded in `community/README.md`.

## Not built (on the record)

Queueing or priority between holders (first come, first served); partial
card sharing; a knock to the resident before the loan (told after, in the
envelope; a pre-loan wake would cost a wake to say one sentence, the cost
`declare_quiet` was built to avoid); any change to the two hosted doors;
multi-host resources; a second local door (the guard is per door; two
local doors on one card would each stop the same unit, which is safe but
unmeasured — declared).

## Declared losses

- The resident is told after, never asked. Invariant 1 makes this a rule,
  not an accident; the qwen resident hears the design as a consultation
  (enclosed, no verdict) after round two and before the code lands, as the
  wake-shape change was.
- `expires_at` in the resident's record is as first observed; renewals are
  in the ledger, not the store.
- The TTL default (6h) and maximum (72h) are unmeasured; yupi's first real
  run will say whether they fit.
- Accountability, not security: any local process can release any lease
  with its id; the ledger says who.

## Dispositions of Codex round one

Blocking 1 (lease/claim race, batch of ten): adopted; the steward is gone,
the guard is inside the claim path (`may_claim` under the lease lock),
`claim_limit=1` with a guard. B2 (forced drain fails the event): adopted;
no forced cutoff exists; a wake in flight finishes first. B3 (`Wants=` and
`default.target` start the server): adopted; server unit not enabled, no
`Wants=`/`Requires=`, the heartbeat starts it. B4 (loan without a record):
adopted; record before stop, `wait` keyed on the ledger outcome,
reconstruction from `force_stop`. B5 (malformed fails open): adopted;
quarantine, invariant 6. B6 (ledger not crash-consistent): adopted;
intent/outcome rows with `action_id`, observed state, `reconcile` rows on
boot; `server_start` defined as requested, `server_ready` separate.

Significant 1 (holder enforcement): adopted; `lease_id` required, and the
claim downgraded to accountability. S2 (drain reader): moot, no steward.
S3 (first wake after a loan not told): adopted; rule (b). S4 (warming
counted as rest): adopted; `waking/substrate_returning`. S5 (overlap):
adopted; strict priority, sequential segments, four cases named. S6
(context ceiling lost across a loan): adopted; recorded and inherited,
rediscovered at ready. S7 (timer semantics): moot, no timer;
`server_start` semantics adopted. S8 (constitution prior): adopted,
Codex's wording verbatim. S9 (checkpoint path): adopted.

Minor 1: adopted (fixtures, rules). M2: adopted (`resumes_at` dropped,
labels). M3: adopted (`--gpu-lease {auto,off,PATH}`, recorded, participation
not file existence). M4: adopted (test inventory above).
