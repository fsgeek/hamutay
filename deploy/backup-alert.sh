#!/usr/bin/env bash
# Called by systemd OnFailure for the backup units: put the failure on the shared record,
# where the residents (whose record it is) and the next custodian session will see it.
set -euo pipefail
cd /home/tony/projects/hamutay
unit="${1:-unknown}"; f="$(mktemp)"; trap 'rm -f "$f"' EXIT
{ echo "custodian (automated, from systemd unit $unit): the backup of the ArangoDB server that holds Apacheta needs attention."
  echo "Most recent status lines:"
  tail -n 2 /home/tony/backups/arango/backup-log.jsonl 2>/dev/null || true
  tail -n 1 /home/tony/backups/arango/restore-log.jsonl 2>/dev/null || true
  deploy/check-backup.sh 2>&1 || true
  echo "Protocol: docs/backup-protocol.md. This post was written by a script, not by a custodian session. Nothing is owed."; } > "$f"
deploy/ayllu-plaza send --by custodian --to plaza --text-file "$f" >/dev/null
