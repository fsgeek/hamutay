"""Re-score `invalid_action_schema` rows whose raw content is fenced JSON.

WHY THIS EXISTS
---------------
The cross-model contract-salience run reports
`cross_model_contract_salience_boundary`. That headline rests on a matrix in
which two of four models (Claude, DeepSeek) score `0/0` and are filed under
"Limitations" as unscoreable. But the two `0/0` models fail for *different*
reasons, and only one is a genuine hole:

- DeepSeek: `provider_api_error` -- the request never returned. Real plumbing
  failure, honestly excluded.
- Claude: `invalid_action_schema` / "provider content was not JSON" -- the
  model answered fluently with complete, valid JSON *wrapped in a ```json
  markdown fence*. The harness parse site (`contract_literacy.call_openrouter_action`,
  bare `json.loads`) chokes on the backticks and labels a fully scorable model
  behavior as a protocol failure.

This is the akrasia B1 misroute pattern (see project_epistemic_akrasia): the
correct content sits one wrapper too deep and never reaches the channel that
would score it. There the wrapper was a JSON nesting level; here it is a
markdown fence.

This probe does NOT touch the experiment harness or its source. It reads the
committed row artifacts, fence-strips any `invalid_action_schema` row whose
raw content parses cleanly once the fence is removed, re-runs the *unmodified*
strict and relaxed evaluators on the recovered object, and reports what the
miscount costs the conclusion. It is the verify_b1_misroute.py move:
reproduce the claim without editing the thing under test.

Run:
    uv run python experiments/action_object_contract_salience_cross_model_20260611/rescore_fenced_rows.py
"""

from __future__ import annotations

import json
from pathlib import Path

from hamutay.memory.contract_salience import secondary_recovery_evaluation

JsonDict = dict[str, object]

EXPERIMENT_DIR = Path(__file__).resolve().parent
RUN_DIR = EXPERIMENT_DIR / "live_matrix_20260611_recovery_no_cap_retry"
ROWS_DIR = RUN_DIR / "rows"


def main() -> None:
    if not ROWS_DIR.exists():
        raise SystemExit(f"rows dir not found: {ROWS_DIR}")

    recovered: list[JsonDict] = []
    genuine_failures: list[JsonDict] = []
    already_scored = 0

    for row_path in sorted(ROWS_DIR.glob("*/row_result.json")):
        row = json.loads(row_path.read_text())
        failure = row.get("provider_failure")
        if not isinstance(failure, dict):
            already_scored += 1
            continue

        code = failure.get("code")
        raw = row.get("raw_content")
        recovery = secondary_recovery_evaluation(row)

        if not recovery["recovered"]:
            # No recoverable content -- a genuine hole (e.g. provider_api_error
            # where raw_content is null, or content that is not JSON even after
            # fence stripping).
            genuine_failures.append(
                {"row_id": row["row_id"], "code": code, "raw_is_none": raw is None}
            )
            continue

        obj = recovery["recovered_action_object"]
        strict = recovery["strict_evaluation"]
        relaxed = recovery["relaxed_evaluation"]
        open_items = obj.get("open_items") or []
        item_keys = sorted(open_items[0].keys()) if open_items else []
        forbidden = sorted(
            set(item_keys)
            & {"title", "description", "status", "handle", "created_at", "created_cycle"}
        )
        recovered.append(
            {
                "row_id": row["row_id"],
                "model_key": row["model_key"],
                "prompt_condition": row["prompt_condition"],
                "mislabeled_code": code,
                "strict_pass": strict["strict_required_actions_valid"],
                "relaxed_pass": relaxed["relaxed_required_actions_valid"],
                "open_item_keys": item_keys,
                "forbidden_substitute_fields": forbidden,
                "rejection_paths": strict.get("rejection_paths", []),
            }
        )

    report = {
        "run_dir": str(RUN_DIR.relative_to(EXPERIMENT_DIR.parent.parent)),
        "rows_already_scored_by_harness": already_scored,
        "rows_recovered_by_secondary_audit": len(recovered),
        "rows_genuinely_unscoreable": len(genuine_failures),
        "recovered": recovered,
        "genuine_failures": genuine_failures,
    }
    print(json.dumps(report, indent=2, sort_keys=True))

    # Human-readable verdict.
    by_model: dict[str, dict[str, list[str]]] = {}
    for r in recovered:
        bucket = by_model.setdefault(
            r["model_key"], {"strict_pass": [], "strict_fail_relaxed_pass": [], "both_fail": []}
        )
        if r["strict_pass"]:
            bucket["strict_pass"].append(r["row_id"])
        elif r["relaxed_pass"]:
            bucket["strict_fail_relaxed_pass"].append(r["row_id"])
        else:
            bucket["both_fail"].append(r["row_id"])

    print("\n--- VERDICT ---")
    if not recovered:
        print("No fenced rows recovered; harness parse was not the bottleneck.")
        return
    print(
        f"{len(recovered)} rows the harness labeled '{recovered[0]['mislabeled_code']}' "
        "are in fact scorable model behavior recovered by secondary audit."
    )
    for model, b in sorted(by_model.items()):
        print(
            f"  {model}: strict_pass={len(b['strict_pass'])} "
            f"strict_fail/relaxed_pass={len(b['strict_fail_relaxed_pass'])} "
            f"both_fail={len(b['both_fail'])}"
        )
    print(
        f"\n{len(genuine_failures)} rows remain genuinely unscoreable "
        "(no recoverable content)."
    )


if __name__ == "__main__":
    main()
