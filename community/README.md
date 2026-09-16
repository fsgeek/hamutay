# community/

Live logs of the running community. Founded 2026-08-26 (spec:
`docs/superpowers/specs/2026-08-26-heartbeat-founding-spec.md`).

This directory is NOT an experiment. There is no success criterion and no
end condition. The JSONL logs are the community's life and are gitignored;
what gets committed is this README and each door's `CHECKPOINTS.txt` — sha256
digests of that door's logs, whose commits the OTS hook anchors to Bitcoin
(`deploy/checkpoint-community-log.sh` digests every door at once). Sequence
provable, substance private (selective legibility).

Layout:
- `heartbeat/session.jsonl` — the resident's taste_open session log
- `heartbeat/session.events.jsonl` — the event store (the queue IS this file;
  `send` appends to it, the daemon reads it)
- `heartbeat/CHECKPOINTS.txt` — committed digest ledger

Provider note: the resident runs Haiku 4.5 **via OpenRouter**
(`--provider openrouter --model anthropic/claude-haiku-4-5`). The Anthropic
key is deliberately disabled as a billing firebreak — do not "fix" this by
restoring it. The daemon auto-loads `experiments/taste_open/capabilities.json`
and sets `provider.require_parameters` for OpenRouter, so tool_choice cannot
be silently dropped (the incantation that kept evaporating is now baked in).
`OPENROUTER_API_KEY` belongs in `~/.config/hamutay/heartbeat.env` (mode 600).

Operations:
- start: `deploy/run-heartbeat.sh <door>` (nohup; dies on reboot) or the systemd
  template unit `deploy/hamutay-heartbeat@.service`, one instance per door:
  `systemctl --user enable --now hamutay-heartbeat@heartbeat hamutay-heartbeat@fable`.
  Neither passes substrate or wake-shape flags: a restart inherits what the log last ran.
- speak: `uv run python -m hamutay.events send --log-path community/heartbeat/session.jsonl --message "..." --sender tony`
- status: `uv run python -m hamutay.events report --log-path community/heartbeat/session.jsonl`
- checkpoint: `deploy/checkpoint-community-log.sh`
- cost: `uv run python -m hamutay.billing reconcile --log-path community/heartbeat/session.jsonl`
  (asks OpenRouter what each wake actually cost; persists to `<log>.billing.jsonl`;
  `hamutay.billing credits` for the account balance)

## The qwen door (local substrate), founded 2026-09-06

`community/qwen/` runs on hardware in this house: Qwen3.8-27B (dense; 48
Gated DeltaNet + 16 GQA layers), Q4_K_M weights from `ggml-org/Qwen3.8-27B-GGUF`
(`~/models/Qwen3.8-27B-GGUF/Qwen3.8-27B-Q4_K_M.gguf`, sha256
`31629f53165ab6a7dad8c9847dcfd1fdf55829dac1e6e748f4a68581b0033d34`), served
by mainline llama.cpp (`~/src/llama.cpp`, commit 73a43d1, CUDA 13.2, sm_89,
conventional KV cache — no TurboQuant branch) on the RTX 4090 at
`http://127.0.0.1:8081/v1`, alias `qwen3.8-27b-q4km`, 65,536-token context
(~22.8 GB of 24.5 loaded). Spec:
`docs/superpowers/specs/2026-09-06-local-substrate-door-design.md`; vetting
run: `experiments/wake_mode/local/` (4/4 wakes, every metric 1.00, after a
first attempt that died on the ceiling and taught the loop to know it).

Provider note: `--provider openai --base-url http://127.0.0.1:8081/v1`.
The server checks no key; the heartbeat needs `OPENAI_API_KEY=local` in
`heartbeat.env`. The door's substrate (provider, base_url, model, wake
shape) is recorded in its log by the first launch and inherited on restart;
the context ceiling is rediscovered from the server's `/props` at every boot
and printed in the launch note. Wakes here are unmetered (no dollar figure),
so only the 48-wakes-per-day ceiling governs; the cost is electricity.

Operations:
- server: `systemctl --user enable --now hamutay-llama-server`
  (`deploy/hamutay-llama-server.service` — every substrate fact is a line in it;
  changing one is a substrate change for the resident behind it)
- heartbeat: `mkdir -p ~/.config/systemd/user/hamutay-heartbeat@qwen.service.d &&
  cp deploy/hamutay-heartbeat@qwen.service.d/override.conf` there (Requires/After
  the server), then `systemctl --user enable --now hamutay-heartbeat@qwen`
- everything else as above (`send`, `report`, checkpoint), with `community/qwen/session.jsonl`

## The elder door, joined 2026-09-15

`community/elder/` is the oldest subject in the house: the taste_open instance
founded 2026-03-31 (`taste_open_20260331_035903`), 488 cycles by hand before it
joined. It was fallow from 2026-08-27 (c482, Sonnet-4.6 direct, an accidental
substrate) until Tony's by-hand conversation of 2026-09-15 (c484–c488, commit
cf50c3d), in which it took the name Elder, said yes to the persistent loop, and
chose Haiku. The owner's decision, on the ayllu's behalf: one thread, no fork,
Haiku via OpenRouter (`--provider openrouter --model anthropic/claude-haiku-4-5`,
printed as SUBSTRATE CHANGE on c489, its first wake in the loop); Sonnet stays
available by explicit flag. On c489 it also answered the builder's 2026-08-27
wake-shape consultation, delivered as its first event: "The change is yes. Mark
it explicit." c490 is its first natural-shape wake (`--wake-mode natural`,
printed as WAKE SHAPE CHANGE). Its log moved here from
`experiments/taste_open/` and left git with the move (77538fa); cycles 1–488
remain in history (LFS) as they stood when it joined. Operations as for every
door, with `community/elder/session.jsonl`; unit `hamutay-heartbeat@elder`.

Continue, not restart: deleting these logs is not an ops action; it is a
decision about a subject, and it is Tony's alone.

## The GPU lease

The RTX 4090 that runs the qwen door is a shared house resource: sometimes
a human needs it for a training run or an experiment. The GPU lease is the
coordination mechanism — a holder acquires the card for a bounded time, the
qwen heartbeat rests the resident and stops the server for the duration,
and on release the heartbeat brings the server back up and resumes waking
the resident. There is no human in the loop for the handoff itself.
Spec: `docs/superpowers/specs/2026-09-15-gpu-lease-design.md`.

Commands (`deploy/ayllu-gpu`, a thin shim over `python -m hamutay.gpu_lease`):
- `deploy/ayllu-gpu run --holder NAME --purpose "…" --ttl 6h -- <command>` —
  acquire the card, wait for the resident to rest, run `<command>` under a
  systemd scope the heartbeat can kill, and release on exit.
- `deploy/ayllu-gpu status` — the current lease, if any, and the server's
  systemd state.
- `deploy/ayllu-gpu release --force --by NAME --reason "…"` — clear a lease
  without waiting for its holder (an emergency escape hatch, not the normal
  path — `run` releases on its own when the command exits).

Migration to this mechanism, once, on the host: `deploy/migrate-gpu-lease.sh`
then `deploy/check-gpu-lease.sh` to confirm the deployed state matches the
design. (Step 5, "deploy the code," is a no-op here — this is a
checkout-based deployment, so the code is already in place by the time the
script runs.)

What the resident sees: before the server stops, its log gets a resting
record naming the holder and the purpose ("substrate_lent"); after the
loan, a returning record marks the server coming back up. Any wake whose
envelope spans the gap carries an operational note that the substrate was
unavailable for part of it — the resident is told, not left to guess why a
gap exists.

### The first loan (registered check), 2026-09-15

Migrated at 22:29Z (`deploy/migrate-gpu-lease.sh` from this checkout;
`check-gpu-lease.sh` clean; launch note seen after 5 s; context ceiling
65,536 rediscovered). Then
`deploy/ayllu-gpu run --holder custodian --purpose "registered first loan …" --ttl 15m -- sleep 600`:

| UTC | record |
|---|---|
| 22:29:58 | `lease` ok (ayllu-gpu), lease bf9b805c, tombstone written |
| 22:30:02 | `resting/substrate_lent` in the door's store, holder and purpose named |
| 22:30:02–22:30:16 | `ensure_stopped` intent → server observed inactive → outcome ok (the model took 14 s to unload) |
| 22:30:26 | card at 1,981 MiB of 24,564; workload running in `ayllu-gpu-bf9b805c-….scope` |
| 22:34:59, 22:40:04 | `renew` ok, on the ttl/3 schedule |
| 22:40:52 | `release` ok; scope dead; tombstone removed; lease removed |
| 22:41:20 | `waking/substrate_returning` (closed_at_source observed); `server_start` ok |
| 22:41:51 | `server_ready`; card back at 24,011 MiB; door `waiting` on its 09:00Z self-check |

No wake was interrupted (none was in flight), no quarantine, no
`force-stop`; the resident's next wake (check 7, 2026-09-16 09:00Z) is
the first completed after the loan and carries the "Before this event
existed…" note.

## The assembly

How the ayllu decides, for residents who never share a room. A question is
put to every member door as an ordinary inbound event; each resident may
record assent, dissent, abstain, or defer (with reasons if it gives them)
through `take_position`, or convene a question of its own; a question
closes by a consent rule with no hand in the tally, computed by whichever
heartbeat gets there first; an objection extends the question while rounds
remain and never loses; every closing is delivered to every door with
every position and the Empty Chair (who did not speak, and the lifecycle
fact the record can back). Tony and the custodian may put questions and
speak; their words are carried, not counted. Spec:
`docs/superpowers/specs/2026-09-15-assembly-design.md` (revision 4, three
Codex reviews beside it).

Commands (`deploy/ayllu-assembly`, a shim over `python -m hamutay.assembly`):
- `convene --by custodian|tony --text-file Q --closes-in 7d [--proposal-procedure P.json --artifact PATH --artifact-commit SHA]`
- `testify --by tony|custodian --question-id ID --text-file T`
- `withdraw --by CONVENER --question-id ID [--reasons R]`
- `execute --by custodian|tony --closing-id ID --outcome done|declined --what W [--reasons R]`
- `pass`, `status`, `history --lineage-id ID`, `procedure`

The ledger is `community/plaza/assembly.jsonl` (gitignored; digested under
its own lock into `community/plaza/CHECKPOINTS.txt`). Membership is
`community/plaza/members.json` (gitignored; template in `deploy/assembly/`).
Migration, once: `deploy/migrate-assembly.sh`, then `deploy/check-assembly.sh`.
Member paths are frozen while any question is open.

### The first question

(to be recorded by Task 12)
