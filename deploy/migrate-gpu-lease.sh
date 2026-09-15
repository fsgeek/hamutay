#!/usr/bin/env bash
# Deployment migration for the GPU lease (spec: docs/superpowers/specs/
# 2026-09-15-gpu-lease-design.md §3), steps 1-7 in order. Each step is
# echoed as it runs. --dry-run prints the commands instead of running them,
# so the whole runbook can be exercised without touching a real systemd
# user instance. Step 6 quiesces the old heartbeat under its store lock and
# ABORTS (nothing more done, door.json not written) if it cannot confirm no
# wake is running before the timeout.
#
# Run from /home/tony/projects/hamutay after merging to main: the script
# refuses to run from a tree that is not hamutay-heartbeat@qwen's own
# WorkingDirectory (see the root check below).
set -euo pipefail

# SELF_ROOT is where this script (and the deploy/ templates it copies from)
# actually lives. ROOT is the target tree that receives community/qwen and
# is the --project for the migrate-quiesce invocation; it defaults to
# SELF_ROOT but tests point it at a fixture tree so the templates still
# come from the real repo while community/qwen is disposable.
SELF_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYSTEMCTL=systemctl
JOURNALCTL=journalctl
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_PATHS=""
ROOT="$SELF_ROOT"
DRY_RUN=0
QUIESCE_TIMEOUT=30m

while [ $# -gt 0 ]; do
  case "$1" in
    --systemctl) SYSTEMCTL="$2"; shift 2 ;;
    --journalctl) JOURNALCTL="$2"; shift 2 ;;
    --unit-dir) UNIT_DIR="$2"; shift 2 ;;
    --unit-paths) UNIT_PATHS="$2"; shift 2 ;;
    --root) ROOT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --quiesce-timeout) QUIESCE_TIMEOUT="$2"; shift 2 ;;
    *) echo "migrate-gpu-lease: unknown argument: $1" >&2; exit 2 ;;
  esac
done
# Same idiom as check-gpu-lease.sh: read-only discovery of every directory
# systemd resolves user units from (generators, transient units, drop-ins,
# ~/.config, /etc, /usr/lib, ...) is not a mutation, so it runs even outside
# --dry-run; tests always pass --unit-paths to stay off the real host.
[ -n "$UNIT_PATHS" ] || UNIT_PATHS="$(systemd-analyze --user unit-paths 2>/dev/null | tr '\n' ' ')"

run() {
  # Print the command; execute it unless --dry-run.
  echo "+ $*"
  if [ "$DRY_RUN" -eq 0 ]; then
    "$@"
  fi
}

# Guard: the migration must run from the tree the heartbeat unit actually
# runs out of. ROOT feeds step 4's door path and step 7's door.json; if it
# names a worktree (or any other checkout) the door file would point the
# live heartbeat at a tree systemd never launches from. Read the unit's own
# WorkingDirectory and refuse a mismatch. An empty answer means we are
# talking to a fake systemctl (tests / --dry-run) or a unit systemd does not
# know: note it and carry on rather than block the rehearsal.
unit_wd="$("$SYSTEMCTL" --user show -p WorkingDirectory --value hamutay-heartbeat@qwen 2>/dev/null || true)"
if [ -z "$unit_wd" ]; then
  echo "migrate-gpu-lease: note — hamutay-heartbeat@qwen reports no WorkingDirectory; skipping the root check"
elif [ "$unit_wd" != "$ROOT" ]; then
  echo "migrate-gpu-lease: refusing to migrate from the wrong tree." >&2
  echo "  --root (or this checkout): $ROOT" >&2
  echo "  hamutay-heartbeat@qwen WorkingDirectory: $unit_wd" >&2
  echo "  Run from /home/tony/projects/hamutay after merging to main." >&2
  exit 1
else
  echo "root check: $ROOT matches hamutay-heartbeat@qwen WorkingDirectory"
fi

echo "step 1: disable hamutay-llama-server (unit still carries [Install])"
run "$SYSTEMCTL" --user disable hamutay-llama-server
wants_link="$UNIT_DIR/default.target.wants/hamutay-llama-server.service"
if [ "$DRY_RUN" -eq 0 ]; then
  if [ -e "$wants_link" ] || [ -L "$wants_link" ]; then
    echo "migrate-gpu-lease: $wants_link still present after disable" >&2
    exit 1
  fi
else
  echo "+ assert absent: $wants_link"
fi

echo "step 2: install the revised server unit and heartbeat@qwen drop-in"
run mkdir -p "$UNIT_DIR/hamutay-heartbeat@qwen.service.d"
run cp "$SELF_ROOT/deploy/hamutay-llama-server.service" "$UNIT_DIR/hamutay-llama-server.service"
run cp "$SELF_ROOT/deploy/hamutay-heartbeat@qwen.service.d/override.conf" \
  "$UNIT_DIR/hamutay-heartbeat@qwen.service.d/override.conf"
run "$SYSTEMCTL" --user daemon-reload

echo "step 3: assert the server carries no dependents"
if [ "$DRY_RUN" -eq 0 ]; then
  en="$("$SYSTEMCTL" --user is-enabled hamutay-llama-server 2>/dev/null)"
  if [ "$en" != "static" ]; then
    echo "migrate-gpu-lease: hamutay-llama-server is-enabled=$en (want static)" >&2
    exit 1
  fi
  if "$SYSTEMCTL" --user show -p Requires,Wants,After hamutay-heartbeat@qwen 2>/dev/null | grep -q hamutay-llama-server; then
    echo "migrate-gpu-lease: heartbeat@qwen still depends on the server" >&2
    exit 1
  fi
  if "$SYSTEMCTL" --user show -p WantedBy,RequiredBy hamutay-llama-server 2>/dev/null | grep -qE '=(.+)$'; then
    echo "migrate-gpu-lease: something wants/requires the server" >&2
    exit 1
  fi
  # The spec requires scanning every directory systemd-analyze --user
  # unit-paths reports, not just where this migration writes (reading is
  # not a mutation). Tests always pass --unit-paths to stay off the host.
  for d in $UNIT_PATHS; do
    [ -d "$d" ] || continue
    while IFS= read -r f; do
      [ "$(basename "$f")" = "hamutay-llama-server.service" ] && continue
      grep -vE '^\s*#' "$f" | grep -qE '^[[:space:]]*(Requires|Wants|BindsTo)=.*hamutay-llama-server' \
        && { echo "migrate-gpu-lease: $f pulls in the server" >&2; exit 1; }
    done < <(find "$d" -type f \( -name '*.service' -o -name '*.conf' \) 2>/dev/null)
    while IFS= read -r l; do
      base="$(basename "$l")"
      target_base="$(basename "$(readlink "$l" 2>/dev/null || true)")"
      if [ "$base" = "hamutay-llama-server.service" ] || [ "$target_base" = "hamutay-llama-server.service" ]; then
        echo "migrate-gpu-lease: symlink $l -> $(readlink "$l" 2>/dev/null)" >&2
        exit 1
      fi
    done < <(find "$d" -type l 2>/dev/null)
  done
else
  echo "+ assert is-enabled=static, no Requires/Wants/After on the server, no WantedBy/RequiredBy"
fi

echo "step 4: resolve the state dir and write 4090.door"
state="${AYLLU_STATE_DIR:-$HOME/.local/state/ayllu}/gpu"
run mkdir -p "$state/4090.tombstones"
if [ "$DRY_RUN" -eq 0 ]; then
  echo "$ROOT/community/qwen" > "$state/4090.door"
else
  echo "+ write $state/4090.door <- $ROOT/community/qwen"
fi

echo "step 5: deploy the code (the old heartbeat keeps running the old code; door.json not written yet)"
echo "+ (code already deployed by this checkout; no action)"

echo "step 6: quiesce the old heartbeat under its store lock"
# The Python package and its uv-managed venv live in SELF_ROOT (this
# checkout); ROOT only supplies the community/qwen door directory (in real
# deployment SELF_ROOT and ROOT are the same directory — tests split them
# to point at a disposable fixture door without a whole fake uv project).
run uv run --project "$SELF_ROOT" python -m hamutay.gpu_lease migrate-quiesce \
  --door "$ROOT/community/qwen" --unit hamutay-heartbeat@qwen \
  --timeout "$QUIESCE_TIMEOUT" --systemctl "$SYSTEMCTL"

echo "step 7: write door.json and start the new heartbeat"
run cp "$SELF_ROOT/deploy/door.json.qwen" "$ROOT/community/qwen/door.json"
run "$SYSTEMCTL" --user start hamutay-heartbeat@qwen

# The new heartbeat has to start, resolve its launch, and print its notes
# before check-gpu-lease.sh can see the launch note. Wait for it rather than
# racing it into a spurious failure. Skipped under --dry-run (nothing started).
if [ "$DRY_RUN" -eq 0 ]; then
  echo "waiting up to 120s for the 'gpu lease: 4090' launch note"
  waited=0
  while [ "$waited" -lt 120 ]; do
    if "$JOURNALCTL" --user -u hamutay-heartbeat@qwen -n 500 --no-pager 2>/dev/null \
         | grep -q 'gpu lease: 4090'; then
      echo "launch note seen after ${waited}s"
      break
    fi
    sleep 5
    waited=$((waited + 5))
  done
  [ "$waited" -lt 120 ] || echo "migrate-gpu-lease: no launch note after ${waited}s; checking anyway" >&2
else
  echo "+ (dry-run) skip the 120s wait for the launch note"
fi

echo "migrate-gpu-lease: done; verifying with check-gpu-lease.sh"
check_cmd=("$SELF_ROOT/deploy/check-gpu-lease.sh" --systemctl "$SYSTEMCTL" --unit-paths "$UNIT_PATHS" --journalctl "$JOURNALCTL")
if [ "$DRY_RUN" -eq 0 ]; then
  if ! "${check_cmd[@]}"; then
    echo "migrate-gpu-lease: the check failed. Re-running this migration is safe:" >&2
    echo "  every step is idempotent, and step 6 re-quiesces under the store lock." >&2
    exit 1
  fi
else
  echo "+ ${check_cmd[*]}"
fi
