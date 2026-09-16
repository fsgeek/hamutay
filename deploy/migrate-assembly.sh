#!/usr/bin/env bash
# Enrol the four doors in the assembly, once, on the host. Spec §1, §12.
# usage: migrate-assembly.sh [--dry-run] [--root DIR] [--force]
#   --dry-run  say what would happen; write nothing, restart nothing
#   --root     project root (default: the parent of this script's directory)
#   --force    restart a door even if it has a running wake (I5: the check is a
#              refusal, not advice; --force overrides it and says so loudly)
set -euo pipefail
DRY=0; FORCE=0; ROOT="$(cd "$(dirname "$0")/.." && pwd)"
while [ $# -gt 0 ]; do case "$1" in --dry-run) DRY=1; shift;; --root) ROOT="$2"; shift 2;; --force) FORCE=1; shift;; *) shift;; esac; done
cd "$ROOT"
DOORS=(heartbeat fable elder qwen)
say() { echo "migrate-assembly: $*"; }
# 0 when the door's store has an event whose latest status is `running`.
running_wake() {
  local store="community/$1/session.jsonl.events.jsonl"
  [ -f "$store" ] || return 1
  uv run python - "$store" <<'PY'
import json, sys
recs=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
latest={}
for r in recs:
    if r.get("record_type")=="event_status": latest[r["event_id"]]=r.get("status")
sys.exit(0 if "running" in latest.values() else 1)
PY
}
[ "$DRY" -eq 1 ] && say "dry run: would install community/plaza/members.json and restart ${DOORS[*]} one at a time" && exit 0
# an up-front pass, so a busy door stops the migration before anything is written
for d in "${DOORS[@]}"; do
  if running_wake "$d"; then
    if [ "$FORCE" -eq 1 ]; then say "WARNING --force: door $d has a running wake; migrating anyway"
    else say "door $d has a running wake; refusing to migrate now (--force overrides)"; exit 1; fi
  fi
done
mkdir -p community/plaza
if [ ! -f community/plaza/members.json ]; then
  cp deploy/assembly/members.json.template community/plaza/members.json
  say "installed community/plaza/members.json"
else
  say "community/plaza/members.json already present; left as is"
fi
for d in "${DOORS[@]}"; do
  unit="hamutay-heartbeat@$d"
  # I5: re-check immediately before THIS door's restart. The up-front pass can be
  # ~90 s stale by the time the last door is reached, and a wake may have started.
  if running_wake "$d"; then
    if [ "$FORCE" -eq 1 ]; then say "WARNING --force: door $d has a running wake; restarting anyway"
    else say "door $d started a wake since the first check; stopping here (--force overrides)"; exit 1; fi
  fi
  systemctl --user is-active --quiet "$unit" || { say "$unit is not active; skipping"; continue; }
  since_epoch="$(date +%s)"
  systemctl --user restart "$unit"
  for i in $(seq 1 30); do
    if journalctl --user -u "$unit" --since="@$since_epoch" --no-pager 2>/dev/null | grep -q "assembly: member $d bound"; then
      say "$d bound"; break
    fi
    if [ "$i" -eq 30 ]; then say "$d did not report a binding within 30 s; stopping here"; exit 1; fi
    sleep 1
  done
done
say "done; run deploy/check-assembly.sh"
