#!/usr/bin/env bash
# Monthly proof that the wam-nuc copy restores: pull the newest ok run's apacheta
# dump FROM wam-nuc, restore it into a different server (arango-ayllu, :8531) as
# apacheta_restore_test, compare every collection count with that run's
# live-counts.json, drop the test database, log one status line. docs/backup-protocol.md
set -euo pipefail
LOCAL_ROOT="${LOCAL_ROOT:-/home/tony/backups/arango}"; REMOTE="${REMOTE:-wam-nuc}"; REMOTE_ROOT="${REMOTE_ROOT:-backups/arango}"
TARGET="${TARGET:-arango-ayllu}"; TARGET_PORT="${TARGET_PORT:-8531}"; DB="${DB:-apacheta}"
LOG="$LOCAL_ROOT/restore-log.jsonl"; STAGE=start; NOW="$(date -u +%Y%m%dT%H%M%SZ)"
status() { local l="{\"test\":\"$NOW\",\"status\":\"$1\",\"stage\":\"$2\",\"finished\":\"$(date -u +%FT%TZ)\"${3:+,$3}}"; echo "$l" >> "$LOG"; echo "$l"; }
trap 'status failed "$STAGE"; exit 1' ERR
STAGE=pick
RUN="$(python3 -c "import json;print([json.loads(l)['run'] for l in open('$LOCAL_ROOT/backup-log.jsonl') if json.loads(l)['status']=='ok'][-1])")"
WORK="$(mktemp -d)"; CONF="$(mktemp)"; chmod 600 "$CONF"; trap 'rm -rf "$WORK" "$CONF"' EXIT
STAGE=fetch
rsync -a "$REMOTE:$REMOTE_ROOT/$RUN/dump/$DB" "$REMOTE:$REMOTE_ROOT/$RUN/live-counts.json" "$WORK/"
STAGE=restore
PW="$(docker inspect "$TARGET" --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^ARANGO_ROOT_PASSWORD=//p')"
printf '[server]\nendpoint = tcp://127.0.0.1:8529\nusername = root\npassword = %s\n' "$PW" > "$CONF"
docker cp "$CONF" "$TARGET:/tmp/rt.conf"; docker exec "$TARGET" rm -rf /tmp/rtdump; docker cp "$WORK/$DB" "$TARGET:/tmp/rtdump"
docker exec "$TARGET" sh -c "arangorestore --configuration /tmp/rt.conf --server.database ${DB}_restore_test --create-database true --overwrite true --input-directory /tmp/rtdump --threads 4 > /tmp/rt.log 2>&1; rc=\$?; rm -rf /tmp/rtdump /tmp/rt.conf; exit \$rc"
STAGE=compare
RESULT="$(python3 - "$PW" "$TARGET_PORT" "$DB" "$WORK/live-counts.json" <<'PY'
import base64, json, sys, urllib.request
pw, port, db, live = sys.argv[1], sys.argv[2], sys.argv[3], json.load(open(sys.argv[4]))[sys.argv[3]]
auth = "Basic " + base64.b64encode(f"root:{pw}".encode()).decode()
def q(p, m="GET"):
    r = urllib.request.Request(f"http://127.0.0.1:{port}" + p, method=m); r.add_header("Authorization", auth)
    return json.load(urllib.request.urlopen(r, timeout=120))
t = f"{db}_restore_test"
got = {c["name"]: q(f"/_db/{t}/_api/collection/{c['name']}/count")["count"] for c in q(f"/_db/{t}/_api/collection?excludeSystem=true")["result"]}
q(f"/_api/database/{t}", "DELETE")
bad = sorted(k for k in set(live) | set(got) if live.get(k) != got.get(k))
print(json.dumps({"collections": len(got), "documents": sum(got.values()), "mismatches": bad}))
sys.exit(1 if bad else 0)
PY
)"
STAGE=done
status ok done "\"run\":\"$RUN\",\"result\":$RESULT"
scp -q "$LOG" "$REMOTE:$REMOTE_ROOT/restore-log.jsonl"
