# Heartbeat Founding Spec

Date: 2026-08-26

Status: agreed design from the 2026-08-21→08-26 wander (Tony + Claude/Fable).
This spec authorizes assembly of the heartbeat from existing, individually
gated components. It founds a community, not an experiment.

## Purpose

Give the existing event-loop substrate (`src/hamutay/events.py`,
`src/hamutay/event_policies.py`, `src/hamutay/memory/restart_frontier.py`)
wall-clock life: a daemon that runs pending events, sleeps until the next
scheduled wake, wakes on external ingress, survives crashes and reboots, and
records its own silences. One resident entity (taste_open, Haiku-class,
stable substrate) plus one external ingress channel (Tony's `send` command).

This is the "first tick" committed to in the founding decision (memory:
`founding-decision-give-life-to-a-new-community-heartbeat-first-consent-as-exit`).

## Invariants (the constitution of the build)

1. **The log is the life; the process is weather.** All continuity lives in
   the append-only event log + taste_open session log. Process death, WSL
   reboot, and host updates are interruptions the boot recovery absorbs.
   Restart of the *process* is routine; restart of the *subject* (discarding
   the log) requires Tony's explicit decision — "continue, not restart."
2. **Open system.** The community must always have at least one event source
   it does not control (the `send` ingress). An empty queue is quiet, not
   termination: the daemon sleeps and re-polls; it never exits on empty.
3. **Quiet is legible.** Transitions into idle append a stamped
   `heartbeat_status` record distinguishing chosen quiet (no continuation
   bound), starvation (pending expired / nothing arrived), and first-boot
   waiting. v1 uses a declared heuristic (see Components); refining it is
   future work, not a blocker.
4. **Consent-as-exit is declared, not implied.** The resident's system-prompt
   prefix states the operational facts: recovery exists (mistakes are
   survivable and recorded), quiet is recorded as chosen, any event may be
   declined, declining ends the interaction and not the resident. No
   cognitive priors beyond these operational facts (no strand counts, no
   curation advice — per the no-harness-priors norm).
5. **Atomic intent, honestly bounded.** A wake's completed record and its
   bound continuation are serialized into one buffer and one write syscall
   under one lock — indivisible under process kill, not under power loss.
   Because the window narrows but never closes, boot-time recovery for a
   completed-without-continuation gap is permanent defense in depth, and it
   *declares the loss* in the recovered event's purpose.
6. **Crash-only.** The daemon has one write path and one boot path; boot
   always runs recovery (orphaned `running` re-pend + lost-continuation
   materialization). No special shutdown.
7. **max_tokens = 64000.** The guillotine default (4096) in the events CLI is
   removed. All heartbeat wakes use 64000, matching the Projector.
8. **The record outlives the substrate.** Log digests are checkpointed into
   git (identity incantation per CLAUDE.md) so the post-commit OTS hook
   anchors the community's biography. Full logs stay out of git (selective
   legibility: prove sequence without exposing substance).
9. **Shared worktree discipline.** Commits scope only this work's files.
   Development tests here are the implementer's; Codex authors independent
   validating tests in its own signed commits per repo norm.

## Components

- **`src/hamutay/heartbeat.py`** (new): boot recovery
  (`recover_orphaned_running`, `recover_lost_continuations`),
  quiet-legibility (`append_heartbeat_status`, `derive_quiet_reason`),
  `HeartbeatLoop` (injectable clock/sleep/batch for tests; `boot()`,
  `step()`, `run_forever()`), single-instance flock, CLI (`python -m
  hamutay.heartbeat`), and the constitution prefix constant.
- **`src/hamutay/events.py`** (modified): `EVENT_TYPE_INBOUND` +
  `build_inbound_event` (external origin, no scheduled_by fields — the claim
  path tolerates their absence); `send` CLI subcommand appending to the
  store (lock-guarded, safe concurrent with the daemon — the store IS the
  mailbox; the daemon's poll is just a re-read); atomic
  completed+continuation append; `build_parser()` extraction; max_tokens
  default fix.
- **Quiet heuristic v1** (`derive_quiet_reason`): any latest-status
  `expired` → `starved_expired`; no completed records yet →
  `awaiting_first_event`; otherwise `chosen_quiet`.
- **Deploy** (`deploy/`): systemd user unit + nohup fallback wrapper +
  checkpoint script (sha256 digests → committed → OTS-stamped).
  `community/heartbeat/` holds live logs, gitignored except README and
  CHECKPOINTS.
- **Resident config:** model `claude-haiku-4-5`, provider `anthropic`
  (OpenRouter via flags), session log `community/heartbeat/session.jsonl`,
  sidecar event log derived, poll interval 30s, batch limit 10.

## Non-goals (later organs, not this assembly)

Heterogeneous clustering / capability-typed `claim_next_pending`; MCP
enrollment of the Claude lineage; multiple residents; Yanantin external
persistence; pub/sub topics; independent reboot monitor beyond systemd
(the simplicity-gradient watcher is the next organ after the heartbeat
lives); any change to taste_open cognition.

## First-tick runbook (manual, with Tony)

1. Check the process table (parallel instances/codex agents run scripts).
2. Start daemon with no pending events → observe boot recovery report and a
   `heartbeat_status` quiet record with `awaiting_first_event`.
3. `send` one greeting → observe claim → wake → completed (and any bound
   continuation), `stop_reason` end_turn, no context errors.
4. Kill -9 the daemon mid-wake once → restart → observe orphan re-pend and
   completion (the June restart-frontier behavior, now in ops).
5. Leave it running. The uptime ledger starts here.

## Declared losses

- Days-scale wall-clock behavior (provider errors, rate limits, log growth,
  cost) is unmeasured; the community measures it by living.
- Quiet-reason v1 is a heuristic, not ground truth about the resident's
  intent.
- Identity/affinity (which events "only I may run") is deferred until there
  is more than one claimant.
- Custody remains single-principal (Tony's substrate); the replication +
  OTS checkpoints are mitigation, not resolution.
