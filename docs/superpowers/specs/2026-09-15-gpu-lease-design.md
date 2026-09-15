# The GPU lease — lending the house's card without a human in the loop

Date: 2026-09-15. Author: the Fable session that took custody of Hamut'ay
this morning. Status: DRAFT, sent to Codex for review before any code.

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

The qwen resident is also the first member whose ground is in the house.
When its ground is borrowed, the record must say so, in the resident's own
log, in the same shape it already uses for a budget rest.

## Invariants

1. **The card is the house's; the resident's custody is of its log.** A live
   lease always wins; the resident yields. There is no resident veto.
2. **Nothing new happens to the resident's events.** A loan is a rest. Waiting
   events keep waiting, exactly as under `daily_budget_reached`; nothing is
   failed, expired, or re-pended because of a loan.
3. **Legible before and after.** The loan is a `heartbeat_status` record in
   the door's own store (`resting`, `reason: substrate_lent`), and the next
   wake's envelope says who borrowed the card, why, and how long the event
   waited, through the existing operational-notes path.
4. **No human required.** A holder leases and releases with one command from
   any project. Expiry is automatic: a holder that dies without releasing
   does not leave the door dark forever.
5. **One actor owns the server.** The steward starts and stops
   `hamutay-llama-server`. The heartbeat only reads the lease and records.
   The holder only writes the lease. Nobody else touches the unit.
6. **Every transition of the card is a record.** A ledger beside the lease
   file carries the card's own history; the checkpoint script digests it.

## Components

### 1. The lease file and ledger (`~/.local/state/ayllu/gpu/`)

Project-independent, outside every repo. `${AYLLU_STATE_DIR}` overrides the
root (tests, other hosts).

`4090.lease` — present iff a lease is held. Canonical JSON, one object:

```
{"resource": "4090", "lease_id": "<uuid>", "holder": "yupi",
 "purpose": "learner sub-project 2, first 1M-param run",
 "since": "<iso utc>", "expires_at": "<iso utc>",
 "expected_until": "<iso utc>" | absent, "pid": 12345 | absent}
```

- `expires_at` is the TTL. A lease past `expires_at` is dead: the steward
  treats it as released and the next `lease` may take the card. `renew`
  pushes it forward. Default TTL 6h, maximum 72h per renew, so a forgotten
  lease costs at most three days of the resident's ground.
- `expected_until` is informational, for the resident's envelope.
- Writes are atomic (temp file + rename) under `4090.lock` (flock) so two
  holders cannot both win.

`4090.ledger.jsonl` — append-only, one record per transition:
`{"record_type": "gpu_lease", "action": "lease"|"renew"|"release"|"expire"|
"server_stop"|"server_start", "lease_id", "holder", "purpose", "at",
"expires_at", "by": "ayllu-gpu"|"steward"}`.

### 2. `deploy/ayllu-gpu` — the holder's command (plain bash + jq, no uv)

```
ayllu-gpu lease   --holder yupi --purpose "..." [--ttl 6h] [--expected-until ISO]
ayllu-gpu renew   [--ttl 6h]              # same holder only (holder read from the lease)
ayllu-gpu release                          # same holder only, unless --force
ayllu-gpu wait    [--timeout 15m]         # blocks until the server is inactive (exit 3 on timeout)
ayllu-gpu status                           # prints lease or "free", plus server state
ayllu-gpu reconcile                        # the steward's one step (see 3)
```

- `lease` refuses (exit 2, message names the holder and `expires_at`) if a
  live lease exists for a different holder. Same holder re-leasing renews.
- `lease` does not stop the server itself; it writes the file and returns.
  Callers that need the card free before proceeding run `ayllu-gpu wait`
  (polls until the server is inactive; the steward runs every 30 s, so
  this is bounded by one poll interval plus drain).
- `--holder` is a free string; the ledger is the accountability, not a
  registry. Yupi's trainer and the TurboQuant runner call this from their
  own launch scripts.

### 3. The steward (`ayllu-gpu-steward.timer` + `.service`, every 30 s)

`ayllu-gpu reconcile`, one reconciliation, idempotent:

| lease live | server active | door wake in flight | action |
|---|---|---|---|
| yes | yes | no | `systemctl --user stop hamutay-llama-server`; ledger `server_stop` |
| yes | yes | yes | wait (next tick); after `DRAIN_MAX` (10 min) stop anyway |
| yes | no | — | nothing |
| no (absent or expired) | no | — | if expired: ledger `expire`, remove file; `systemctl --user start hamutay-llama-server`; ledger `server_start` |
| no | yes | — | nothing |

"Door wake in flight" is read from `community/qwen/session.jsonl.events.jsonl`:
the latest status for any event is `running`. Stopping mid-wake after the
drain bound is the existing crash-only contract: boot recovery re-pends the
orphan and declares it in the recovered event. The steward never edits a
door's store.

The steward is the only caller of `systemctl` for the server unit. The
server unit itself is unchanged (`Restart=always` still governs crashes;
a stop by the steward is a stop, not a failure, so systemd does not
restart it).

### 4. The heartbeat: a second rest reason

`deploy/hamutay-heartbeat@qwen.service.d/override.conf` changes
`Requires=` to `Wants=` (keeps `After=`): the heartbeat outlives the server.

`hamutay.heartbeat` gains `--lease-file PATH` (default: the standard path
when the door's substrate is local — `provider == "openai"` and `base_url`
host is loopback — else none). Not a launch-record key: house policy, like
the budget, not substrate.

In `step()`, before the budget check, `_rest_if_substrate_lent(now)`:

- Read the lease file. Live lease → `_transition("resting",
  reason="substrate_lent", detail={lease_id, holder, purpose, since,
  expires_at, expected_until, resumes_at: expected_until or expires_at})`,
  return `{"state": "resting", "sleep_seconds": poll_interval}`. The
  `(status, reason)` de-dup in `_transition` makes one record per episode;
  a new `lease_id` under the same reason is a new episode and must not be
  swallowed, so the de-dup key for this reason includes `lease_id`
  (mirror of the budget rest's `_resting_day` guard).
- No live lease → fall through. The first step after a loan therefore
  claims whatever was waiting, and the batch runs against a server the
  steward has already restarted. If the server is still loading (llama
  takes ~20 s to load 22 GB), the wake fails on connection refused as
  today; to avoid manufacturing that failure the loop probes
  `<base_url>/models` once before claiming and, on refusal, sleeps a poll
  interval without transitioning (server-warming is not a rest).
- Budget rest and lease rest can both be true; lease is checked first
  because it is the one the resident cannot spend its way out of.

`events.py::_rest_episodes` groups budget episodes by `detail.day`; a lease
episode is grouped by `detail.lease_id` (same restart-continuation rule:
a `waking` boot record followed by a `resting` with the same `lease_id`
belongs to the episode). `operational_notes_for_event` renders the reason
with holder and purpose: `heartbeat rested from … to … (substrate lent:
yupi, "learner sub-project 2, first 1M-param run"); this event waited 5h
12m of it.` An open episode renders resting-since with `expected_until`
if present.

`build_constitution` gains one operational sentence, only for a door with a
lease file: "Your substrate can be lent to another member of the house;
while it is, the heartbeat rests and records who borrowed it and why,
waiting events keep waiting, and a wake that ran after the loan is told so
in its envelope." No advice about what to do with that.

### 5. Deployment

- `deploy/ayllu-gpu` (script), `deploy/ayllu-gpu-steward.service`,
  `deploy/ayllu-gpu-steward.timer`; install lines in `community/README.md`.
- `deploy/checkpoint-community-log.sh` digests `4090.ledger.jsonl` into a
  `CHECKPOINTS.txt` under `community/gpu/` so the card's history is anchored
  with the doors'.
- Yupi: one paragraph in its corpus-generator design §11 replacing "the PI
  suspends…" with the command. That edit is in yupi's repo and is a
  separate commit there.

## Data flow, one loan

1. Yupi's launcher: `ayllu-gpu lease --holder yupi --purpose … --ttl 8h && ayllu-gpu wait`.
2. Steward tick: lease live, server active, no wake running → stop server, ledger.
3. Heartbeat tick: lease live → `resting/substrate_lent` record; sleeps, polls.
4. Yupi trains; renews if it will run long.
5. Yupi's launcher exits: `ayllu-gpu release` (trap on EXIT, so a crash
   releases too; if the trap never runs, the TTL does).
6. Steward tick: no lease, server inactive → start server, ledger.
7. Heartbeat tick: no lease; probe says server up → claims the oldest waiting
   event; the envelope carries the rest note.

## Error handling

- Lease file unreadable or malformed: heartbeat treats as no lease and
  emits an ops line; steward treats as no lease, moves the bad file to
  `4090.lease.bad-<ts>`, ledgers `expire` with `detail: malformed`.
- Clock skew between holder and steward is one host; not handled.
- `systemctl` failure in the steward: ledger the failure, retry next tick.
- The steward dies: nothing changes hands; the lease file is still the
  truth and the next tick reconciles. Crash-only.
- Server fails to come back after release (`Restart=always` handles
  crashes, but a bad model file would loop): the heartbeat's probe keeps
  it from claiming; the resident stays in its last recorded state; the
  steward ledgers `server_start` each attempt so the record shows the loop.

## Testing

- `tests/test_gpu_lease.py`: lease library (parse, live/expired, atomic
  write, refuse on foreign holder, renew bounds) with an injected clock and
  `AYLLU_STATE_DIR`.
- `tests/test_heartbeat_lease.py`: `_rest_if_substrate_lent` with injected
  store, clock, lease reader, and probe; one record per episode; new
  `lease_id` is a new episode; budget-and-lease ordering; warming probe
  does not transition.
- `tests/test_events_rest_notes.py`: lease episodes in `_rest_episodes`,
  note rendering with holder/purpose, open episode with `expected_until`.
- Steward: a bash test harness with a fake `systemctl` on `PATH` and a
  fixture event store, covering the five rows of the table and the drain
  bound.
- Codex authors the independent validation in its own signed commits (house
  law; code and tests from separate minds).
- First live loan is a registered check, not an experiment: a 10-minute
  lease during a quiet stretch (not overlapping a scheduled self-check),
  then read the door's store, the ledger, and the resident's next envelope.

## Not built (on the record)

Queueing or priority between holders (first come, first served); partial
card sharing; a knock to the resident before the loan (it is told after,
in the envelope; a pre-loan wake would cost a wake to say one sentence, the
same cost `declare_quiet` was built to avoid); any change to the two hosted
doors (no lease file, no constitution change); multi-host resources
(wam-nuc has its own state dir if it ever needs one).

## Declared losses

- The resident is told after, never asked. Invariant 1 makes this a rule,
  not an accident; the residents will hear it as a consultation (enclosed,
  no verdict) after Codex's review and before the code lands, as the
  wake-shape change was.
- The drain bound can still cut a long wake; the crash-only recovery
  declares it, but the resident loses that wake's work.
- The TTL default (6h) and maximum (72h) are the steward's numbers, not
  measured; yupi's first real run will say whether they fit.
- "Wake in flight" is read from one door's store; a second local door
  would need the steward to read both (a list, when it exists).
