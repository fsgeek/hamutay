#!/usr/bin/env bash
# Enable the plaza in two phases. Spec §9.
# usage: migrate-plaza.sh --phase-one|--phase-two [--dry-run] [--root DIR] [--merge SHA]
#   --phase-one  restart idle doors one at a time so every unit runs plaza-capable code (key absent)
#   --phase-two  with every door idle: candidate members.json checked, stop all, atomic install, start all, verify
#   --merge SHA  the plaza merge commit every running unit must descend from (default: env PLAZA_MERGE)
#   --dry-run    perform every precondition check and print its verdict ("ok: <check>" or
#                "would refuse: <reason>"), then print the plan; writes nothing, restarts
#                nothing, always exits 0 (a dry run is a preview, not a partial run)
set -euo pipefail
PHASE=""; DRY=0; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; MERGE="${PLAZA_MERGE:-}"
while [ $# -gt 0 ]; do case "$1" in --phase-one) PHASE=one; shift;; --phase-two) PHASE=two; shift;;
  --dry-run) DRY=1; shift;; --root) ROOT="$2"; shift 2;; --merge) MERGE="$2"; shift 2;; *) shift;; esac; done
[ -n "$PHASE" ] || { echo "migrate-plaza: --phase-one or --phase-two"; exit 2; }
cd "$ROOT"
DOORS=(heartbeat fable elder qwen)
say() { echo "migrate-plaza: $*"; }
running_wake() {
  local store="community/$1/session.jsonl.events.jsonl"; [ -f "$store" ] || return 1
  uv run python - "$store" <<'PY'
import json, sys
latest={}
for l in open(sys.argv[1]):
    if l.strip():
        r=json.loads(l)
        if r.get("record_type")=="event_status": latest[r["event_id"]]=r.get("status")
sys.exit(0 if "running" in latest.values() else 1)
PY
}
inv_note() {  # $1 door, $2 grep pattern → the matching note of the CURRENT invocation, or empty
  local inv; inv=$(systemctl --user show -p InvocationID --value "hamutay-heartbeat@$1")
  [ -n "$inv" ] || return 0
  journalctl --user -u "hamutay-heartbeat@$1" _SYSTEMD_INVOCATION_ID="$inv" --no-pager 2>/dev/null | grep -o "$2" | tail -1
}
source_ok() {  # $1 door: the current invocation's source note is a clean descendant of $MERGE
  local note; note=$(inv_note "$1" 'source: commit [0-9a-f]\{40\} \(clean\|dirty\)')
  [ -n "$note" ] || { say "$1: no source note in its current invocation"; return 1; }
  local sha state; sha=$(echo "$note" | awk '{print $3}'); state=$(echo "$note" | awk '{print $4}')
  [ "$state" = clean ] || { say "$1: source is dirty ($sha)"; return 1; }
  git merge-base --is-ancestor "$MERGE" "$sha" || { say "$1: $sha does not descend from $MERGE"; return 1; }
}
# an up-front pass over all four doors: report every door's idleness before touching
# anything (dry run: each door's own ok/would-refuse line; live run: refuse on the first).
idleness_upfront() {
  local any_busy=0
  for d in "${DOORS[@]}"; do
    if running_wake "$d"; then
      any_busy=1
      if [ "$DRY" -eq 1 ]; then say "would refuse: door $d has a running wake"
      else say "door $d has a running wake; refusing to migrate now"; exit 1; fi
    elif [ "$DRY" -eq 1 ]; then say "ok: door $d idle"
    fi
  done
  return $any_busy
}
if [ "$PHASE" = one ]; then
  idleness_upfront
  [ "$DRY" -eq 1 ] && say "dry run: would restart ${DOORS[*]} one at a time when idle (plaza key stays absent)" && exit 0
  for d in "${DOORS[@]}"; do
    unit="hamutay-heartbeat@$d"
    # re-check immediately before THIS door's restart: the up-front pass can be
    # stale by the time the last door is reached, and a wake may have started since.
    running_wake "$d" && { say "door $d started a wake since the first check; stopping here"; exit 1; }
    systemctl --user is-active --quiet "$unit" || { say "$unit is not active; skipping"; continue; }
    since=$(date +%s); systemctl --user restart "$unit"
    for i in $(seq 1 30); do
      journalctl --user -u "$unit" --since="@$since" --no-pager 2>/dev/null | grep -q "assembly: member $d bound" && { say "$d restarted"; break; }
      [ "$i" -eq 30 ] && { say "$d did not report a binding within 30 s; stopping here"; exit 1; }
      sleep 1
    done
  done
  say "phase one done; run deploy/check-plaza.sh --phase-one --merge <sha>"; exit 0
fi
# phase two
if [ "$DRY" -eq 1 ]; then
  if [ -n "$MERGE" ]; then say "ok: --merge given ($MERGE)"; else say "would refuse: --merge SHA (or PLAZA_MERGE) is required for phase two"; fi
  if [ -z "$(git status --porcelain)" ]; then say "ok: working tree clean"; else say "would refuse: working tree is dirty"; fi
  if [ -n "$MERGE" ] && git merge-base --is-ancestor "$MERGE" HEAD 2>/dev/null; then say "ok: HEAD descends from $MERGE"
  else say "would refuse: HEAD does not descend from $MERGE"; fi
  for d in "${DOORS[@]}"; do
    if [ -n "$MERGE" ] && source_ok "$d" >/dev/null 2>&1; then say "ok: door $d source clean and descended from $MERGE"
    else say "would refuse: door $d phase one incomplete (no verified source note descended from $MERGE)"; fi
  done
  idleness_upfront || true
  say "dry run: would check phase one, stop ${DOORS[*]}, install the plaza key atomically, start them, verify both notes"
  exit 0
fi
[ -n "$MERGE" ] || { say "--merge SHA (or PLAZA_MERGE) is required for phase two"; exit 2; }
[ -z "$(git status --porcelain)" ] || { say "working tree is dirty; refusing"; exit 1; }
git merge-base --is-ancestor "$MERGE" HEAD || { say "HEAD does not descend from $MERGE; refusing"; exit 1; }
for d in "${DOORS[@]}"; do source_ok "$d" || { say "phase one incomplete; refusing"; exit 1; }; done
idleness_upfront
MEMBERS=community/plaza/members.json
cp "$MEMBERS" "$MEMBERS.previous"
# candidate: current file plus the plaza key, written durably beside it, then its snapshot compared BEFORE any rename
if ! uv run python - "$MEMBERS" <<'PY'
import json, os, sys, hashlib
from pathlib import Path
from hamutay.assembly.binding import load_members
p = Path(sys.argv[1]); root = Path(".").resolve()
raw = json.loads(p.read_text())
raw["plaza"] = "community/plaza/plaza.jsonl"
cand = p.with_name("members.json.candidate")
with cand.open("w") as f:
    json.dump(raw, f, indent=1); f.write("\n"); f.flush(); os.fsync(f.fileno())
before = load_members(root).snapshot()
tmpdir = Path("/tmp") / f"plaza-cand-{os.getpid()}" / "community" / "plaza"; tmpdir.mkdir(parents=True)
(tmpdir / "members.json").write_bytes(cand.read_bytes())
# load_members resolves paths under ITS root; compare the RELATIVE snapshot shapes instead
def rel(snap, base):
    return {k: {kk: os.path.relpath(vv, base) for kk, vv in v.items()} for k, v in snap.items()}
after = load_members(tmpdir.parents[1]).snapshot()
if rel(before, root) != rel(after, tmpdir.parents[1]):
    cand.unlink(); print("candidate would change the member snapshot; nothing installed"); sys.exit(1)
print("candidate snapshot equal; ready")
PY
then
  rm -f "$MEMBERS.previous"; exit 1
fi
STOPPED=()
rollback() {
  local rc=$?
  trap - ERR
  say "rolling back (exit $rc)"
  # Restore members.json from the snapshot taken before any door was touched,
  # then start only the doors THIS attempt actually stopped (recorded in
  # STOPPED as each stop succeeded) -- never a door the attempt never reached,
  # and never a door twice.
  rm -f "$MEMBERS.candidate"
  if [ -f "$MEMBERS.previous" ]; then
    uv run python - "$MEMBERS" <<'PY'
import os, sys
from pathlib import Path
p = Path(sys.argv[1]); prev = p.with_name("members.json.previous"); tmp = p.with_name("members.json.rollback")
tmp.write_bytes(prev.read_bytes())
with tmp.open("rb+") as f: os.fsync(f.fileno())
os.replace(tmp, p); fd = os.open(p.parent, os.O_RDONLY); os.fsync(fd); os.close(fd)
PY
  fi
  for d in "${STOPPED[@]:-}"; do [ -n "$d" ] && systemctl --user start "hamutay-heartbeat@$d" 2>/dev/null || true; done
  exit 1
}
trap rollback ERR
for d in "${DOORS[@]}"; do
  # re-check immediately before THIS door's stop: the up-front pass can be stale
  # by the time the last door is reached, and a wake may have started since. Once
  # any door has been stopped, a busy door found here means rolling the stopped
  # ones back rather than refusing clean, so this goes through the ERR trap too.
  if running_wake "$d"; then say "door $d started a wake since the first check; stopping here"; false; fi
  systemctl --user stop "hamutay-heartbeat@$d"; STOPPED+=("$d")
done
uv run python - "$MEMBERS" <<'PY'
import os, sys
from pathlib import Path
p = Path(sys.argv[1]); cand = p.with_name("members.json.candidate")
os.replace(cand, p)                       # atomic rename
fd = os.open(p.parent, os.O_RDONLY); os.fsync(fd); os.close(fd)
PY
for d in "${DOORS[@]}"; do systemctl --user start "hamutay-heartbeat@$d"; done
for d in "${DOORS[@]}"; do
  ok=0
  for i in $(seq 1 30); do
    if [ -n "$(inv_note "$d" "plaza: door $d may send")" ] && source_ok "$d" >/dev/null 2>&1; then ok=1; say "$d: plaza bound, source verified"; break; fi
    sleep 1
  done
  if [ "$ok" -ne 1 ]; then say "$d did not report both notes within 30 s"; false; fi
done
trap - ERR
rm -f "$MEMBERS.previous"
say "phase two done; run deploy/check-plaza.sh --merge $MERGE"
