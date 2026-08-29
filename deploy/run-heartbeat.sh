#!/usr/bin/env bash
# Nohup fallback for environments without a systemd user session.
# NOTE: nohup does NOT survive reboot; prefer the systemd template unit.
#
# Usage: deploy/run-heartbeat.sh [door]     (default door: heartbeat)
#   door = directory under community/ holding session.jsonl; e.g. heartbeat, fable
#
# No substrate or wake-shape flags here on purpose: a restart inherits what
# the log last ran (model, provider, wake shape), and a brand-new log takes
# the heartbeat's defaults. Passing flags here would silently move a resident
# back to whatever this file said every time it restarted. The log knows
# what it ran; this script does not get a vote. To change a resident on
# purpose, run the daemon by hand with the flag; it prints the change loudly.
set -euo pipefail
cd "$(dirname "$0")/.."
door="${1:-heartbeat}"
mkdir -p "community/$door"
nohup uv run python -m hamutay.heartbeat \
  --log-path "community/$door/session.jsonl" \
  --project-root . \
  >> "community/$door/daemon.out" 2>&1 &
echo "heartbeat for community/$door started, pid $!"
