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
RQ="$(printf %q "$REMOTE_ROOT")"   # REMOTE_ROOT quoted for the remote shell
runs() { find "$1" -mindepth 1 -maxdepth 1 -type d -name '20*Z' 2>/dev/null | sort; }  # run dirs only

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
PREV="$(runs "$LOCAL_ROOT" | tail -n 1)"

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
        # The piece after the last newline is b"" for a complete file. Only that
        # unterminated piece can be a write in progress; a terminated line that
        # does not parse is damage, and fails the run.
        tail = lines.pop()
        for i, line in enumerate(lines):
            try:
                json.loads(line)
            except ValueError:
                sys.exit(f"unparseable line {i + 1} of {os.path.relpath(p, sys.argv[1])}")
        if tail:
            try:
                json.loads(tail)
            except ValueError:
                partial.append(os.path.relpath(p, sys.argv[1]))
print(json.dumps(partial))
EOF
)"

STAGE="manifest"
( cd "$OUT" && find community -type f -print0 | sort -z | xargs -0 -r sha256sum > MANIFEST.sha256 )
SIZE="$(du -sb "$OUT" | cut -f1)"
FILES="$(wc -l < "$OUT/MANIFEST.sha256")"

STAGE="copy"
ssh -o BatchMode=yes "$REMOTE" "mkdir -p $RQ"
RPREV="$(ssh -o BatchMode=yes "$REMOTE" "find $RQ -mindepth 1 -maxdepth 1 -type d -name '20*Z' | sort | tail -n 1")"
# A relative --link-dest is resolved against the destination directory, so copy
# into $REMOTE_ROOT/$TS/ and point at its sibling.
rsync -a --protect-args ${RPREV:+--link-dest="../$(basename "$RPREV")"} "$OUT/" "$REMOTE:$REMOTE_ROOT/$TS/"

STAGE="verify-remote"
# An empty source gives an empty manifest, which sha256sum -c rejects; require the
# file, and check it whenever it lists anything.
ssh -o BatchMode=yes "$REMOTE" "cd $RQ/$TS && test -f MANIFEST.sha256 && { test ! -s MANIFEST.sha256 || sha256sum --quiet -c MANIFEST.sha256; }"

STAGE="prune"
runs "$LOCAL_ROOT" | head -n -"$KEEP" | xargs -r -d '\n' rm -rf
ssh -o BatchMode=yes "$REMOTE" "find $RQ -mindepth 1 -maxdepth 1 -type d -name '20*Z' | sort | head -n -$KEEP | xargs -r -d '\n' rm -rf"

STAGE="done"
status ok done "\"bytes\":$SIZE,\"files\":$FILES,\"partial_tail\":$PARTIAL,\"remote\":\"$REMOTE:$REMOTE_ROOT/$TS\""
rsync -a --protect-args "$LOG" "$REMOTE:$REMOTE_ROOT/backup-log.jsonl"
