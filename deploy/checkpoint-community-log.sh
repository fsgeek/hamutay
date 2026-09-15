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

NO_COMMIT=0
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
while [ $# -gt 0 ]; do
  case "$1" in
    --no-commit) NO_COMMIT=1; shift ;;
    --root) ROOT="$2"; shift 2 ;;
    *) shift ;;
  esac
done
cd "$ROOT"

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

# The GPU lease's ledger lives outside community/<door>/ (it is a shared
# house resource, not one door's log): community/gpu/CHECKPOINTS.txt. The
# ledger itself is never copied into git, only its digest.
gpu_state="${AYLLU_STATE_DIR:-$HOME/.local/state/ayllu}/gpu"
gpu_ledger="$gpu_state/4090.ledger.jsonl"
gpu_lock="$gpu_state/4090.lock"
if [ ! -f "$gpu_ledger" ]; then
  echo "no $gpu_ledger yet; skipping the GPU lease checkpoint" >&2
else
  gpu_snap="$snapdir/4090.ledger.jsonl"
  flock "$gpu_lock" cp "$gpu_ledger" "$gpu_snap"
  gpu_digest=$(sha256sum "$gpu_snap" | cut -d' ' -f1)
  gpu_bytes=$(stat -c%s "$gpu_snap")
  mkdir -p community/gpu
  gpu_checkpoints="community/gpu/CHECKPOINTS.txt"
  echo "$stamp 4090.ledger.jsonl:$gpu_digest:$gpu_bytes" >> "$gpu_checkpoints"
  ledgers+=("$gpu_checkpoints")
fi

if [ ${#ledgers[@]} -eq 0 ]; then
  echo "no community logs yet; nothing to checkpoint" >&2
  exit 0
fi

names=("${doors[@]#community/}")
[ -f "$gpu_ledger" ] && names+=("gpu")

if [ "$NO_COMMIT" -eq 1 ]; then
  echo "checkpoint prepared, --no-commit: not staging or committing" >&2
  exit 0
fi

git add "${ledgers[@]}"
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" \
    -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
    commit -S -m "community: checkpoint log digests ($(IFS=,; echo "${names[*]}"))"
