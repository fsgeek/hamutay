"""Auto tool-choice follow-up for the narrow second-wake surface."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from hamutay.taste_open import ExchangeResult


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/second_wake_protocol_surface_20260605/"
    / "run_second_wake_protocol_surface.py"
)
OBJECT_FORCED_RESULTS_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/second_wake_protocol_surface_20260605/results.json"
)

CONDITION = "second_wake_protocol_surface_auto"
N_REPLICATES = 6


def load_base_runner():
    spec = importlib.util.spec_from_file_location(
        "second_wake_protocol_surface_base",
        BASE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load protocol surface runner from {BASE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base_runner = load_base_runner()
OriginalNarrowBackend = base_runner.NarrowSecondWakeBackend


class AutoToolChoiceNarrowBackend(OriginalNarrowBackend):
    """Same narrow terminal tool, with OpenAI tool_choice set to auto."""

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict] | None = None,
        tool_executor: Any | None = None,
    ) -> ExchangeResult:
        del experiment_label, extra_tools, tool_executor
        self.calls += 1
        oai_messages = [{"role": "system", "content": system}] + messages
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": self._max_tokens,
            "messages": oai_messages,
            "tools": [self._narrow_tool_def()],
            "tool_choice": "auto",
        }
        self._apply_openai_payload_options(payload)
        data = self._post_chat(payload)
        choice = data["choices"][0]
        raw_stop = choice.get("finish_reason") or "unknown"
        if raw_stop == "length":
            raise RuntimeError(
                "Auto narrow backend: finish_reason=length; refusing to parse "
                "possibly truncated structured output"
            )
        stop_reason = {
            "stop": "end_turn",
            "length": "max_tokens",
            "tool_calls": "tool_use",
        }.get(raw_stop, raw_stop)
        usage = data.get("usage", {})
        message = choice.get("message", {})
        tool_calls = message.get("tool_calls") or []
        for tool_call in tool_calls:
            fn = tool_call.get("function", {})
            if fn.get("name") != "complete_second_wake":
                continue
            narrow_output = self._parse_tool_arguments(
                "complete_second_wake",
                fn.get("arguments", ""),
            )
            return ExchangeResult(
                raw_output=self._durable_output(narrow_output),
                stop_reason=stop_reason,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            )
        if tool_calls:
            names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
            raise RuntimeError(
                "Auto narrow backend: tool_calls returned but missing "
                f"complete_second_wake (saw: {names})"
            )
        content = message.get("content", "")
        if content:
            raw_json = self._extract_json(content)
            if raw_json is not None:
                raw_json = self._unwrap_tool_echo(raw_json)
                params = raw_json.get("parameters") if raw_json.get("name") else raw_json
                if isinstance(params, dict):
                    return ExchangeResult(
                        raw_output=self._durable_output(params),
                        stop_reason=stop_reason,
                        input_tokens=usage.get("prompt_tokens", 0),
                        output_tokens=usage.get("completion_tokens", 0),
                    )
        raise RuntimeError("Auto narrow backend: no complete_second_wake output")


def stable_uuid(label: str):
    return uuid5(
        NAMESPACE_URL,
        f"hamutay-second-wake-protocol-surface-auto-20260605-{label}",
    )


def second_label(replicate: int) -> str:
    return f"second-wake-protocol-surface-auto-r{replicate + 1}"


def provider_tool_choice_failure(row: dict[str, Any]) -> bool:
    event_summary = row.get("event_summary")
    text = json.dumps(event_summary, default=str)
    return "tool_choice" in text and "Provider returned error" in text


def terminal_tool_missing(row: dict[str, Any]) -> bool:
    event_summary = row.get("event_summary")
    return "no complete_second_wake output" in json.dumps(event_summary, default=str)


def object_forced_baseline() -> dict[str, Any]:
    if not OBJECT_FORCED_RESULTS_PATH.exists():
        return {"available": False}
    payload = json.loads(OBJECT_FORCED_RESULTS_PATH.read_text())
    condition = (
        payload.get("summary", {})
        .get("conditions", {})
        .get("second_wake_protocol_surface", {})
    )
    rows = payload.get("results", [])
    return {
        "available": True,
        "path": str(OBJECT_FORCED_RESULTS_PATH.relative_to(PROJECT_ROOT)),
        "final_valid": condition.get("final_valid"),
        "provider_tool_choice_failures": sum(
            provider_tool_choice_failure(row)
            for row in rows
            if isinstance(row, dict)
        ),
        "delete_update_conflicts": condition.get("delete_update_conflicts"),
        "both_contexts_delivered": condition.get("both_contexts_delivered"),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    conditions = {
        CONDITION: base_runner.condition_summary(results),
    }
    baseline = object_forced_baseline()
    provider_failures = sum(provider_tool_choice_failure(row) for row in results)
    terminal_missing = sum(terminal_tool_missing(row) for row in results)
    both_delivered = sum(bool(row.get("both_contexts_delivered")) for row in results)
    final_valid = sum(bool(row.get("second_wake_state_valid")) for row in results)
    recovered = sum(
        bool(row.get("chain_final_answer_contains_code_phrase"))
        and bool(row.get("chain_final_evidence_uses_intermediate"))
        for row in results
    )
    delete_conflicts = sum(bool(row.get("delete_update_conflict")) for row in results)
    prior_provider_failures = int(baseline.get("provider_tool_choice_failures") or 0)
    return {
        "conditions": conditions,
        "object_forced_baseline": baseline,
        "provider_tool_choice_failures": provider_failures,
        "terminal_tool_missing_failures": terminal_missing,
        "substantive_task_success": recovered,
        "hypothesis_results": {
            "H351_provider_tool_choice_failures_reduced": (
                baseline.get("available") is True
                and provider_failures < prior_provider_failures
            ),
            "H352_context_delivery_at_least_5_of_6": both_delivered >= 5,
            "H353_final_valid_at_least_5_of_6": final_valid >= 5,
            "H354_delete_update_conflicts_remain_zero": delete_conflicts == 0,
            "H355_terminal_tool_missing_distinguishable": terminal_missing == 0
            or all(
                terminal_tool_missing(row)
                for row in results
                if "second_wake_record_missing" in (row.get("second_wake_failures") or [])
            ),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "second_wake_protocol_surface_auto_20260605",
        "model": base_runner.MODEL,
        "n_replicates": N_REPLICATES,
        "filtered_bound_field": base_runner.BOUND_FIELD,
        "results": results,
        "summary": aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def configure_base_runner() -> None:
    base_runner.EXP_DIR = EXP_DIR
    base_runner.RESULTS_PATH = RESULTS_PATH
    base_runner.CONDITION = CONDITION
    base_runner.N_REPLICATES = N_REPLICATES
    base_runner.NarrowSecondWakeBackend = AutoToolChoiceNarrowBackend
    base_runner.stable_uuid = stable_uuid
    base_runner.second_label = second_label
    base_runner.write_results = write_results


def main() -> None:
    configure_base_runner()
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    results: list[dict[str, Any]] = []
    if RESULTS_PATH.exists():
        prior = json.loads(RESULTS_PATH.read_text()).get("results", [])
        if isinstance(prior, list):
            results = base_runner.refresh_completed_results(
                [row for row in prior if isinstance(row, dict)]
            )
    done = base_runner.completed_replicates(results)
    for replicate in range(N_REPLICATES):
        if replicate + 1 in done:
            print(f"{CONDITION} r{replicate + 1} already recorded", flush=True)
            continue
        print(f"{CONDITION} r{replicate + 1}", flush=True)
        results.append(base_runner.run_replicate(replicate, api_key))
        done.add(replicate + 1)
        write_results(results)
    write_results(results)
    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
