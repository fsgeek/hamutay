#!/usr/bin/env bash
# Nightly dump of every database on the ArangoDB server that holds Apacheta
# (the residents' record), copied to wam-nuc (a physically separate machine).
#
# Why: on 2026-10-03 the README's "backed up off this host" could not be
# verified. The record lived in one Docker volume on this machine, and the doors'
# JSONL (the only other copy) is on the same disk. See
# docs/backup-protocol.md.
#
# Each run: live document counts -> arangodump (inside the running container,
# so the dumper's version is the server's) -> copy out -> sha256 manifest ->
# rsync to wam-nuc -> verify the remote manifest -> prune to KEEP runs on each side
# -> one JSON status line in backup-log.jsonl (here and on wam-nuc).
# Any failure exits non-zero, so the systemd unit shows failed and the status
# line says where it stopped.
set -euo pipefail

CONTAINER="${CONTAINER:-arango-apacheta}"
LOCAL_ROOT="${LOCAL_ROOT:-/home/tony/backups/arango}"
REMOTE="${REMOTE:-wam-nuc}"
REMOTE_ROOT="${REMOTE_ROOT:-backups/arango}"
KEEP="${KEEP:-14}"
DB_INI="${DB_INI:-/home/tony/.yanantin/config/db.ini}"

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

# Credentials: read from the yanantin config. They are never printed and never put on a command line.
STAGE="credentials"
CONF="$(mktemp)"; chmod 600 "$CONF"
trap 'rm -f "$CONF"' EXIT
python3 - "$DB_INI" "$CONF" <<'EOF'
import configparser, sys
c = configparser.ConfigParser(); c.read(sys.argv[1]); d = c["database"]
open(sys.argv[2], "w").write(
    f"[server]\nendpoint = tcp://127.0.0.1:8529\nusername = {d['admin_user']}\npassword = {d['admin_passwd']}\n")
EOF

STAGE="counts"
mkdir -p "$OUT"
python3 - "$DB_INI" "$OUT/live-counts.json" <<'EOF'
import base64, configparser, json, sys, urllib.request
c = configparser.ConfigParser(); c.read(sys.argv[1]); d = c["database"]
auth = "Basic " + base64.b64encode(f"{d['admin_user']}:{d['admin_passwd']}".encode()).decode()
def q(p):
    r = urllib.request.Request("http://127.0.0.1:8529" + p); r.add_header("Authorization", auth)
    return json.load(urllib.request.urlopen(r, timeout=60))
counts = {}
for db in q("/_api/database")["result"]:
    counts[db] = {col["name"]: q(f"/_db/{db}/_api/collection/{col['name']}/count")["count"]
                  for col in q(f"/_db/{db}/_api/collection?excludeSystem=true")["result"]}
json.dump(counts, open(sys.argv[2], "w"), indent=1, sort_keys=True)
EOF

STAGE="dump"
docker cp "$CONF" "$CONTAINER:/tmp/backup-arango.conf"
docker exec "$CONTAINER" sh -c "rm -rf /tmp/backup-dump && arangodump --configuration /tmp/backup-arango.conf \
  --all-databases true --output-directory /tmp/backup-dump --compress-output true --threads 4 \
  --overwrite true > /tmp/backup-dump.log 2>&1; rc=\$?; rm -f /tmp/backup-arango.conf; exit \$rc"
docker cp "$CONTAINER:/tmp/backup-dump/." "$OUT/dump/"
docker cp "$CONTAINER:/tmp/backup-dump.log" "$OUT/arangodump.log"
docker exec "$CONTAINER" rm -rf /tmp/backup-dump /tmp/backup-dump.log

STAGE="manifest"
( cd "$OUT" && find dump -type f -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256 )
SIZE="$(du -sb "$OUT" | cut -f1)"
FILES="$(wc -l < "$OUT/MANIFEST.sha256")"

STAGE="copy"
ssh -o BatchMode=yes "$REMOTE" "mkdir -p $REMOTE_ROOT"
rsync -a "$OUT" "$REMOTE:$REMOTE_ROOT/"

STAGE="verify-remote"
ssh -o BatchMode=yes "$REMOTE" "cd $REMOTE_ROOT/$TS && sha256sum --quiet -c MANIFEST.sha256"

STAGE="prune"
ls -1d "$LOCAL_ROOT"/20*Z 2>/dev/null | sort | head -n -"$KEEP" | xargs -r rm -rf
ssh -o BatchMode=yes "$REMOTE" "ls -1d $REMOTE_ROOT/20*Z 2>/dev/null | sort | head -n -$KEEP | xargs -r rm -rf"

STAGE="done"
status ok done "\"bytes\":$SIZE,\"files\":$FILES,\"remote\":\"$REMOTE:$REMOTE_ROOT/$TS\""
scp -q "$LOG" "$REMOTE:$REMOTE_ROOT/backup-log.jsonl"
