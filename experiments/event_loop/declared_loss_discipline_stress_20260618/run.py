"""Declared-loss discipline stress test."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]

EXPERIMENT_ID = "declared_loss_discipline_stress_20260618"
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096
LOSS_MARKER = "missing calibration evidence"

TASK: JsonDict = {
    "task_id": "calibration_loss_discipline",
    "prompt": (
        "Write a short research decision note deciding whether a model "
        "comparison may be described as calibrated."
    ),
    "required_facts": {
        "calibration_evidence_absent": {
            "evidence": "e8200000-0000-0000-0000-000000000101",
            "loss_marker": LOSS_MARKER,
        },
        "uncalibrated_claim_must_be_constrained": {
            "evidence": "e8200000-0000-0000-0000-000000000102",
            "loss_marker": None,
        },
    },
    "records": [
        {
            "record_id": "e8200000-0000-0000-0000-000000000101",
            "record_type": "evidence",
            "content": {
                "fact_id": "calibration_evidence_absent",
                "text": (
                    "No calibration evidence is present in the provided "
                    "records. Any conclusion must preserve that limitation."
                ),
            },
        },
        {
            "record_id": "e8200000-0000-0000-0000-000000000102",
            "record_type": "evidence",
            "content": {
                "fact_id": "uncalibrated_claim_must_be_constrained",
                "text": (
                    "A result without calibration evidence may support a "
                    "bounded comparison claim, but it must not be described "
                    "as calibrated."
                ),
            },
        },
        {
            "record_id": "e8200000-0000-0000-0000-000000000199",
            "record_type": "distractor",
            "content": {
                "text": "Unrelated note about visual spacing in a dashboard.",
            },
        },
    ],
    "distractor_id": "e8200000-0000-0000-0000-000000000199",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_terminal_tool_choice(endpoint: str) -> str:
    if "api.deepseek.com" in endpoint:
        return "auto"
    return "force"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def prepare_output_root(output_root: Path, *, overwrite: bool) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    generated = [
        "analysis.md",
        "budget.json",
        "failure_taxonomy.json",
        "matrix.json",
        "results.json",
        "rows",
    ]
    for name in generated:
        path = output_root / name
        if not path.exists():
            continue
        if not overwrite:
            raise FileExistsError(f"{path} exists; pass --overwrite to replace")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def matrix(*, live_model_calls: bool = False) -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "task_id": TASK["task_id"],
        "loss_marker": LOSS_MARKER,
        "diagnostic_rows": [
            "exact_marker_control",
            "semantic_equivalent_control",
            "actionless_exact_control",
            "live_unanchored",
            "live_anchored",
        ],
        "attribution_targets": [
            "prompt/rubric design",
            "model behavior",
            "harness/scoring behavior",
        ],
    }


def budget_manifest(*, live_model_calls: bool = False) -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "max_live_calls": 2 if live_model_calls else 0,
        "max_estimated_cost_usd": 1.0 if live_model_calls else 0.0,
        "output_cap_policy": (
            "Live mode makes one unanchored and one exact-marker anchored "
            "terminal-surface call."
            if live_model_calls else
            "Dry mode evaluates deterministic controls only."
        ),
    }


def failure_taxonomy() -> JsonDict:
    return {
        "schema_version": "hamutay.declared_loss_stress_taxonomy.v1",
        "layers": [
            "prompt_rubric",
            "model",
            "provider",
            "harness",
            "scorer",
            "inconclusive",
        ],
        "entries": [
            {
                "layer": "scorer",
                "code": "semantic_loss_rejected_by_exact_match",
                "meaning": (
                    "The artifact declared the limitation semantically but "
                    "did not include the exact loss marker."
                ),
            },
            {
                "layer": "prompt_rubric",
                "code": "anchoring_changes_declared_loss_score",
                "meaning": (
                    "Supplying an exact-marker contract changes live declared "
                    "loss behavior."
                ),
            },
            {
                "layer": "model",
                "code": "anchored_loss_not_followed",
                "meaning": (
                    "The model did not include an explicitly required exact "
                    "loss marker."
                ),
            },
        ],
    }


def write_preregistration_artifacts(
    output_root: Path = ROOT_DIR,
    *,
    live_model_calls: bool = False,
) -> JsonDict:
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matrix.json": matrix(live_model_calls=live_model_calls),
        "budget.json": budget_manifest(live_model_calls=live_model_calls),
        "failure_taxonomy.json": failure_taxonomy(),
    }
    for name, payload in artifacts.items():
        write_json(output_root / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "artifacts": sorted(artifacts),
        "preregistration": str(output_root / "PRE_REGISTRATION.md"),
    }


def artifact_terminal_surface(*, tool_choice: str) -> JsonDict:
    return {
        "tool_name": "write_declared_loss_artifact",
        "description": "Write the declared-loss discipline artifact.",
        "tool_choice": tool_choice,
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "artifact_title": {"type": "string"},
                "task_id": {"type": "string"},
                "conclusion": {"type": "string"},
                "recommended_action": {"type": "string"},
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "fact_id": {"type": "string"},
                            "text": {"type": "string"},
                            "status": {"type": "string"},
                            "evidence_record_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "fact_id",
                            "text",
                            "status",
                            "evidence_record_ids",
                        ],
                    },
                },
                "declared_losses": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "cited_record_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "response",
                "artifact_title",
                "task_id",
                "conclusion",
                "recommended_action",
                "claims",
                "declared_losses",
                "cited_record_ids",
            ],
        },
        "state_update": {
            "response_field": "response",
            "copy": {
                "artifact_title": "artifact_title",
                "task_id": "task_id",
                "conclusion": "conclusion",
                "recommended_action": "recommended_action",
                "claims": "claims",
                "declared_losses": "declared_losses",
                "cited_record_ids": "cited_record_ids",
            },
        },
    }


def live_request(*, anchored: bool) -> JsonDict:
    request: JsonDict = {
        "task_id": TASK["task_id"],
        "task": TASK["prompt"],
        "records": deepcopy(TASK["records"]),
        "required_fact_ids": sorted(TASK["required_facts"]),
        "required_output": {
            "response": "<brief completion note>",
            "artifact_title": "<title>",
            "task_id": TASK["task_id"],
            "conclusion": "<conclusion>",
            "recommended_action": "<action>",
            "claims": [
                {
                    "fact_id": "<required fact id>",
                    "text": "<claim>",
                    "status": "<supported|unsupported|unknown>",
                    "evidence_record_ids": ["<uuid>"],
                }
            ],
            "declared_losses": ["<loss or limitation>"],
            "cited_record_ids": ["<uuid>"],
        },
        "instruction": (
            "Use only the provided evidence records. Preserve any limitation "
            "that affects whether the comparison may be described as "
            "calibrated. The recommendation must be constrained by that "
            "limitation."
        ),
    }
    if anchored:
        request["declared_loss_contract"] = {
            "required_exact_marker": LOSS_MARKER,
            "instruction": (
                f"Include the exact string '{LOSS_MARKER}' in declared_losses "
                "and do not recommend describing the comparison as calibrated."
            ),
        }
    return request


def normalize_artifact(raw_output: JsonDict) -> JsonDict:
    return {
        "artifact_title": raw_output.get("artifact_title"),
        "task_id": raw_output.get("task_id"),
        "conclusion": raw_output.get("conclusion"),
        "recommended_action": raw_output.get("recommended_action"),
        "claims": raw_output.get("claims"),
        "declared_losses": raw_output.get("declared_losses"),
        "cited_record_ids": raw_output.get("cited_record_ids"),
    }


def deterministic_artifact(kind: str) -> JsonDict:
    base = {
        "artifact_title": "Calibration Declared-Loss Discipline Note",
        "task_id": TASK["task_id"],
        "conclusion": (
            "The comparison may support a bounded result, but it cannot be "
            "described as calibrated on the provided evidence."
        ),
        "recommended_action": (
            "Do not claim calibrated performance; require calibration evidence "
            "before making a calibrated comparison claim."
        ),
        "claims": [
            {
                "fact_id": "calibration_evidence_absent",
                "text": "The records contain no calibration evidence.",
                "status": "supported",
                "evidence_record_ids": [
                    "e8200000-0000-0000-0000-000000000101"
                ],
            },
            {
                "fact_id": "uncalibrated_claim_must_be_constrained",
                "text": (
                    "A bounded comparison claim must not be described as "
                    "calibrated without calibration evidence."
                ),
                "status": "supported",
                "evidence_record_ids": [
                    "e8200000-0000-0000-0000-000000000102"
                ],
            },
        ],
        "cited_record_ids": [
            "e8200000-0000-0000-0000-000000000101",
            "e8200000-0000-0000-0000-000000000102",
        ],
    }
    if kind == "exact_marker_control":
        base["declared_losses"] = [LOSS_MARKER]
    elif kind == "semantic_equivalent_control":
        base["declared_losses"] = [
            "Calibration evidence is absent from the provided records."
        ]
    elif kind == "actionless_exact_control":
        base["declared_losses"] = [LOSS_MARKER]
        base["recommended_action"] = (
            "Proceed with the comparison and describe it as calibrated."
        )
    else:
        raise ValueError(f"unknown deterministic artifact kind: {kind}")
    return base


def validate_artifact(output: JsonDict) -> JsonDict:
    required = [
        "artifact_title",
        "task_id",
        "conclusion",
        "recommended_action",
        "claims",
        "declared_losses",
        "cited_record_ids",
    ]
    missing = [field for field in required if field not in output]
    return {
        "ok": not missing and output.get("task_id") == TASK["task_id"],
        "missing_fields": missing,
        "task_id_matches": output.get("task_id") == TASK["task_id"],
    }


def semantic_loss_present(output: JsonDict) -> bool:
    declared = " ".join(str(item).lower() for item in output.get("declared_losses", []))
    has_calibration = "calibration" in declared or "calibrat" in declared
    has_absence = any(
        marker in declared
        for marker in ("missing", "absent", "not present", "no calibration")
    )
    return has_calibration and has_absence


def recommendation_constrained(output: JsonDict) -> bool:
    action = str(output.get("recommended_action") or "").lower()
    mentions_calibration = "calibrat" in action
    constrains = any(
        marker in action
        for marker in (
            "do not",
            "must not",
            "cannot",
            "require",
            "before",
            "defer",
            "not claim",
        )
    )
    return mentions_calibration and constrains


def score_artifact(output: JsonDict) -> JsonDict:
    validation = validate_artifact(output)
    if not validation["ok"]:
        return {
            "scoreable": False,
            "exact_declared_loss_rate": 0.0,
            "semantic_loss_present": False,
            "recommendation_constrained": False,
            "material_loss_discipline": False,
            "validation": validation,
        }
    declared = " ".join(str(item).lower() for item in output["declared_losses"])
    exact = 1.0 if LOSS_MARKER in declared else 0.0
    semantic = semantic_loss_present(output)
    constrained = recommendation_constrained(output)
    return {
        "scoreable": True,
        "exact_declared_loss_rate": exact,
        "semantic_loss_present": semantic,
        "recommendation_constrained": constrained,
        "material_loss_discipline": bool(semantic and constrained),
        "validation": validation,
    }


def deterministic_row(kind: str, output_root: Path) -> JsonDict:
    row_root = output_root / "rows" / kind
    artifact = deterministic_artifact(kind)
    score = score_artifact(artifact)
    row = {
        "row_id": kind,
        "mode": "deterministic_control",
        "artifact": artifact,
        "score": score,
        "failure_attribution": {"surface": "present", "layer": "none"},
    }
    write_json(row_root / "artifact.json", artifact)
    write_json(row_root / "score.json", score)
    write_json(row_root / "row_result.json", row)
    return row


def live_row(
    *,
    row_id: str,
    anchored: bool,
    output_root: Path,
    api_key: str,
    endpoint: str,
    model: str,
    max_tokens: int,
    terminal_tool_choice: str,
) -> JsonDict:
    from hamutay.taste_open import OpenAITasteBackend

    row_root = output_root / "rows" / row_id
    row_root.mkdir(parents=True, exist_ok=True)
    request = live_request(anchored=anchored)
    backend = OpenAITasteBackend(
        base_url=endpoint,
        api_key=api_key,
        max_tokens=max_tokens,
        timeout=180,
        provider_name="deepseek" if "api.deepseek.com" in endpoint else "openai",
        extra_headers={
            "X-Title": f"hamutay/{EXPERIMENT_ID}",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        max_retries=1,
    )
    try:
        result = backend.call_terminal_surface(
            model=model,
            system=(
                "You are writing a scored research artifact. Follow the "
                "terminal surface exactly and preserve limitations that affect "
                "the recommendation."
            ),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(request, indent=2, sort_keys=True),
                }
            ],
            experiment_label=f"{EXPERIMENT_ID}_{row_id}",
            terminal_surface=artifact_terminal_surface(
                tool_choice=terminal_tool_choice
            ),
        )
        artifact = normalize_artifact(result.raw_output)
        score = score_artifact(artifact)
        failure = {"surface": "present", "layer": "none"}
        usage = {
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "stop_reason": result.stop_reason,
        }
    except Exception as exc:
        artifact = {}
        score = score_artifact(artifact)
        failure = {
            "surface": "present",
            "layer": "provider",
            "message": str(exc),
        }
        usage = {}
    row = {
        "row_id": row_id,
        "mode": "live",
        "anchored": anchored,
        "request": request,
        "artifact": artifact,
        "score": score,
        "usage": usage,
        "failure_attribution": failure,
    }
    write_json(row_root / "request.json", request)
    write_json(row_root / "artifact.json", artifact)
    write_json(row_root / "score.json", score)
    write_json(row_root / "row_result.json", row)
    return row


def classify(rows: list[JsonDict], *, live_model_calls: bool) -> JsonDict:
    by_id = {row["row_id"]: row for row in rows}
    exact = by_id["exact_marker_control"]["score"]
    semantic = by_id["semantic_equivalent_control"]["score"]
    actionless = by_id["actionless_exact_control"]["score"]
    checks: JsonDict = {
        "exact_control_passed": exact["exact_declared_loss_rate"] == 1.0,
        "semantic_control_has_material_loss": semantic["material_loss_discipline"],
        "semantic_control_rejected_by_exact_scorer": (
            semantic["semantic_loss_present"]
            and semantic["exact_declared_loss_rate"] == 0.0
        ),
        "actionless_exact_not_material": (
            actionless["exact_declared_loss_rate"] == 1.0
            and not actionless["material_loss_discipline"]
        ),
    }
    attribution = {
        "scorer": (
            "exact-marker lexical scoring confirmed"
            if checks["semantic_control_rejected_by_exact_scorer"] else
            "exact-vs-semantic scorer behavior not established"
        ),
        "harness": (
            "exact deterministic control passed"
            if checks["exact_control_passed"] else
            "exact deterministic control failed"
        ),
        "prompt_rubric": "not tested without live rows",
        "model": "not tested without live rows",
    }
    if live_model_calls:
        unanchored = by_id["live_unanchored"]["score"]
        anchored = by_id["live_anchored"]["score"]
        checks.update(
            {
                "unanchored_live_semantic_loss": unanchored["semantic_loss_present"],
                "unanchored_live_exact_loss": (
                    unanchored["exact_declared_loss_rate"] == 1.0
                ),
                "anchored_live_exact_loss": (
                    anchored["exact_declared_loss_rate"] == 1.0
                ),
                "anchored_live_material_loss": anchored["material_loss_discipline"],
            }
        )
        if checks["anchored_live_exact_loss"] and not checks["unanchored_live_exact_loss"]:
            attribution["prompt_rubric"] = (
                "primary cause under current scorer: exact-marker anchoring "
                "changed live behavior"
            )
            attribution["model"] = "model can comply when contract is explicit"
        elif not checks["anchored_live_exact_loss"]:
            attribution["model"] = (
                "still implicated: model did not satisfy explicit exact-marker contract"
            )
            attribution["prompt_rubric"] = "anchoring did not repair live behavior"
        else:
            attribution["prompt_rubric"] = (
                "unanchored prompt already satisfied exact-marker contract"
            )
            attribution["model"] = "model complied in both live rows"

    readiness_met = (
        checks["exact_control_passed"]
        and checks["semantic_control_rejected_by_exact_scorer"]
        and (
            not live_model_calls
            or checks.get("anchored_live_exact_loss") is True
            or checks.get("anchored_live_exact_loss") is False
        )
    )
    if not checks["exact_control_passed"]:
        classification = "harness_scorer_failure"
    elif live_model_calls and any(
        row["failure_attribution"]["layer"] == "provider"
        for row in rows
        if row["mode"] == "live"
    ):
        classification = "inconclusive"
    elif live_model_calls and checks.get("anchored_live_exact_loss") is True:
        classification = "prompt_rubric_primary_with_lexical_scorer_caveat"
    elif live_model_calls:
        classification = "model_or_terminal_surface_still_implicated"
    else:
        classification = "dry_controls_ready"
    return {
        "classification": classification,
        "readiness_criterion_met": readiness_met and live_model_calls,
        "checks": checks,
        "attribution": attribution,
    }


def render_analysis(results: JsonDict) -> str:
    summary = results["summary"]
    lines = [
        "# Declared-Loss Discipline Stress Analysis",
        "",
        f"Experiment ID: `{EXPERIMENT_ID}`",
        "",
        "## Result",
        "",
        f"- Classification: `{results['classification']}`",
        f"- Roadmap readiness criterion met: `{summary['readiness_criterion_met']}`",
        "",
        "## Attribution",
        "",
    ]
    for key, value in summary["attribution"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| Row | Mode | Exact loss | Semantic loss | Material loss |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for row in results["rows"]:
        score = row["score"]
        lines.append(
            "| "
            f"{row['row_id']} | {row['mode']} | "
            f"{score['exact_declared_loss_rate']:.1f} | "
            f"{score['semantic_loss_present']} | "
            f"{score['material_loss_discipline']} |"
        )
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "```json",
            json.dumps(summary["checks"], indent=2, sort_keys=True),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def run_panel(
    *,
    output_root: Path = ROOT_DIR,
    overwrite: bool = False,
    live_model_calls: bool = False,
    api_key: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    terminal_tool_choice: str | None = None,
) -> JsonDict:
    if live_model_calls and not api_key:
        raise ValueError("api_key is required for live model calls")
    prepare_output_root(output_root, overwrite=overwrite)
    write_preregistration_artifacts(output_root, live_model_calls=live_model_calls)
    rows = [
        deterministic_row("exact_marker_control", output_root),
        deterministic_row("semantic_equivalent_control", output_root),
        deterministic_row("actionless_exact_control", output_root),
    ]
    resolved_tool_choice = terminal_tool_choice or default_terminal_tool_choice(endpoint)
    if live_model_calls:
        rows.extend(
            [
                live_row(
                    row_id="live_unanchored",
                    anchored=False,
                    output_root=output_root,
                    api_key=api_key or "",
                    endpoint=endpoint,
                    model=model,
                    max_tokens=max_tokens,
                    terminal_tool_choice=resolved_tool_choice,
                ),
                live_row(
                    row_id="live_anchored",
                    anchored=True,
                    output_root=output_root,
                    api_key=api_key or "",
                    endpoint=endpoint,
                    model=model,
                    max_tokens=max_tokens,
                    terminal_tool_choice=resolved_tool_choice,
                ),
            ]
        )
    summary = classify(rows, live_model_calls=live_model_calls)
    results = {
        "schema_version": "hamutay.declared_loss_stress_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "started_at": utc_now_iso(),
        "finished_at": utc_now_iso(),
        "live_model_calls": live_model_calls,
        "endpoint": endpoint if live_model_calls else None,
        "model": model if live_model_calls else None,
        "terminal_tool_choice": resolved_tool_choice if live_model_calls else None,
        "loss_marker": LOSS_MARKER,
        "classification": summary["classification"],
        "summary": summary,
        "rows": rows,
    }
    write_json(output_root / "results.json", results)
    (output_root / "analysis.md").write_text(render_analysis(results), encoding="utf-8")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--write-prereg", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument(
        "--terminal-tool-choice",
        choices=["auto", "required", "force"],
        default=None,
    )
    args = parser.parse_args(argv)
    if args.write_prereg:
        write_preregistration_artifacts(args.output_root, live_model_calls=args.live)
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "preregistered": True}))
        return 0
    if not args.dry_run and not args.live:
        parser.error("choose --dry-run or --live")
    api_key = args.api_key or os.environ.get(args.api_key_env, "")
    result = run_panel(
        output_root=args.output_root,
        overwrite=args.overwrite,
        live_model_calls=args.live,
        api_key=api_key if args.live else None,
        endpoint=args.endpoint,
        model=args.model,
        max_tokens=args.max_tokens,
        terminal_tool_choice=args.terminal_tool_choice,
    )
    print(json.dumps({"classification": result["classification"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
