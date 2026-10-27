#!/usr/bin/env bash
# A3 run (docs/preregistrations/2026-10-27-a3-loss-record-prereg.md): for each
# model in a3_models_20261027.txt, one run per arm, order alternating by list
# position (even: K then R; odd: R then K). Each run gets its own output dir.
set -uo pipefail
cd "$(dirname "$0")/../.."
base="experiments/taste_open/a3_runs_20261027/$2"
mkdir -p "$base/K" "$base/R"
i=${3:-0}
while read -r model; do
  [ -n "$model" ] || continue
  slug="$(printf '%02d' "$i")_${model//\//__}"
  if [ $((i % 2)) -eq 0 ]; then order="K R"; else order="R K"; fi
  for arm in $order; do
    flag=""; [ "$arm" = R ] && flag="--remove-not-lost"
    echo "[$i] $arm $model $(date -u +%FT%TZ)"
    uv run python experiments/taste_open/sweep.py --models "$model" $flag \
      --output-dir "$base/$arm/$slug" > "$base/$arm/$slug.log" 2>&1
    echo "    exit $?"
  done
  i=$((i + 1))
done < "$1"
echo "done $(date -u +%FT%TZ)"
