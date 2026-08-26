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

ledger=community/heartbeat/CHECKPOINTS.txt
mkdir -p community/heartbeat

shopt -s nullglob
logs=(community/heartbeat/*.jsonl)
if [ ${#logs[@]} -eq 0 ]; then
  echo "no community logs yet; nothing to checkpoint" >&2
  exit 0
fi

snapdir=$(mktemp -d)
trap 'rm -rf "$snapdir"' EXIT
line="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
for log in "${logs[@]}"; do
  snap="$snapdir/$(basename "$log")"
  cp "$log" "$snap"
  digest=$(sha256sum "$snap" | cut -d' ' -f1)
  bytes=$(stat -c%s "$snap")
  line+=" $(basename "$log"):$digest:$bytes"
done
echo "$line" >> "$ledger"

git add "$ledger"
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" \
    -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
    commit -S -m "community: checkpoint heartbeat log digests"
