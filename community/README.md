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

Continue, not restart: deleting these logs is not an ops action; it is a
decision about a subject, and it is Tony's alone.
