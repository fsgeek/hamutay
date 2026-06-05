"""Run the fork-run hub projection experiment."""

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
from hamutay.tools.memory import tool_walk

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


def walk_ids(
    bridge: ApachetaBridge,
    record_id: str,
    *,
    mode: str | None = None,
    depth: int,
) -> list[str]:
    params = {
        "from_record_id": record_id,
        "direction": "forward",
        "depth": depth,
    }
    if mode is not None:
        params["mode"] = mode
    result = tool_walk(params, prior_states=[], bridge=bridge)
    return [step["record_id"] for step in result.get("path", [])]


def project_and_score(
    *,
    bridge: ApachetaBridge,
    final_run_record: dict[str, Any],
    cycle: int = 99,
) -> dict[str, Any]:
    plan = build_fork_run_graph_plan(final_run_record)
    applied = apply_fork_run_graph_plan(bridge=bridge, plan=plan, cycle=cycle)
    path_ids = walk_ids(
        bridge,
        applied["fork_run_record_id"],
        depth=len(plan["edges"]) + len(plan["suppression_records"]) + 1,
    )
    adjacent_ids = walk_ids(
        bridge,
        applied["fork_run_record_id"],
        mode="adjacent",
        depth=1,
    )
    planned = {edge["target_record_id"] for edge in plan["edges"]}
    planned.update(node["record_id"] for node in applied["suppression_nodes"])
    hub_edges = all(
        edge["from_record_id"] == applied["fork_run_record_id"]
        for edge in applied["edges"]
    ) and all(
        node["from_record_id"] == applied["fork_run_record_id"]
        for node in applied["suppression_nodes"]
    )
    return {
        "plan": plan,
        "applied": applied,
        "path_record_ids": path_ids,
        "adjacent_record_ids": adjacent_ids,
        "planned_record_ids": sorted(planned),
        "hub_edges": hub_edges,
        "path_is_single": len(path_ids) == 1,
        "adjacent_reached_all": planned <= set(adjacent_ids),
    }


def run_success() -> dict[str, Any]:
    bridge = ApachetaBridge.from_memory(session_id="hub-success", model="fake")
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
        cycle=3,
        role="join",
    )
    final_run_record = {
        "fork_run_id": "hub-success",
        "classification": "joined",
        "scheduled_by_cycle": 2,
        "scheduled_by_record_id": str(root),
        "branch_labels": ["branch-a", "branch-b"],
        "branch_events": {
            "branch-a": {
                "terminal_status": "completed",
                "result_record_id": str(branch_a),
            },
            "branch-b": {
                "terminal_status": "completed",
                "result_record_id": str(branch_b),
            },
        },
        "join_result_record_id": str(join),
    }
    projection = project_and_score(
        bridge=bridge,
        final_run_record=final_run_record,
    )
    return {
        "scenario": "hub_success",
        "classification": "joined",
        "projection": projection,
    }


def run_failure() -> dict[str, Any]:
    bridge = ApachetaBridge.from_memory(session_id="hub-failure", model="fake")
    root = store_state(
        bridge,
        "00000000-0000-0000-0000-000000000101",
        cycle=2,
        role="coordinator",
    )
    failed = store_state(
        bridge,
        "00000000-0000-0000-0000-0000000001aa",
        cycle=3,
        role="failed-branch",
    )
    final_run_record = {
        "fork_run_id": "hub-failure",
        "classification": "branch_failed",
        "scheduled_by_cycle": 2,
        "scheduled_by_record_id": str(root),
        "branch_labels": ["branch-a", "branch-b"],
        "failed_branch": "branch-a",
        "failed_branch_wake_record_id": str(failed),
        "branch_events": {
            "branch-a": {
                "event_id": "event-a",
                "terminal_status": "failed",
            },
            "branch-b": {
                "event_id": "event-b",
                "terminal_status": "suppressed",
            },
        },
        "suppressed_events": ["event-b"],
        "suppression_records": [
            {
                "event_id": "event-b",
                "suppressed_by_record_id": str(failed),
                "suppressed_by_cycle": 3,
                "suppressed_by_policy": "fork_join_policy_runner",
                "suppression_reason": "branch failure",
            }
        ],
    }
    projection = project_and_score(
        bridge=bridge,
        final_run_record=final_run_record,
    )
    suppression_nodes = projection["applied"]["suppression_nodes"]
    suppression_node = suppression_nodes[0] if suppression_nodes else {}
    return {
        "scenario": "hub_failure",
        "classification": "branch_failed",
        "projection": projection,
        "suppression_node": suppression_node,
        "suppression_names_event": bool(
            suppression_node.get("content", {}).get("suppressed_event_id")
        ),
        "suppression_names_source": bool(
            suppression_node.get("content", {}).get("suppressed_by_record_id")
        ),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_scenario = {result["scenario"]: result for result in results}
    success = by_scenario["hub_success"]
    failure = by_scenario["hub_failure"]
    return {
        "hypothesis_results": {
            "H116_projection_helper_writes_hub_edges": (
                success["projection"]["hub_edges"]
                and failure["projection"]["hub_edges"]
            ),
            "H117_adjacent_walk_recovers_all_hub_endpoints": (
                success["projection"]["adjacent_reached_all"]
                and failure["projection"]["adjacent_reached_all"]
            ),
            "H118_default_path_walk_single_path_compatible": (
                success["projection"]["path_is_single"]
                and failure["projection"]["path_is_single"]
                and len(success["projection"]["adjacent_record_ids"])
                > len(success["projection"]["path_record_ids"])
            ),
            "H119_failure_hub_projection_preserves_suppression": (
                failure["suppression_names_event"]
                and failure["suppression_names_source"]
                and failure["suppression_node"].get("from_record_id")
                == failure["projection"]["applied"]["fork_run_record_id"]
                and failure["projection"]["adjacent_reached_all"]
            ),
        },
        "summary": {
            "scenario_count": len(results),
            "scenarios": list(by_scenario),
        },
    }


def main() -> None:
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")
    results = [run_success(), run_failure()]
    payload = {"results": results, **aggregate(results)}
    (EXP_DIR / "results.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n"
    )
    print(json.dumps(payload["hypothesis_results"], indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
