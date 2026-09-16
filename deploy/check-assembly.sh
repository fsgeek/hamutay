#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"; rc=0
chk() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; rc=1; fi; }
chk "members.json loads" "uv run python -c 'from hamutay.assembly.binding import load_members; import sys; sys.exit(0 if load_members(__import__(\"pathlib\").Path(\".\")) else 1)'"
for d in heartbeat fable elder qwen; do
  chk "unit $d active" "systemctl --user is-active --quiet hamutay-heartbeat@$d"
  chk "unit $d bound" "journalctl --user -u hamutay-heartbeat@$d --no-pager 2>/dev/null | grep 'assembly:' | tail -1 | grep -q bound"
done
chk "status exits 0" "deploy/ayllu-assembly status >/dev/null"
chk "gitignore rules" "grep -q community/plaza/members.json .gitignore && grep -q community/plaza/assembly.jsonl.lock .gitignore"
chk "checkpoint under lock" "grep -q assembly.jsonl.lock deploy/checkpoint-community-log.sh"
exit $rc
