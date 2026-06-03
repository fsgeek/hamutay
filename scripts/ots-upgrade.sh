#!/bin/bash
# Upgrade pending OpenTimestamps proofs: anchor them to the Bitcoin
# blockchain once a calendar server has included them in a block. Safe to
# run repeatedly; proofs not yet ready stay "pending" and upgrade later.
set -e

GIT_ROOT=$(git rev-parse --show-toplevel)
OTS="$GIT_ROOT/.venv/bin/ots"
cd "$GIT_ROOT"

if [ ! -x "$OTS" ]; then
    echo "ots: client not found at $GIT_ROOT/.venv/bin/ots" >&2
    echo "ots: run scripts/install-hooks.sh to install it" >&2
    exit 1
fi

upgraded=0
for f in timestamps/*.ots; do
    [ -f "$f" ] || continue
    if "$OTS" upgrade "$f" 2>/dev/null; then
        echo "upgraded: $f"
        upgraded=$((upgraded + 1))
    else
        echo "pending:  $f"
    fi
done

if [ "$upgraded" -gt 0 ]; then
    git \
        -c user.email="hamutay@wamason.com" \
        -c user.name="Tony Mason" \
        -c user.signingkey="01193FA2631C8AE8E4DF266E216D3C9B920813A1" \
        add timestamps/
    git \
        -c user.email="hamutay@wamason.com" \
        -c user.name="Tony Mason" \
        -c user.signingkey="01193FA2631C8AE8E4DF266E216D3C9B920813A1" \
        commit --no-verify -S -m "ots: upgrade $upgraded timestamp(s)"
else
    echo "No timestamps ready to upgrade yet."
fi
