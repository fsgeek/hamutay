#!/usr/bin/env bash
# Nohup fallback for environments without a systemd user session.
# NOTE: nohup does NOT survive reboot; prefer the systemd unit.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p community/heartbeat
nohup uv run python -m hamutay.heartbeat \
  --log-path community/heartbeat/session.jsonl \
  --project-root . \
  >> community/heartbeat/daemon.out 2>&1 &
echo "heartbeat started, pid $!"
