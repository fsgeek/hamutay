#!/usr/bin/env bash
# Asserts the deployed state the GPU lease design requires (spec §3). Exit 0 iff all hold.
set -uo pipefail
SYSTEMCTL=systemctl; UNIT_PATHS=""; JOURNALCTL=journalctl
while [ $# -gt 0 ]; do case "$1" in --systemctl) SYSTEMCTL="$2"; shift 2;; --unit-paths) UNIT_PATHS="$2"; shift 2;; --journalctl) JOURNALCTL="$2"; shift 2;; *) shift;; esac; done
[ -n "$UNIT_PATHS" ] || UNIT_PATHS="$(systemd-analyze --user unit-paths 2>/dev/null | tr '\n' ' ')"
fail=0; say() { echo "check-gpu-lease: $*" >&2; fail=1; }

en="$("$SYSTEMCTL" --user is-enabled hamutay-llama-server 2>/dev/null)"
[ "$en" = "static" ] || say "hamutay-llama-server is-enabled=$en (want static)"

"$SYSTEMCTL" --user show -p Requires,Wants,After hamutay-heartbeat@qwen 2>/dev/null | grep -q hamutay-llama-server \
  && say "heartbeat@qwen still depends on the server"

"$SYSTEMCTL" --user show -p WantedBy,RequiredBy hamutay-llama-server 2>/dev/null | grep -qE '=(.+)$' \
  && say "something wants/requires the server"

for d in $UNIT_PATHS; do
  [ -d "$d" ] || continue

  # File-content check: no regular unit file/drop-in (other than the server
  # unit itself) may name the server in a Requires=/Wants=/BindsTo= line.
  # Comment lines, and lines that only mention the name inside a comment,
  # are not directives and are skipped.
  while IFS= read -r f; do
    [ "$(basename "$f")" = "hamutay-llama-server.service" ] && continue
    while IFS= read -r line; do
      # strip a leading comment line entirely
      case "$line" in
        \#*) continue ;;
      esac
      # strip a trailing inline comment (a '#' anywhere makes the rest a
      # comment for our purposes — directive lines never legitimately
      # contain '#')
      directive="${line%%#*}"
      # strip leading whitespace: systemd honours an indented directive
      # (e.g. a tab before "Wants=...") the same as a column-0 one.
      directive="${directive#"${directive%%[![:space:]]*}"}"
      case "$directive" in
        Requires=*hamutay-llama-server*|Wants=*hamutay-llama-server*|BindsTo=*hamutay-llama-server*)
          say "$f pulls in the server: $line" ;;
      esac
    done < "$f"
  done < <(find "$d" -type f \( -name '*.service' -o -name '*.conf' \) 2>/dev/null)

  # Symlink check: neither the link's own basename nor its readlink target's
  # basename may be the server unit name.
  while IFS= read -r l; do
    base="$(basename "$l")"
    target_base="$(basename "$(readlink "$l" 2>/dev/null || true)")"
    if [ "$base" = "hamutay-llama-server.service" ] || [ "$target_base" = "hamutay-llama-server.service" ]; then
      say "symlink $l -> $(readlink "$l" 2>/dev/null)"
    fi
  done < <(find "$d" -type l 2>/dev/null)
done

state="${AYLLU_STATE_DIR:-$HOME/.local/state/ayllu}/gpu"
[ -f "$state/4090.door" ] || say "no $state/4090.door"

"$JOURNALCTL" --user -u hamutay-heartbeat@qwen -n 500 --no-pager 2>/dev/null | grep -q 'gpu lease: 4090' \
  || say "no 'gpu lease: 4090' launch note in the last 500 lines of hamutay-heartbeat@qwen's journal"

exit $fail
