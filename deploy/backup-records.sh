#!/usr/bin/env bash
# Nightly backup of the house's own records -- community/: every door's log and
# events, the plaza, the assembly ledger, the checkpoints -- copied to wam-nuc
# (a physically separate machine). backup-arango.sh covers Apacheta only; before
# 2026-10-15 these files existed on one host (plaza seq 92).
#
# snapshot community/ (hard-linked against the previous run, so unchanged files
# cost nothing) -> note any JSONL whose last line is incomplete (a line being
# appended during the copy; every earlier line must parse) -> MANIFEST.sha256 ->
# rsync to wam-nuc (hard-linked there too) -> verify the remote manifest ->
# prune to KEEP runs on each side -> one JSON status line in backup-log.jsonl
# (here and on wam-nuc). Nothing is ever written under SRC.
set -euo pipefail
SRC="${SRC:-/home/tony/projects/hamutay/community}"
LOCAL_ROOT="${LOCAL_ROOT:-/home/tony/backups/records}"
REMOTE="${REMOTE:-wam-nuc}"
REMOTE_ROOT="${REMOTE_ROOT:-backups/records}"
KEEP="${KEEP:-14}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$LOCAL_ROOT/$TS"
LOG="$LOCAL_ROOT/backup-log.jsonl"
STAGE="start"

mkdir -p "$LOCAL_ROOT"
status() {  # status <ok|failed> <stage> [extra-json-fields]
  local line
  line="{\"run\":\"$TS\",\"status\":\"$1\",\"stage\":\"$2\",\"finished\":\"$(date -u +%FT%TZ)\"${3:+,$3}}"
  echo "$line" >> "$LOG"
  echo "$line"
}
trap 'status failed "$STAGE"; exit 1' ERR

STAGE="source"
[ -d "$SRC" ]
PREV="$(ls -1d "$LOCAL_ROOT"/20*Z 2>/dev/null | sort | tail -n 1 || true)"

STAGE="snapshot"
mkdir -p "$OUT"
rsync -a ${PREV:+--link-dest="$PREV/community"} "$SRC/" "$OUT/community/"

STAGE="lines"
PARTIAL="$(python3 - "$OUT/community" <<'EOF'
import json, os, sys
partial = []
for d, _, files in os.walk(sys.argv[1]):
    for f in sorted(files):
        if not f.endswith(".jsonl"):
            continue
        p = os.path.join(d, f)
        lines = open(p, "rb").read().split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()
        for i, line in enumerate(lines):
            try:
                json.loads(line)
            except ValueError:
                if i == len(lines) - 1:
                    partial.append(os.path.relpath(p, sys.argv[1]))
                else:
                    sys.exit(f"unparseable line {i + 1} of {os.path.relpath(p, sys.argv[1])}")
print(json.dumps(partial))
EOF
)"

STAGE="manifest"
( cd "$OUT" && find community -type f -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256 )
SIZE="$(du -sb "$OUT" | cut -f1)"
FILES="$(wc -l < "$OUT/MANIFEST.sha256")"

STAGE="copy"
ssh -o BatchMode=yes "$REMOTE" "mkdir -p $REMOTE_ROOT"
RPREV="$(ssh -o BatchMode=yes "$REMOTE" "ls -1d $REMOTE_ROOT/20*Z 2>/dev/null | sort | tail -n 1" || true)"
# A relative --link-dest is resolved against the destination directory, so copy
# into $REMOTE_ROOT/$TS/ and point at its sibling.
rsync -a ${RPREV:+--link-dest="../$(basename "$RPREV")"} "$OUT/" "$REMOTE:$REMOTE_ROOT/$TS/"

STAGE="verify-remote"
ssh -o BatchMode=yes "$REMOTE" "cd $REMOTE_ROOT/$TS && sha256sum --quiet -c MANIFEST.sha256"

STAGE="prune"
ls -1d "$LOCAL_ROOT"/20*Z 2>/dev/null | sort | head -n -"$KEEP" | xargs -r rm -rf
ssh -o BatchMode=yes "$REMOTE" "ls -1d $REMOTE_ROOT/20*Z 2>/dev/null | sort | head -n -$KEEP | xargs -r rm -rf"

STAGE="done"
status ok done "\"bytes\":$SIZE,\"files\":$FILES,\"partial_tail\":$PARTIAL,\"remote\":\"$REMOTE:$REMOTE_ROOT/$TS\""
scp -q "$LOG" "$REMOTE:$REMOTE_ROOT/backup-log.jsonl"
