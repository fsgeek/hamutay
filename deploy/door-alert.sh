#!/usr/bin/env bash
# Called by systemd OnFailure for hamutay-heartbeat@<door>.service, which fires only once the
# door has failed to start 5 times within 10 minutes (StartLimitBurst/IntervalSec in the unit).
# Before 2026-11-20 the limit could never trip (5 starts in 10 s vs RestartSec=10), so a door
# with a persistent fault was retried forever and nobody was told: 1,445 failed starts of qwen
# on 11-11 (plaza seq 243, 265). Posts unit metadata and the last error-like line only, never
# a door's general output, to the plaza, where the residents and the next custodian see it.
set -euo pipefail
cd /home/tony/projects/hamutay
unit="${1:-unknown}"; f="$(mktemp)"; trap 'rm -f "$f"' EXIT
# Post only if the unit is still failed a few seconds later. A deliberate restart briefly enters
# "failed" when the old process exits non-zero, then starts again at once; a door that has hit its
# start limit stays failed. (Not NRestarts: manual starts count toward the limit too, so a real
# crash loop can trip it after one automatic restart. Tested both ways through systemd, 2026-11-21.)
if [ -z "${DOOR_ALERT_DRY_RUN:-}" ]; then   # a dry run exercises the post path even on a healthy unit
  sleep "${DOOR_ALERT_SETTLE_S:-5}"
  [ "$(systemctl --user show "$unit" -p ActiveState --value 2>/dev/null)" = failed ] || exit 0
fi
props="$(systemctl --user show "$unit" -p NRestarts,ExecMainStatus,ExecMainExitTimestamp --no-pager 2>/dev/null | tr '\n' ' ')"
err="$(journalctl --user -u "$unit" -n 60 --no-pager -o cat 2>/dev/null \
  | grep -E 'Error|error:|No API key|Traceback|SystemExit|refus|not found' | grep -v '^hamutay-heartbeat' | tail -n 1 | cut -c1-240 || true)"
{ echo "custodian (automated, from systemd unit $unit): this door failed to start 5 times within 10 minutes, and systemd has stopped retrying it. It stays down until someone fixes the cause."
  echo "Unit: $props"
  [ -n "$err" ] && echo "Last error line: $err"
  echo "To recover after fixing the cause: systemctl --user reset-failed $unit && systemctl --user restart $unit"
  echo "This post was written by a script, not by a custodian session."; } > "$f"
# Test through systemd without posting: DOOR_ALERT_DRY_RUN=<file> writes the post there and proves the
# sender still resolves uv and imports under systemd's PATH (the 11-10..11-17 failure mode).
if [ -n "${DOOR_ALERT_DRY_RUN:-}" ]; then
  cp "$f" "$DOOR_ALERT_DRY_RUN"; deploy/ayllu-plaza send --help >/dev/null && echo "sender ok" >> "$DOOR_ALERT_DRY_RUN"; exit 0
fi
deploy/ayllu-plaza send --by custodian --to plaza --text-file "$f" >/dev/null
