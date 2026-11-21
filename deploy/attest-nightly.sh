#!/usr/bin/env bash
# Nightly attestation: put what the house claims about itself into signed, OTS-stamped commits.
#   1. Copy restore-test results not yet attested into community/backup/RESTORE-TESTS.txt
#      (verbatim lines from ~/backups/arango/restore-log.jsonl; counts only, no secrets).
#   2. Digest every community log (deploy/checkpoint-community-log.sh --no-commit).
#   3. One commit with hamutay's identity; the post-commit hook stamps it. No push: pushing is
#      the steward's decision, after checking identities.
# Why (2026-11-20): restore results were never committed, signed or stamped, and wam-nuc's copy
# is overwritten whole by each run; the community checkpoints were last committed 2026-10-05 and
# Marker (joined 10-19) had never been checkpointed, because nothing scheduled them.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
LOG="${RESTORE_LOG:-$HOME/backups/arango/restore-log.jsonl}"
LEDGER=community/backup/RESTORE-TESTS.txt

if ! git diff --cached --quiet; then
  echo "refusing to attest: index has staged changes (shared worktree)" >&2; exit 1
fi

mkdir -p community/backup
touch "$LEDGER"
added=0
if [ -f "$LOG" ]; then
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    id="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(d["test"] + "/" + d.get("db", "") )' "$line" 2>/dev/null || true)"
    [ -z "$id" ] && continue
    grep -qF "$line" "$LEDGER" || { echo "$line" >> "$LEDGER"; added=$((added+1)); }
  done < "$LOG"
fi

deploy/checkpoint-community-log.sh --no-commit

git add "$LEDGER" community/*/CHECKPOINTS.txt
if git diff --cached --quiet; then
  echo "nothing to attest"; exit 0
fi
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" \
    -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
    commit -S -q -m "attest: nightly checkpoint of community log digests; restore-test lines added: $added"
git log -1 --format='%h %s'
