#!/usr/bin/env bash
# Enrol the four doors in the assembly, once, on the host. Spec §1, §12.
set -euo pipefail
DRY=0; ROOT="$(cd "$(dirname "$0")/.." && pwd)"
while [ $# -gt 0 ]; do case "$1" in --dry-run) DRY=1; shift;; --root) ROOT="$2"; shift 2;; *) shift;; esac; done
cd "$ROOT"
DOORS=(heartbeat fable elder qwen)
say() { echo "migrate-assembly: $*"; }
[ "$DRY" -eq 1 ] && say "dry run: would install community/plaza/members.json and restart ${DOORS[*]} one at a time" && exit 0
for d in "${DOORS[@]}"; do
  store="community/$d/session.jsonl.events.jsonl"
  [ -f "$store" ] || continue
  if uv run python - "$store" <<'PY'
import json, sys
recs=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
latest={}
for r in recs:
    if r.get("record_type")=="event_status": latest[r["event_id"]]=r.get("status")
sys.exit(0 if "running" in latest.values() else 1)
PY
  then say "door $d has a running wake; refusing to migrate now"; exit 1; fi
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
