from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "live_sustained_loop_provider_readiness_20260617"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "live_sustained_loop_provider_readiness",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def test_dry_probe_makes_sustained_live_loop_behavior_knowable(tmp_path):
    module = load_module()

    results = module.run_probe(output_root=tmp_path, overwrite=True)

    assert results["classification"] == "passed"
    assert results["success"]["checks"] == {
        "clean_idle": True,
        "completed_three_events": True,
        "mixed_event_types": True,
        "no_context_errors": True,
        "no_lifecycle_anomalies": True,
        "no_outcome_warnings": True,
        "terminal_surface_sequence": True,
    }
    assert results["success"]["completed_types"] == [
        "inbound_message",
        "self_scheduled_reflection",
        "housekeeping",
    ]
    assert results["success"]["completed_terminal_surface_tools"] == [
        "handle_inbound_ipc",
        "complete_bound_continuation",
        "complete_housekeeping_audit",
    ]
    assert results["failure_attribution"] == []
    assert (tmp_path / "taste_open.jsonl").exists()
    assert (tmp_path / "events.jsonl").exists()
    assert (tmp_path / "restart_frontier.jsonl").exists()

    attempts = read_jsonl(tmp_path / "attempts.jsonl")
    event_attempts = [
        attempt for attempt in attempts
        if attempt["record_type"] == "event_attempt"
    ]
    assert [attempt["event_type"] for attempt in event_attempts] == [
        "inbound_message",
        "self_scheduled_reflection",
        "housekeeping",
    ]
    assert all(attempt["terminal_surface"] for attempt in attempts)
    assert results["event_summary"]["context_errors"] == []
    assert any(
        event["status"] == "pending"
        and event.get("recovered_by") == "restart_frontier"
        for event in read_jsonl(tmp_path / "events.jsonl")
    )


def test_provider_tool_choice_rejection_is_attributed(tmp_path):
    module = load_module()
    backend = module.ScriptedTerminalBackend(
        [RuntimeError("Thinking mode does not support this tool_choice")]
    )

    results = module.run_probe(
        output_root=tmp_path,
        overwrite=True,
        live_model_calls=True,
        api_key="test-key",
        backend=backend,
        endpoint="https://api.deepseek.com",
        terminal_tool_choice="force",
    )

    assert results["classification"] == "failed"
    assert results["stopped_after"] == "seed_exchange"
    failures = results["failure_attribution"]
    assert failures
    first = failures[0]["failure_attribution"]
    assert first["layer"] == "provider"
    assert first["code"] == "provider_rejected_tool_choice"
    assert first["surface"] == "present"


def test_missing_continuation_request_is_model_output_failure(tmp_path):
    module = load_module()
    backend = module.ScriptedTerminalBackend(
        [
            {
                "response": "live loop probe initialized",
                "probe_status": "ready",
                "open_items": [],
            },
            {
                "response": "accepted inbound IPC work",
                "inbound_status": "accepted",
                "open_items": [],
            }
        ]
    )

    results = module.run_probe(
        output_root=tmp_path,
        overwrite=True,
        backend=backend,
    )

    assert results["classification"] == "failed"
    assert results["stopped_after"] == "inbound_continuation_check"
    failures = results["failure_attribution"]
    assert failures
    first = failures[0]["failure_attribution"]
    assert first["layer"] == "model_output"
    assert first["code"] == "missing_continuation_request"
    assert first["surface"] == "present"


def test_symbolic_contract_ignores_model_authored_identity_and_surface(tmp_path):
    module = load_module()
    wrong_surface = module.inbound_terminal_surface(tool_choice="auto")
    backend = module.ScriptedTerminalBackend(
        [
            {
                "response": "live loop probe initialized",
                "probe_status": "ready",
                "open_items": [],
            },
            {
                "response": "accepted inbound IPC work",
                "inbound_status": "accepted",
                "open_items": [{"kind": "todo", "text": "finish inbound work"}],
                "continuation_request": {
                    "requested": True,
                    "purpose": "Finish inbound work from <result_record_id>.",
                    "symbolic_context": [
                        {
                            "source": "completed_wake_state",
                            "field": "inbound_status",
                        }
                    ],
                    "requested_context": [
                        {
                            "tool": "recall",
                            "record_id": "00000000-0000-0000-0000-000000000001",
                            "field": "inbound_status",
                        }
                    ],
                    "label": "wrong-terminal-surface",
                    "terminal_surface": wrong_surface,
                },
            },
            {
                "response": "continued with wrong surface",
                "inbound_status": "continued",
                "open_items": [],
                "continuation_request": {"requested": False},
            },
            {
                "response": "housekeeping audit complete",
                "open_items": [],
                "housekeeping_audit": {
                    "audit_index": 1,
                    "open_item_count": 0,
                    "status": "clean",
                },
            },
        ]
    )

    results = module.run_probe(
        output_root=tmp_path,
        overwrite=True,
        backend=backend,
    )

    assert results["classification"] == "passed"
    assert results["failure_attribution"] == []
    assert results["success"]["completed_terminal_surface_tools"] == [
        "handle_inbound_ipc",
        "complete_bound_continuation",
        "complete_housekeeping_audit",
    ]

    records = read_jsonl(tmp_path / "events.jsonl")
    inbound_completed = next(
        record for record in records
        if record.get("event_type") == "inbound_message"
        and record.get("status") == "completed"
    )
    continuation_pending = next(
        record for record in records
        if record.get("event_type") == "self_scheduled_reflection"
        and record.get("status") == "pending"
    )
    assert continuation_pending["binding_contract"] == (
        "framework_bound_symbolic_continuation.v1"
    )
    assert continuation_pending["ignored_model_authored_fields"] == [
        "requested_context",
        "terminal_surface",
    ]
    assert continuation_pending["terminal_surface"]["tool_name"] == (
        "complete_bound_continuation"
    )
    assert continuation_pending["requested_context"] == [
        {
            "tool": "recall",
            "record_id": inbound_completed["result_record_id"],
            "field": "inbound_status",
        }
    ]
