"""Run the scheduler walk requested-context experiment."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.apacheta_bridge import ApachetaBridge
from hamutay.event_policies import (
    apply_fork_run_graph_plan,
    build_fork_run_graph_plan,
)
from hamutay.events import (
    build_event_envelope,
    build_pending_event,
    resolve_requested_context,
)

EXP_DIR = Path(__file__).resolve().parent


def now() -> datetime:
    return datetime.now(timezone.utc)


def store_state(
    bridge: ApachetaBridge,
    record_id: str,
    *,
    cycle: int,
    role: str,
) -> UUID:
    rid = UUID(record_id)
    bridge._prior_id = None
    bridge.store_open_state(
        {"cycle": cycle, "role": role},
        cycle=cycle,
        record_id=rid,
        timestamp=now(),
    )
    return rid


def build_projected_success_hub() -> dict[str, Any]:
    bridge = ApachetaBridge.from_memory(
        session_id="scheduler-walk-context",
        model="fake",
    )
    root = store_state(
        bridge,
        "00000000-0000-0000-0000-000000000001",
        cycle=2,
        role="coordinator",
    )
    branch_a = store_state(
        bridge,
        "00000000-0000-0000-0000-0000000000aa",
        cycle=3,
        role="branch-a",
    )
    branch_b = store_state(
        bridge,
        "00000000-0000-0000-0000-0000000000bb",
        cycle=3,
        role="branch-b",
    )
    join = store_state(
        bridge,
        "00000000-0000-0000-0000-0000000000cc",
        cycle=4,
        role="join",
    )
    final_run_record = {
        "fork_run_id": "scheduler-walk-success",
        "classification": "joined",
        "scheduled_by_cycle": 2,
        "scheduled_by_record_id": str(root),
        "branch_labels": ["branch-a", "branch-b"],
        "branch_events": {
            "branch-a": {
                "event_id": "event-a",
                "terminal_status": "completed",
                "result_record_id": str(branch_a),
            },
            "branch-b": {
                "event_id": "event-b",
                "terminal_status": "completed",
                "result_record_id": str(branch_b),
            },
        },
        "join_result_record_id": str(join),
    }
    plan = build_fork_run_graph_plan(final_run_record)
    applied = apply_fork_run_graph_plan(bridge=bridge, plan=plan, cycle=5)
    planned_record_ids = sorted(
        str(edge["target_record_id"]) for edge in plan["edges"]
    )
    return {
        "bridge": bridge,
        "plan": plan,
        "applied": applied,
        "planned_record_ids": planned_record_ids,
    }


def run_valid_walk_context() -> dict[str, Any]:
    projected = build_projected_success_hub()
    walk_request = {
        "tool": "walk",
        "from_record_id": projected["applied"]["fork_run_record_id"],
        "direction": "forward",
        "depth": 1,
        "mode": "adjacent",
    }
    event = build_pending_event(
        purpose="Inspect the completed fork-run graph neighborhood.",
        requested_context=[walk_request],
        scheduled_by_cycle=5,
        scheduled_by_record_id=UUID(projected["applied"]["fork_run_record_id"]),
        label="scheduler-walk-context",
    )
    context_results = resolve_requested_context(
        event["requested_context"],
        prior_states=[],
        bridge=projected["bridge"],
    )
    envelope_text = build_event_envelope(event, context_results, "run-walk-1")
    envelope = json.loads(envelope_text)
    walked_ids = [
        step["record_id"]
        for step in context_results[0]["result"].get("path", [])
    ]
    planned = set(projected["planned_record_ids"])
    return {
        "scenario": "valid_walk_context",
        "walk_request": walk_request,
        "event": event,
        "context_results": context_results,
        "envelope": envelope,
        "planned_record_ids": projected["planned_record_ids"],
        "walked_record_ids": walked_ids,
        "well_formed_walk_accepted": event["requested_context"] == [
            walk_request
        ],
        "walk_result_has_path": bool(
            context_results
            and isinstance(context_results[0].get("result"), dict)
            and context_results[0]["result"].get("path")
        ),
        "walk_reached_all_planned": planned <= set(walked_ids),
        "envelope_preserved_request": envelope["requested_context"] == [
            walk_request
        ],
        "envelope_preserved_result": (
            envelope["context_results"] == context_results
            and planned
            <= {
                step["record_id"]
                for item in envelope["context_results"]
                for step in item.get("result", {}).get("path", [])
            }
        ),
    }


def invalid_walk_cases() -> list[dict[str, Any]]:
    cases = [
        {
            "name": "missing_from_record_id",
            "request": {"tool": "walk", "direction": "forward"},
        },
        {
            "name": "invalid_direction",
            "request": {
                "tool": "walk",
                "from_record_id": "00000000-0000-0000-0000-000000000111",
                "direction": "sideways",
            },
        },
        {
            "name": "invalid_mode",
            "request": {
                "tool": "walk",
                "from_record_id": "00000000-0000-0000-0000-000000000111",
                "mode": "fanout",
            },
        },
        {
            "name": "invalid_depth",
            "request": {
                "tool": "walk",
                "from_record_id": "00000000-0000-0000-0000-000000000111",
                "depth": -1,
            },
        },
        {
            "name": "extra_key",
            "request": {
                "tool": "walk",
                "from_record_id": "00000000-0000-0000-0000-000000000111",
                "depth": 1,
                "field": "state",
            },
        },
    ]
    results = []
    for case in cases:
        accepted = False
        error = None
        try:
            build_pending_event(
                purpose="Invalid walk request.",
                requested_context=[case["request"]],
                scheduled_by_cycle=1,
                scheduled_by_record_id=UUID(
                    "00000000-0000-0000-0000-000000000001"
                ),
            )
            accepted = True
        except ValueError as exc:
            error = str(exc)
        results.append({**case, "accepted": accepted, "error": error})
    return results


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    valid = next(
        result for result in results if result["scenario"] == "valid_walk_context"
    )
    invalid = next(
        result for result in results if result["scenario"] == "invalid_walk_cases"
    )
    invalid_rejected = all(not case["accepted"] for case in invalid["cases"])
    return {
        "hypothesis_results": {
            "H120_scheduler_requested_context_accepts_walk": (
                valid["well_formed_walk_accepted"]
            ),
            "H121_scheduler_walk_context_resolves_memory_tool": (
                valid["walk_result_has_path"]
                and valid["walk_reached_all_planned"]
            ),
            "H122_event_envelope_preserves_walk_evidence": (
                valid["envelope_preserved_request"]
                and valid["envelope_preserved_result"]
            ),
            "H123_invalid_walk_context_rejected_before_persistence": (
                invalid_rejected
            ),
        },
        "summary": {
            "scenario_count": len(results),
            "valid_walk_endpoint_count": len(valid["walked_record_ids"]),
            "invalid_case_count": len(invalid["cases"]),
            "invalid_rejected_count": sum(
                not case["accepted"] for case in invalid["cases"]
            ),
        },
    }


def main() -> None:
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")
    results = [
        run_valid_walk_context(),
        {"scenario": "invalid_walk_cases", "cases": invalid_walk_cases()},
    ]
    payload = {"results": results, **aggregate(results)}
    (EXP_DIR / "results.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n"
    )
    print(json.dumps(payload["hypothesis_results"], indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
