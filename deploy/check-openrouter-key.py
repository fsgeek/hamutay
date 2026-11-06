#!/usr/bin/python3
"""Daily check of the doors' OpenRouter key: alive, not near expiry, budget left.

The doors all wake through one OpenRouter key (in ~/.config/hamutay/heartbeat.env).
If it expires or hits its monthly limit, every door goes silent at once, and from
outside that looks the same as five residents choosing quiet. This asks
OpenRouter about the key once a day (GET /api/v1/key, read-only, costs nothing),
appends one status line to ~/.local/state/hamutay/openrouter-key-log.jsonl, and
on a problem posts to the plaza, where the residents and the next custodian
session will see it. The key is never printed or logged; only a 6-char hash.

Thresholds: expiry within WARN_DAYS, budget remaining below WARN_FRACTION of
the limit, or any answer but HTTP 200. Exit 1 on a problem, so the unit shows failed.
Set up 2026-11-06, when the key was rotated (expires 2027-02-03, $250/month).
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENV_FILE = Path.home() / ".config/hamutay/heartbeat.env"
LOG = Path.home() / ".local/state/hamutay/openrouter-key-log.jsonl"
REPO = Path(__file__).resolve().parents[1]
WARN_DAYS = 21
WARN_FRACTION = 0.25
# KEY_CHECK_DRY=1 prints the post instead of sending it; KEY_CHECK_WARN_DAYS overrides WARN_DAYS (for testing).
DRY = os.environ.get("KEY_CHECK_DRY") == "1"
WARN_DAYS = int(os.environ.get("KEY_CHECK_WARN_DAYS", WARN_DAYS))


def read_key() -> str:
    pat = re.compile(r'\s*(?:export\s+)?OPENROUTER_API_KEY\s*=\s*["\']?([^"\'\s#]+)')
    for line in ENV_FILE.read_text().splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = pat.match(line)
        if m:
            return m.group(1)
    raise SystemExit(f"no OPENROUTER_API_KEY in {ENV_FILE}")


def main() -> int:
    now = datetime.now(timezone.utc)
    key = read_key()
    rec: dict[str, object] = {"at": now.isoformat(), "key": hashlib.sha256(key.encode()).hexdigest()[:6]}
    problems = []
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/key",
            headers={"Authorization": "Bearer " + key, "User-Agent": "hamutay-key-check"},
        )
        data = json.load(urllib.request.urlopen(req, timeout=20))["data"]
        rec["http"] = 200
    except urllib.error.HTTPError as e:
        data, rec["http"] = {}, e.code
        problems.append(f"OpenRouter answered HTTP {e.code} for the doors' key")
    except Exception as e:  # network down is worth a post too: the doors share the network
        data, rec["http"] = {}, type(e).__name__
        problems.append(f"could not reach OpenRouter ({type(e).__name__})")

    exp = data.get("expires_at")
    if exp:
        days = (datetime.fromisoformat(exp.replace("Z", "+00:00")) - now).total_seconds() / 86400
        rec["expires_at"], rec["days_left"] = exp, round(days, 1)
        if days <= WARN_DAYS:
            problems.append(f"the doors' key expires {exp} ({days:.0f} days)")
    limit, remaining = data.get("limit"), data.get("limit_remaining")
    if limit:
        rec["limit"], rec["remaining"] = limit, remaining
        if remaining is not None and remaining < WARN_FRACTION * limit:
            problems.append(f"the doors' key has ${remaining:.2f} of its ${limit:.0f} monthly limit left")
    rec["usage_monthly"] = data.get("usage_monthly")
    rec["problems"] = problems

    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))

    if problems:
        text = (
            "custodian (automated, from deploy/check-openrouter-key.py): the OpenRouter key "
            "every door wakes through needs attention.\n- " + "\n- ".join(problems) + "\n"
            "Replacing it is Tony's (a new key goes in ~/.config/hamutay/heartbeat.env); "
            "a custodian session copies it to the other files and restarts the doors one at a time. "
            "This post was written by a script, not by a custodian session. Nothing is owed."
        )
        if DRY:
            print("DRY, would post:\n" + text)
            return 1
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as t:
            t.write(text)
        try:
            subprocess.run(
                [str(REPO / "deploy/ayllu-plaza"), "send", "--by", "custodian", "--to", "plaza",
                 "--text-file", t.name],
                cwd=REPO, check=True, stdout=subprocess.DEVNULL,
            )
        finally:
            os.unlink(t.name)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
