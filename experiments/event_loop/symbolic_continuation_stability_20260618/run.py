from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "symbolic_continuation_stability_20260618"
ROOT_DIR = Path(__file__).resolve().parent
PROBE_RUN_PATH = (
    ROOT_DIR.parent
    / "live_sustained_loop_provider_readiness_20260617"
    / "run.py"
)
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_REPLICATIONS = 3

JsonDict = dict[str, Any]


def load_probe_module():
    spec = importlib.util.spec_from_file_location(
        "live_sustained_loop_provider_readiness_20260617",
        PROBE_RUN_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load probe module: {PROBE_RUN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, record: JsonDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n")


def read_jsonl(path: Path) -> list[JsonDict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


class DriftInjectionBackend:
    """Inject forbidden scheduler-owned fields into a live continuation output."""

    def __init__(self, wrapped, probe_module):
        self.wrapped = wrapped
        self.probe_module = probe_module
        self.injection_count = 0

    def call_terminal_surface(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        terminal_surface: JsonDict,
    ):
        result = self.wrapped.call_terminal_surface(
            model=model,
            system=system,
            messages=messages,
            experiment_label=experiment_label,
            terminal_surface=terminal_surface,
        )
        raw_output = json.loads(json.dumps(result.raw_output, default=str))
        continuation = raw_output.get("continuation_request")
        if (
            self.injection_count == 0
            and terminal_surface.get("tool_name") == "handle_inbound_ipc"
            and isinstance(continuation, dict)
        ):
            continuation["requested_context"] = [
                {
                    "tool": "recall",
                    "record_id": "00000000-0000-0000-0000-000000000001",
                    "field": "inbound_status",
                }
            ]
            continuation["terminal_surface"] = (
                self.probe_module.inbound_terminal_surface(tool_choice="auto")
            )
            continuation["event_id"] = "00000000-0000-0000-0000-000000000002"
            continuation["run_id"] = "00000000-0000-0000-0000-000000000003"
            self.injection_count += 1
        return self.probe_module.ExchangeResult(
            raw_output=raw_output,
            stop_reason=result.stop_reason,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cache_read_tokens=result.cache_read_tokens,
            cache_creation_tokens=result.cache_creation_tokens,
            tool_activity=result.tool_activity,
        )


def continuation_pending_records(run_root: Path) -> list[JsonDict]:
    return [
        record for record in read_jsonl(run_root / "events.jsonl")
        if record.get("record_type") == "event_status"
        and record.get("event_type") == "self_scheduled_reflection"
        and record.get("status") == "pending"
    ]


def completed_event_count(result: JsonDict) -> int:
    return int(result.get("event_summary", {}).get("status_counts", {}).get("completed", 0))


def summarize_run(*, name: str, mode: str, run_root: Path, result: JsonDict) -> JsonDict:
    pending_continuations = continuation_pending_records(run_root)
    ignored_fields = sorted({
        field
        for record in pending_continuations
        for field in record.get("ignored_model_authored_fields", []) or []
    })
    return {
        "name": name,
        "mode": mode,
        "run_root": str(run_root.relative_to(run_root.parents[2])),
        "classification": result.get("classification"),
        "success": result.get("success"),
        "failure_attribution": result.get("failure_attribution", []),
        "completed_event_count": completed_event_count(result),
        "binding_contracts": sorted({
            str(record.get("binding_contract"))
            for record in pending_continuations
            if record.get("binding_contract")
        }),
        "ignored_model_authored_fields": ignored_fields,
        "continuation_requested_context": [
            record.get("requested_context")
            for record in pending_continuations
        ],
        "continuation_terminal_surfaces": [
            (record.get("terminal_surface") or {}).get("tool_name")
            for record in pending_continuations
        ],
    }


def classify_panel(rows: list[JsonDict], *, expected_replications: int) -> JsonDict:
    passed_rows = [row for row in rows if row.get("classification") == "passed"]
    replication_rows = [row for row in rows if row.get("mode") == "replication"]
    adversarial_rows = [row for row in rows if row.get("mode") == "adversarial_drift"]
    total_completed_events = sum(int(row.get("completed_event_count", 0)) for row in rows)
    checks = {
        "all_rows_passed": len(passed_rows) == len(rows),
        "replication_count": len(replication_rows) == expected_replications,
        "adversarial_count": len(adversarial_rows) == 1,
        "repeated_live_wakes": total_completed_events >= (expected_replications + 1) * 3,
        "all_rows_use_symbolic_binding": all(
            row.get("binding_contracts") == [
                "framework_bound_symbolic_continuation.v1"
            ]
            for row in rows
        ),
        "adversarial_drift_was_ignored": any(
            {
                "requested_context",
                "terminal_surface",
            }.issubset(set(row.get("ignored_model_authored_fields", [])))
            for row in adversarial_rows
        ),
        "all_rows_have_attribution_surface": all(
            isinstance(row.get("failure_attribution"), list)
            for row in rows
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "total_completed_events": total_completed_events,
    }


def run_panel(
    *,
    output_root: Path = ROOT_DIR,
    overwrite: bool = False,
    live_model_calls: bool = False,
    api_key: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    replications: int = DEFAULT_REPLICATIONS,
    terminal_tool_choice: str | None = None,
) -> JsonDict:
    if output_root.exists() and overwrite:
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    probe = load_probe_module()
    terminal_tool_choice = terminal_tool_choice or probe.default_terminal_tool_choice(
        endpoint
    )
    if live_model_calls and not api_key:
        raise ValueError("api_key is required for live model calls")

    rows: list[JsonDict] = []
    for index in range(1, replications + 1):
        name = f"replication_{index:02d}"
        run_root = output_root / "runs" / name
        result = probe.run_probe(
            output_root=run_root,
            overwrite=True,
            live_model_calls=live_model_calls,
            api_key=api_key,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
        )
        rows.append(
            summarize_run(
                name=name,
                mode="replication",
                run_root=run_root,
                result=result,
            )
        )

    adversarial_name = "adversarial_drift_01"
    adversarial_root = output_root / "runs" / adversarial_name
    adversarial_backend = None
    if live_model_calls:
        live_backend = probe.make_live_backend(
            endpoint=endpoint,
            api_key=api_key or "",
            max_tokens=probe.DEFAULT_MAX_TOKENS,
        )
        adversarial_backend = DriftInjectionBackend(live_backend, probe)
    else:
        adversarial_backend = DriftInjectionBackend(
            probe.ScriptedTerminalBackend(
                probe.scripted_success_outputs(terminal_tool_choice)
            ),
            probe,
        )
    adversarial_result = probe.run_probe(
        output_root=adversarial_root,
        overwrite=True,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
        backend=adversarial_backend,
    )
    rows.append(
        summarize_run(
            name=adversarial_name,
            mode="adversarial_drift",
            run_root=adversarial_root,
            result=adversarial_result,
        )
    )

    summary = classify_panel(rows, expected_replications=replications)
    results = {
        "schema_version": "hamutay.symbolic_continuation_stability.v1",
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "endpoint": endpoint if live_model_calls else None,
        "model": model,
        "terminal_tool_choice": terminal_tool_choice,
        "classification": "passed" if summary["passed"] else "failed",
        "summary": summary,
        "rows": rows,
    }
    write_json(output_root / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT_DIR)
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--replications", type=int, default=DEFAULT_REPLICATIONS)
    parser.add_argument(
        "--terminal-tool-choice",
        choices=["auto", "required", "force"],
        default=None,
    )
    args = parser.parse_args(argv)
    api_key = os.environ.get(args.api_key_env) if args.live else None
    results = run_panel(
        output_root=args.output_root,
        overwrite=args.overwrite,
        live_model_calls=args.live,
        api_key=api_key,
        endpoint=args.endpoint,
        model=args.model,
        replications=args.replications,
        terminal_tool_choice=args.terminal_tool_choice,
    )
    print(json.dumps(results, indent=2, sort_keys=True, default=str))
    return 0 if results["classification"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
