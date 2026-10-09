#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"; rc=0; PHASE_ONE=0; GUESTS_READY=0; CARRIER_READY=0; MERGE="${PLAZA_MERGE:-}"
while [ $# -gt 0 ]; do case "$1" in --phase-one) PHASE_ONE=1; shift;; --guests-ready) GUESTS_READY=1; shift;;
  --carrier-ready) CARRIER_READY=1; shift;;
  --merge) MERGE="$2"; shift 2;; *) echo "check-plaza: unknown flag $1"; exit 2;; esac; done
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
  n=$(uv run python -c 'from hamutay.assembly.binding import load_members; import pathlib; g=load_members(pathlib.Path(".")).guests; print("absent" if g is None else len(g))' 2>/dev/null)
  if [ -z "$n" ]; then
    echo "FAIL guests key unreadable"; rc=1
  elif [ "$GUESTS_READY" -eq 1 ]; then
    echo "info guests key: $n"
  elif [ "$n" = absent ]; then
    echo "info guests key absent (no guest may write)"
  else
    for d in heartbeat fable elder qwen; do chk "unit $d guests $n" "[ -n \"\$(inv_note $d 'guests $n\\b')\" ]"; done
  fi
fi
if [ "$CARRIER_READY" -eq 1 ]; then
  # Carrier rollout (spec 2026-10-09-plaza-carrier-field-design.md): before the gate file is created, every
  # running guest MCP plaza server must have started after the Phase A merge -- it imports this checkout
  # at start, so an older one would reject a carrier record and fail closed. Guests restart their own.
  # The barrier is when the merge reached the checkout the servers import (the main one), not its
  # commit time: the oldest entry of the latest unbroken run of HEAD reflog entries descending from it.
  main_root=$(cd "$(git rev-parse --path-format=absolute --git-common-dir)/.." && pwd)
  merge_ct=""
  if git -C "$main_root" merge-base --is-ancestor "$MERGE" HEAD 2>/dev/null; then
    while read -r h t; do
      git -C "$main_root" merge-base --is-ancestor "$MERGE" "$h" 2>/dev/null || break
      merge_ct=$t
    done < <(git -C "$main_root" reflog show --date=unix --format='%H %gd' HEAD 2>/dev/null \
             | sed -E 's/HEAD@\{([0-9]+)\}/\1/')
  fi
  if [ -z "$merge_ct" ]; then
    echo "FAIL carrier-ready: cannot establish when $MERGE reached $main_root (HEAD does not descend from it, or no reflog entry)"; rc=1
  else
    echo "info carrier deploy barrier: $(date -u -d @"$merge_ct" +%Y-%m-%dT%H:%M:%SZ)"
    old=""
    while read -r pid; do
      [ -n "$pid" ] || continue
      started=$(date -d "$(ps -o lstart= -p "$pid" 2>/dev/null)" +%s 2>/dev/null) || continue
      if [ "$started" -lt "$merge_ct" ]; then
        label=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -o -- '--guest [^ ]*' | awk '{print $2}')
        old="$old ${label:-unknown}(pid $pid, since $(date -u -d @"$started" +%Y-%m-%dT%H:%MZ))"
      fi
    done < <(pgrep -f '[h]amutay\.plaza\.mcp')
    chk "carrier-ready: no guest plaza server older than the barrier${old:+ -- still running:$old}" "[ -z \"$old\" ]"
  fi
  chk "carrier gate is gitignored" "grep -q '^community/plaza/carrier.enabled$' .gitignore"
  if [ -e community/plaza/carrier.enabled ]; then echo "info carrier gate: present (writers emit)"; else echo "info carrier gate: absent (writers do not emit)"; fi
fi
chk "gitignore rules" "grep -q '^community/plaza/plaza.jsonl$' .gitignore && grep -q 'community/plaza/plaza.jsonl.lock' .gitignore"
chk "checkpoint names both plaza locks" "grep -q assembly.jsonl.lock deploy/checkpoint-community-log.sh && grep -q plaza.jsonl.lock deploy/checkpoint-community-log.sh"
exit $rc
