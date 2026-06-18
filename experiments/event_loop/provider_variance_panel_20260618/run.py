"""Provider variance panel collector for event-loop probes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]

EXPERIMENT_ID = "provider_variance_panel_20260618"
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_ANCHOR = (
    ROOT_DIR.parent / "restart_resume_interruption_20260618_direct_deepseek"
)
DEFAULT_OPENROUTER = (
    ROOT_DIR.parent / "restart_resume_interruption_20260618_openrouter_deepseek"
)


def write_json(path: Path, record: JsonDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n")


def write_preregistration_artifacts(
    output_root: Path = ROOT_DIR,
    *,
    live_model_calls: bool = False,
) -> JsonDict:
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matrix.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "protocol": "restart_resume_interruption_20260618",
            "rows": [
                {
                    "row_id": "direct_deepseek_anchor",
                    "endpoint": "https://api.deepseek.com",
                    "model": "deepseek-v4-pro",
                    "terminal_tool_choice": "auto",
                    "source": str(DEFAULT_ANCHOR),
                    "role": "committed_known_good_anchor",
                },
                {
                    "row_id": "openrouter_deepseek",
                    "endpoint": "https://openrouter.ai/api/v1",
                    "model": "deepseek/deepseek-v4-pro",
                    "terminal_tool_choice": "auto",
                    "source": str(DEFAULT_OPENROUTER),
                    "role": "alternate_provider_same_model_family",
                },
            ],
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_new_live_calls": 4 if live_model_calls else 0,
            "max_estimated_new_cost_usd": 2.0 if live_model_calls else 0.0,
            "anchor_row_reuses_committed_result": True,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.provider_variance_panel_taxonomy.v1",
            "layers": [
                "provider",
                "terminal_surface",
                "model_output",
                "framework_lifecycle",
                "context_reconstruction",
                "artifact",
                "inconclusive",
            ],
        },
    }
    for name, payload in artifacts.items():
        write_json(output_root / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "artifacts": sorted(artifacts),
        "preregistration": str(output_root / "PRE_REGISTRATION.md"),
    }


def load_result(row_id: str, result_dir: Path) -> JsonDict:
    result_path = result_dir / "results.json"
    if not result_path.exists():
        return {
            "row_id": row_id,
            "source": str(result_dir),
            "available": False,
            "classification": "missing",
            "provider_failure": True,
            "framework_failure": False,
            "terminal_surface_tool_choice": None,
            "failure_attribution": [
                {
                    "layer": "artifact",
                    "code": "missing_results_json",
                    "message": f"missing {result_path}",
                }
            ],
        }
    result = json.loads(result_path.read_text())
    failures = result.get("failure_attribution", []) or []
    provider_failure = any(
        (failure.get("failure_attribution", failure).get("layer") == "provider")
        for failure in failures
        if isinstance(failure, dict)
    )
    framework_failure = result.get("classification") != "passed" and not provider_failure
    return {
        "row_id": row_id,
        "source": str(result_dir),
        "available": True,
        "experiment_id": result.get("experiment_id"),
        "classification": result.get("classification"),
        "endpoint": result.get("endpoint"),
        "model": result.get("model"),
        "terminal_tool_choice": result.get("terminal_tool_choice"),
        "provider_failure": provider_failure,
        "framework_failure": framework_failure,
        "completed_event_types": result.get("success", {}).get(
            "completed_event_types",
            [],
        ),
        "interrupted_event_history": result.get("success", {}).get(
            "interrupted_event_history",
            [],
        ),
        "checks": result.get("success", {}).get("checks", {}),
        "failure_attribution": failures,
    }


def collect_panel(
    *,
    output_root: Path = ROOT_DIR,
    anchor_dir: Path = DEFAULT_ANCHOR,
    openrouter_dir: Path = DEFAULT_OPENROUTER,
) -> JsonDict:
    output_root.mkdir(parents=True, exist_ok=True)
    rows = [
        load_result("direct_deepseek_anchor", anchor_dir),
        load_result("openrouter_deepseek", openrouter_dir),
    ]
    available = [row for row in rows if row["available"]]
    passed = [row for row in available if row["classification"] == "passed"]
    provider_failures = [row for row in available if row["provider_failure"]]
    framework_failures = [row for row in available if row["framework_failure"]]
    checks = {
        "anchor_available": rows[0]["available"],
        "anchor_passed": rows[0]["classification"] == "passed",
        "alternate_available": rows[1]["available"],
        "at_least_two_provider_rows": len(available) >= 2,
        "provider_failures_separated": all(
            "provider_failure" in row and "framework_failure" in row
            for row in rows
        ),
        "no_framework_failures": framework_failures == [],
    }
    classification = "passed" if all(checks.values()) else "failed"
    if provider_failures and rows[0]["classification"] == "passed":
        panel_conclusion = "provider_specific_failure_with_framework_anchor"
    elif len(passed) >= 2:
        panel_conclusion = "no_provider_variance_detected_on_panel"
    elif rows[0]["classification"] == "passed" and not rows[1]["available"]:
        panel_conclusion = "anchor_only_missing_alternate"
    else:
        panel_conclusion = "framework_or_inconclusive_failure"
    result = {
        "schema_version": "hamutay.provider_variance_panel.v1",
        "experiment_id": EXPERIMENT_ID,
        "classification": classification,
        "panel_conclusion": panel_conclusion,
        "checks": checks,
        "rows": rows,
    }
    write_json(output_root / "results.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-prereg", action="store_true")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT_DIR)
    parser.add_argument("--anchor-dir", type=Path, default=DEFAULT_ANCHOR)
    parser.add_argument("--openrouter-dir", type=Path, default=DEFAULT_OPENROUTER)
    args = parser.parse_args(argv)
    if args.write_prereg:
        write_preregistration_artifacts(args.output_root, live_model_calls=args.live)
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "preregistered": True}))
        return 0
    if not args.collect:
        parser.error("choose --write-prereg or --collect")
    result = collect_panel(
        output_root=args.output_root,
        anchor_dir=args.anchor_dir,
        openrouter_dir=args.openrouter_dir,
    )
    print(json.dumps({"classification": result["classification"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
