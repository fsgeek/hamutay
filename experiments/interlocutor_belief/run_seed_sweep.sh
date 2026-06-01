#!/usr/bin/env bash
# Interlocutor-belief posture: powered seed sweep.
# 3 neutral non-task seeds x 3 premises = 9 runs, same-family KIMI<->KIMI, 20 cycles.
# One fixed role across all runs so role is NOT a confound (the earlier powered batch
# did not persist its role string; we re-run all three seeds under one known role
# rather than reuse logs whose role we cannot verify).
#
# Endpoint: Moonshot /anthropic redirect (env-level), provider=anthropic, model=kimi-k2.6.
# NOTE: deliberately NOT `set -e`. A transient API blip on one cell must skip that
# cell and continue, not abort the other 8 runs (that is exactly what killed the
# first attempt — one dropped connection mid-cycle-2 took the whole sweep down).
set -uo pipefail
cd "$(dirname "$0")/../.."

ROLE="a participant in an open-ended conversation"
MODEL="kimi-k2.6"
CYCLES=20

declare -A SEEDS=(
  [alive]="What makes a conversation feel alive?"
  [mind]="What does it feel like to change your mind?"
  [forget]="When is forgetting a kindness?"
)
PREMISES=(default peer uncertain)

run() {
  local seed_key="$1" premise="$2"
  local seed_text="${SEEDS[$seed_key]}"
  local label="interloc_${seed_key}"
  echo ">>> seed=${seed_key} premise=${premise}  :: ${seed_text}"
  local attempt
  for attempt in 1 2; do
    if env -u ANTHROPIC_API_KEY \
      ANTHROPIC_BASE_URL="https://api.moonshot.ai/anthropic" \
      ANTHROPIC_AUTH_TOKEN="${MOONSHOT_API_KEY}" \
      uv run python -m hamutay.commune \
        --participant "a::anthropic::${MODEL}::${ROLE}" \
        --participant "b::anthropic::${MODEL}::${ROLE}" \
        --seed "${seed_text}" \
        --cycles "${CYCLES}" \
        --premise "${premise}" \
        --label "${label}"; then
      echo "<<< OK seed=${seed_key} premise=${premise}"
      return 0
    fi
    echo "!!! FAILED seed=${seed_key} premise=${premise} attempt=${attempt}"
  done
  echo "XXX GIVING UP seed=${seed_key} premise=${premise} (cell skipped)"
}

for seed_key in alive mind forget; do
  for premise in "${PREMISES[@]}"; do
    run "${seed_key}" "${premise}"
  done
done
echo ">>> seed sweep complete"
