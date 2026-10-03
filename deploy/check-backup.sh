#!/usr/bin/env bash
# Is the backup alive? Last nightly run ok and younger than 26 h; last restore test ok and younger than 35 days.
LOCAL_ROOT="${LOCAL_ROOT:-/home/tony/backups/arango}"
python3 - "$LOCAL_ROOT" <<'PY'
import json, sys, datetime as dt
root = sys.argv[1]; now = dt.datetime.now(dt.timezone.utc); rc = 0
def last(path):
    try: return json.loads(open(path).read().strip().splitlines()[-1])
    except Exception: return None
for name, path, limit in (("nightly backup", f"{root}/backup-log.jsonl", dt.timedelta(hours=26)),
                          ("restore test", f"{root}/restore-log.jsonl", dt.timedelta(days=35))):
    r = last(path)
    if not r: print(f"FAIL {name}: no record at {path}"); rc = 1; continue
    age = now - dt.datetime.fromisoformat(r["finished"].replace("Z", "+00:00"))
    good = r["status"] == "ok" and age <= limit
    print(f"{'ok  ' if good else 'FAIL'} {name}: {r['status']} at {r['finished']} ({age.total_seconds()/3600:.1f} h ago, limit {limit})")
    rc |= 0 if good else 1
sys.exit(rc)
PY
