#!/bin/bash
# Upgrade pending OpenTimestamps proofs: anchor them to the Bitcoin
# blockchain once a calendar server has included them in a block. Safe to
# run repeatedly; proofs not yet ready stay "pending" and upgrade later.
set -e

GIT_ROOT=$(git rev-parse --show-toplevel)
cd "$GIT_ROOT"

# Resolve ots the same way the post-commit hook does (venv first, uv fallback).
if [ -x "$GIT_ROOT/.venv/bin/ots" ]; then
    OTS=("$GIT_ROOT/.venv/bin/ots")
elif command -v uv >/dev/null 2>&1 && uv run --quiet ots --version >/dev/null 2>&1; then
    OTS=(uv run --quiet ots)
else
    echo "ots: client not found at $GIT_ROOT/.venv/bin/ots" >&2
    echo "ots: run scripts/install-hooks.sh to install it" >&2
    exit 1
fi

upgraded=0
pending=0
previously_completed=0
changed_paths=()
for f in timestamps/*.ots; do
    [ -f "$f" ] || continue
    original_hash=$(sha256sum "$f" | cut -d' ' -f1)
    if "${OTS[@]}" upgrade "$f" 2>/dev/null; then
        upgraded_hash=$(sha256sum "$f" | cut -d' ' -f1)
        if [ "$original_hash" != "$upgraded_hash" ]; then
            echo "upgraded: $f"
            upgraded=$((upgraded + 1))
            changed_paths+=("$f")
            if [ -f "$f.bak" ]; then
                changed_paths+=("$f.bak")
            fi
        else
            previously_completed=$((previously_completed + 1))
        fi
    else
        pending=$((pending + 1))
        echo "pending:  $f"
    fi
done

echo "ots: upgraded $upgraded, pending $pending, previously completed $previously_completed"

if [ "$upgraded" -gt 0 ]; then
    git \
        -c user.email="hamutay@wamason.com" \
        -c user.name="Tony Mason" \
        -c user.signingkey="01193FA2631C8AE8E4DF266E216D3C9B920813A1" \
        add -- "${changed_paths[@]}"
    git \
        -c user.email="hamutay@wamason.com" \
        -c user.name="Tony Mason" \
        -c user.signingkey="01193FA2631C8AE8E4DF266E216D3C9B920813A1" \
        commit --only --no-verify -S -m "ots: upgrade $upgraded timestamp(s)" -- "${changed_paths[@]}"
else
    echo "No timestamps ready to upgrade yet."
fi
