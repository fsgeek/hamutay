#!/usr/bin/env bash
# Append sha256 digests of point-in-time snapshots of the community logs to
# the committed ledger, then commit with hamutay's identity so the OTS
# post-commit hook stamps it.
#
# Semantics: the logs are append-only, so a digest of a byte snapshot is a
# valid commitment to the history up to that point even while the daemon
# keeps appending. We snapshot with cp first so each hashed file is
# internally coherent, and record its byte length beside the digest.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! git diff --cached --quiet; then
  echo "refusing to checkpoint: index has staged changes (shared worktree)" >&2
  exit 1
fi

# One ledger per door: community/<door>/CHECKPOINTS.txt. Every door's
# JSONL logs (session, events, billing) are digested; the logs themselves
# stay gitignored (selective legibility: sequence provable, substance private).
shopt -s nullglob
doors=()
for d in community/*/; do
  d=${d%/}
  logs=("$d"/*.jsonl)
  [ ${#logs[@]} -gt 0 ] && doors+=("$d")
done
if [ ${#doors[@]} -eq 0 ]; then
  echo "no community logs yet; nothing to checkpoint" >&2
  exit 0
fi
snapdir=$(mktemp -d)
trap 'rm -rf "$snapdir"' EXIT
stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ledgers=()
for d in "${doors[@]}"; do
  ledger="$d/CHECKPOINTS.txt"
  line="$stamp"
  for log in "$d"/*.jsonl; do
    snap="$snapdir/$(basename "$log")"
    cp "$log" "$snap"
    digest=$(sha256sum "$snap" | cut -d' ' -f1)
    bytes=$(stat -c%s "$snap")
    line+=" $(basename "$log"):$digest:$bytes"
  done
  echo "$line" >> "$ledger"
  ledgers+=("$ledger")
done
git add "${ledgers[@]}"
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" \
    -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
    commit -S -m "community: checkpoint log digests ($(IFS=,; echo "${doors[*]#community/}"))"
