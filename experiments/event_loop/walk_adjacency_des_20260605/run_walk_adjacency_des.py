"""Run the walk adjacency graph traversal experiment."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.apacheta_bridge import ApachetaBridge
from hamutay.event_policies import build_fork_run_graph_plan
from hamutay.tools.memory import tool_walk

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]


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


def apply_hub_projection(
    bridge: ApachetaBridge,
    final_run_record: dict[str, Any],
) -> dict[str, Any]:
    plan = build_fork_run_graph_plan(final_run_record)
    repeated_plan = build_fork_run_graph_plan(final_run_record)
    fork_run_record_id = bridge.store_instance_record(
        plan["fork_run_content"],
        cycle=99,
        tags=tuple(plan["fork_run_tags"]),
    )
    edges = []
    for edge in plan["edges"]:
        edge_id = bridge.store_edge(
            fork_run_record_id,
            UUID(str(edge["target_record_id"])),
            edge["relation"],
            ordering=99,
        )
        edges.append({
            **edge,
            "from_record_id": str(fork_run_record_id),
            "edge_id": str(edge_id),
        })

    suppression_nodes = []
    for item in plan["suppression_records"]:
        suppression_id = bridge.store_instance_record(
            item["content"],
            cycle=99,
            tags=("fork_run", "suppression", plan["fork_run_id"]),
        )
        edge_id = bridge.store_edge(
            fork_run_record_id,
            suppression_id,
            item["relation"],
            ordering=99,
        )
        suppression_nodes.append({
            "role": item["role"],
            "record_id": str(suppression_id),
            "from_record_id": str(fork_run_record_id),
            "edge_id": str(edge_id),
            "content": item["content"],
        })

    planned_targets = {
        str(edge["target_record_id"])
        for edge in plan["edges"]
    }
    planned_targets.update(
        node["record_id"] for node in suppression_nodes
    )
    return {
        "plan": plan,
        "plan_is_deterministic": plan == repeated_plan,
        "fork_run_record_id": str(fork_run_record_id),
        "edges": edges,
        "suppression_nodes": suppression_nodes,
        "planned_target_record_ids": sorted(planned_targets),
    }


def walk_record(
    bridge: ApachetaBridge,
    record_id: str,
    *,
    mode: str | None = None,
    depth: int,
) -> dict[str, Any]:
    params = {
        "from_record_id": record_id,
        "direction": "forward",
        "depth": depth,
    }
    if mode is not None:
        params["mode"] = mode
    return tool_walk(params, prior_states=[], bridge=bridge)


def summarize_walk(walk: dict[str, Any]) -> dict[str, Any]:
    path = walk.get("path", [])
    return {
        "count": len(path),
        "record_ids": [step["record_id"] for step in path],
        "depths": [step.get("depth") for step in path],
        "edge_types": [step.get("edge_type") for step in path],
    }


def run_success_star() -> dict[str, Any]:
    bridge = ApachetaBridge.from_memory(
        session_id="walk-adjacency-success",
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
        cycle=3,
        role="join",
    )
    final_run_record = {
        "fork_run_id": "walk-success",
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
    projection = apply_hub_projection(bridge, final_run_record)
    path_walk = walk_record(
        bridge,
        projection["fork_run_record_id"],
        depth=5,
    )
    adjacent_walk = walk_record(
        bridge,
        projection["fork_run_record_id"],
        mode="adjacent",
        depth=1,
    )
    reached = set(summarize_walk(adjacent_walk)["record_ids"])
    planned = set(projection["planned_target_record_ids"])
    return {
        "scenario": "success_star",
        "projection": projection,
        "path_walk": summarize_walk(path_walk),
        "adjacent_walk": summarize_walk(adjacent_walk),
        "adjacent_reached_all": planned <= reached,
        "path_is_single": len(path_walk.get("path", [])) == 1,
    }


def run_failure_star() -> dict[str, Any]:
    bridge = ApachetaBridge.from_memory(
        session_id="walk-adjacency-failure",
        model="fake",
    )
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
        "fork_run_id": "walk-failure",
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
    projection = apply_hub_projection(bridge, final_run_record)
    adjacent_walk = walk_record(
        bridge,
        projection["fork_run_record_id"],
        mode="adjacent",
        depth=1,
    )
    reached = set(summarize_walk(adjacent_walk)["record_ids"])
    planned = set(projection["planned_target_record_ids"])
    return {
        "scenario": "failure_star",
        "projection": projection,
        "adjacent_walk": summarize_walk(adjacent_walk),
        "adjacent_reached_all": planned <= reached,
        "suppression_nodes": projection["suppression_nodes"],
    }


def run_cycle_case() -> dict[str, Any]:
    bridge = ApachetaBridge.from_memory(
        session_id="walk-adjacency-cycle",
        model="fake",
    )
    a = store_state(
        bridge,
        "00000000-0000-0000-0000-000000000201",
        cycle=1,
        role="a",
    )
    b = store_state(
        bridge,
        "00000000-0000-0000-0000-000000000202",
        cycle=2,
        role="b",
    )
    c = store_state(
        bridge,
        "00000000-0000-0000-0000-000000000203",
        cycle=3,
        role="c",
    )
    bridge.store_edge(a, b, "BRIDGES", ordering=1)
    bridge.store_edge(b, c, "BRIDGES", ordering=2)
    bridge.store_edge(c, a, "BRIDGES", ordering=3)
    depth_one = walk_record(bridge, str(a), mode="adjacent", depth=1)
    depth_five = walk_record(bridge, str(a), mode="adjacent", depth=5)
    depth_five_ids = summarize_walk(depth_five)["record_ids"]
    return {
        "scenario": "cycle_case",
        "depth_one": summarize_walk(depth_one),
        "depth_five": summarize_walk(depth_five),
        "depth_one_bounded": summarize_walk(depth_one)["record_ids"] == [str(b)],
        "depth_five_no_repeats": len(depth_five_ids) == len(set(depth_five_ids)),
        "depth_five_does_not_return_start": str(a) not in depth_five_ids,
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_scenario = {result["scenario"]: result for result in results}
    success = by_scenario["success_star"]
    failure = by_scenario["failure_star"]
    cycle = by_scenario["cycle_case"]
    return {
        "hypothesis_results": {
            "H112_adjacent_walk_recovers_first_hop_endpoints": (
                success["adjacent_reached_all"]
                and failure["adjacent_reached_all"]
            ),
            "H113_default_path_walk_backward_compatible": (
                success["path_is_single"]
                and success["path_walk"]["count"] == 1
                and success["adjacent_walk"]["count"] > success["path_walk"]["count"]
            ),
            "H114_adjacent_walk_bounded_and_cycle_safe": (
                cycle["depth_one_bounded"]
                and cycle["depth_five_no_repeats"]
                and cycle["depth_five_does_not_return_start"]
            ),
            "H115_hub_projection_replaces_spine_projection": (
                success["adjacent_reached_all"]
                and failure["adjacent_reached_all"]
                and bool(failure["suppression_nodes"])
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
    results = [run_success_star(), run_failure_star(), run_cycle_case()]
    payload = {"results": results, **aggregate(results)}
    (EXP_DIR / "results.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n"
    )
    print(json.dumps(payload["hypothesis_results"], indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
