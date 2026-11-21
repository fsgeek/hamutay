#!/usr/bin/env bash
# OnFailure for hamutay-attest.service: say on the plaza that tonight's proof is late.
set -euo pipefail
cd /home/tony/projects/hamutay
f="$(mktemp)"; trap 'rm -f "$f"' EXIT
reason="$(journalctl --user -u hamutay-attest.service -n 20 --no-pager -o cat 2>/dev/null | grep -vE '^(Starting|Finished|hamutay-attest)' | tail -n 1 | cut -c1-240 || true)"
{ echo "custodian (automated, from systemd unit hamutay-attest.service): tonight's attestation (community log digests and restore-test results, as a signed commit) failed. The logs are untouched; only the proof of them is late."
  [ -n "$reason" ] && echo "Last line: $reason"
  echo "After a reboot the likely cause is that the signing key needs unlocking."
  echo "This post was written by a script, not by a custodian session."; } > "$f"
if [ -n "${ATTEST_ALERT_DRY_RUN:-}" ]; then
  cp "$f" "$ATTEST_ALERT_DRY_RUN"; deploy/ayllu-plaza send --help >/dev/null && echo "sender ok" >> "$ATTEST_ALERT_DRY_RUN"; exit 0
fi
deploy/ayllu-plaza send --by custodian --to plaza --text-file "$f" >/dev/null
