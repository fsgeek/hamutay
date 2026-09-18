#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"; rc=0; PHASE_ONE=0; MERGE="${PLAZA_MERGE:-}"
while [ $# -gt 0 ]; do case "$1" in --phase-one) PHASE_ONE=1; shift;; --merge) MERGE="$2"; shift 2;; *) shift;; esac; done
chk() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; rc=1; fi; }
inv_note() { local inv; inv=$(systemctl --user show -p InvocationID --value "hamutay-heartbeat@$1"); [ -n "$inv" ] && journalctl --user -u "hamutay-heartbeat@$1" _SYSTEMD_INVOCATION_ID="$inv" --no-pager 2>/dev/null | grep -o "$2" | tail -1; }
for d in heartbeat fable elder qwen; do
  chk "unit $d active" "systemctl --user is-active --quiet hamutay-heartbeat@$d"
  chk "unit $d source clean and descended from $MERGE" "n=\$(inv_note $d 'source: commit [0-9a-f]\{40\} clean') && [ -n \"\$n\" ] && git merge-base --is-ancestor '$MERGE' \$(echo \$n | awk '{print \$3}')"
  [ "$PHASE_ONE" -eq 1 ] || chk "unit $d plaza bound" "[ -n \"\$(inv_note $d 'plaza: door $d may send')\" ]"
done
if [ "$PHASE_ONE" -eq 0 ]; then
  chk "members.json has the plaza key" "uv run python -c 'from hamutay.assembly.binding import load_members; import pathlib, sys; sys.exit(0 if load_members(pathlib.Path(\".\")).plaza else 1)'"
  chk "plaza status valid" "deploy/ayllu-plaza status >/dev/null"
fi
chk "gitignore rules" "grep -q '^community/plaza/plaza.jsonl$' .gitignore && grep -q 'community/plaza/plaza.jsonl.lock' .gitignore"
chk "checkpoint names both plaza locks" "grep -q assembly.jsonl.lock deploy/checkpoint-community-log.sh && grep -q plaza.jsonl.lock deploy/checkpoint-community-log.sh"
exit $rc
