"""Phase 2A entity-scoped wake-state contract probe."""

from __future__ import annotations

import argparse
import datetime as datetime_module
import importlib.util
import json
import os
import sys
import typing as typing_module
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]

EXPERIMENT_ID = "phase_2a_substrate_contract_20260618"
ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
YANANTIN_SRC_ROOT = PROJECT_ROOT.parent / "yanantin" / "src"
TIKSI_SRC_ROOT = PROJECT_ROOT.parent / "tiksi" / "src"
for path in (PROJECT_ROOT, SRC_ROOT, YANANTIN_SRC_ROOT, TIKSI_SRC_ROOT):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))
if not hasattr(datetime_module, "UTC"):
    datetime_module.UTC = datetime_module.timezone.utc
if not hasattr(typing_module, "Self"):
    from typing_extensions import Self

    typing_module.Self = Self

REPAIR_RUN_PATH = (
    ROOT_DIR.parent / "multi_entity_state_isolation_repair_20260618" / "run.py"
)
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096
UNDERLYING_DIRNAME = "underlying_multi_entity_state_isolation"
ENTITY_IDS = {"entity_red", "entity_blue"}
AUTHORIZED_SHARED_EVENT_TYPES = {
    "identity_isolation_audit",
    "multi_entity_artifact",
}
SCHEDULER_OWNED_FIELDS = {
    "event_id",
    "record_id",
    "run_id",
    "scheduled_by_record_id",
    "scheduled_by_cycle",
    "created_by_record_epoch",
    "scheduled_by_record_epoch",
    "record_uniquifier",
}


def load_repair_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "multi_entity_state_isolation_for_phase_2a",
        REPAIR_RUN_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {REPAIR_RUN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


REPAIR = load_repair_module()


def write_json(path: Path, record: JsonDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n")


def read_jsonl(path: Path) -> list[JsonDict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


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
            "contract": "CONTRACT.md",
            "underlying_protocol": "multi_entity_state_isolation_repair_20260618",
            "required_checks": [
                "private_entity_prior_state_isolated",
                "entity_identity_preserved",
                "authorized_shared_context_explicit",
                "audit_and_final_clean",
                "scheduler_owned_fields_not_model_authored",
                "failure_attribution_surface_present",
            ],
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 7 if live_model_calls else 0,
            "max_estimated_cost_usd": 3.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.phase_2a_substrate_contract_taxonomy.v1",
            "layers": [
                "state_isolation",
                "identity",
                "shared_context_authorization",
                "scheduler_field_ownership",
                "scheduler",
                "model_output",
                "provider",
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
        "contract": str(output_root / "CONTRACT.md"),
    }


def json_contains_entity(value: Any, entity_id: str) -> bool:
    return entity_id in json.dumps(value, sort_keys=True, default=str)


def private_entity_prior_state_observations(session_log: Path) -> JsonDict:
    observations: list[JsonDict] = []
    leaks: list[JsonDict] = []
    for record in read_jsonl(session_log):
        raw_output = record.get("raw_output")
        if not isinstance(raw_output, dict):
            continue
        entity_id = raw_output.get("entity_id")
        workstream_id = raw_output.get("workstream_id")
        if entity_id not in ENTITY_IDS:
            continue
        prior_state = record.get("prior_state") or {}
        foreign_mentions = sorted(
            other for other in ENTITY_IDS - {str(entity_id)}
            if json_contains_entity(prior_state, other)
        )
        observation = {
            "cycle": record.get("cycle"),
            "entity_id": entity_id,
            "workstream_id": workstream_id,
            "prior_state_keys": sorted(prior_state) if isinstance(prior_state, dict) else [],
            "foreign_entity_mentions": foreign_mentions,
        }
        observations.append(observation)
        if foreign_mentions:
            leaks.append(observation)
    return {
        "private_entity_prior_state_observations": observations,
        "private_entity_prior_state_leaks": leaks,
        "private_entity_prior_state_isolated": leaks == [] and len(observations) >= 4,
    }


def scheduler_owned_field_violations(session_log: Path) -> list[JsonDict]:
    violations: list[JsonDict] = []
    for record in read_jsonl(session_log):
        raw_output = record.get("raw_output")
        if not isinstance(raw_output, dict):
            continue
        authored = sorted(SCHEDULER_OWNED_FIELDS & set(raw_output))
        if authored:
            violations.append(
                {
                    "cycle": record.get("cycle"),
                    "record_id": record.get("record_id"),
                    "authored_scheduler_fields": authored,
                }
            )
    return violations


def authorized_shared_context_checks(event_log: Path) -> JsonDict:
    event_records = read_jsonl(event_log)
    pending_shared = [
        record for record in event_records
        if record.get("record_type") == "event_status"
        and record.get("status") == "pending"
        and record.get("event_type") in AUTHORIZED_SHARED_EVENT_TYPES
    ]
    observations: list[JsonDict] = []
    for record in pending_shared:
        requested_context = record.get("requested_context") or []
        observations.append(
            {
                "event_id": record.get("event_id"),
                "event_type": record.get("event_type"),
                "requested_context_count": len(requested_context),
                "record_ids": [
                    item.get("record_id") for item in requested_context
                    if isinstance(item, dict) and item.get("record_id")
                ],
            }
        )
    return {
        "authorized_shared_context_observations": observations,
        "authorized_shared_context_explicit": (
            len(observations) == 2
            and all(item["requested_context_count"] >= 2 for item in observations)
        ),
    }


def analyze_contract(output_root: Path, underlying_results: JsonDict) -> JsonDict:
    underlying_root = output_root / UNDERLYING_DIRNAME
    session_log = underlying_root / "taste_open.jsonl"
    event_log = underlying_root / "events.jsonl"
    prior_state = private_entity_prior_state_observations(session_log)
    shared_context = authorized_shared_context_checks(event_log)
    scheduler_violations = scheduler_owned_field_violations(session_log)
    underlying_success = underlying_results.get("success", {})
    underlying_checks = underlying_success.get("checks", {})
    checks = {
        "underlying_protocol_passed": underlying_results.get("classification") == "passed",
        "private_entity_prior_state_isolated": prior_state[
            "private_entity_prior_state_isolated"
        ],
        "entity_identity_preserved": underlying_checks.get(
            "entity_event_identity_preserved"
        ) is True,
        "authorized_shared_context_explicit": shared_context[
            "authorized_shared_context_explicit"
        ],
        "audit_and_final_clean": (
            underlying_checks.get("audit_no_contamination") is True
            and underlying_checks.get("audit_no_attribution_errors") is True
            and underlying_checks.get("final_no_contamination") is True
            and underlying_checks.get("final_no_attribution_errors") is True
        ),
        "scheduler_owned_fields_not_model_authored": scheduler_violations == [],
        "failure_attribution_surface_present": "failure_attribution" in underlying_results,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        **prior_state,
        **shared_context,
        "scheduler_owned_field_violations": scheduler_violations,
        "underlying_result_path": str(underlying_root / "results.json"),
        "underlying_classification": underlying_results.get("classification"),
    }


def failure_attribution(success: JsonDict) -> list[JsonDict]:
    if success["passed"]:
        return []
    failures: list[JsonDict] = []
    layers = {
        "underlying_protocol_passed": "scheduler",
        "private_entity_prior_state_isolated": "state_isolation",
        "entity_identity_preserved": "identity",
        "authorized_shared_context_explicit": "shared_context_authorization",
        "audit_and_final_clean": "model_output",
        "scheduler_owned_fields_not_model_authored": "scheduler_field_ownership",
        "failure_attribution_surface_present": "artifact",
    }
    for check, passed in success["checks"].items():
        if passed is not True:
            failures.append(
                {
                    "surface": "present",
                    "layer": layers.get(check, "artifact"),
                    "code": f"{check}_failed",
                    "check": check,
                }
            )
    return failures


def run_probe(
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
    if output_root.exists() and overwrite:
        import shutil

        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    write_preregistration_artifacts(output_root, live_model_calls=live_model_calls)
    underlying_root = output_root / UNDERLYING_DIRNAME
    underlying_results = REPAIR.run_probe(
        output_root=underlying_root,
        overwrite=True,
        live_model_calls=live_model_calls,
        api_key=api_key,
        endpoint=endpoint,
        model=model,
        max_tokens=max_tokens,
        terminal_tool_choice=terminal_tool_choice,
    )
    success = analyze_contract(output_root, underlying_results)
    failures = failure_attribution(success)
    classification = "passed" if success["passed"] and not failures else "failed"
    results = {
        "schema_version": "hamutay.phase_2a_substrate_contract.v1",
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "endpoint": endpoint if live_model_calls else None,
        "model": model,
        "terminal_tool_choice": terminal_tool_choice,
        "classification": classification,
        "success": success,
        "failure_attribution": failures,
        "evidence": {
            "contract": "CONTRACT.md",
            "underlying_run": UNDERLYING_DIRNAME,
            "underlying_results": f"{UNDERLYING_DIRNAME}/results.json",
        },
    }
    write_json(output_root / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--write-prereg", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT_DIR)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--terminal-tool-choice", default=None)
    args = parser.parse_args(argv)
    if args.write_prereg:
        write_preregistration_artifacts(args.output_root, live_model_calls=args.live)
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "preregistered": True}))
        return 0
    if not args.live and not args.dry_run:
        parser.error("choose --dry-run or --live")
    result = run_probe(
        output_root=args.output_root,
        overwrite=args.overwrite,
        live_model_calls=args.live,
        api_key=os.environ.get(args.api_key_env, "") if args.live else None,
        endpoint=args.endpoint,
        model=args.model,
        max_tokens=args.max_tokens,
        terminal_tool_choice=args.terminal_tool_choice,
    )
    print(json.dumps({"classification": result["classification"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
