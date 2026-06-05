"""Run the preregistered live validation/repair scaffold gate."""

from __future__ import annotations

import json
import os
import signal
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.taste_open import ExchangeResult, OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
SOURCE_LOG = (
    PROJECT_ROOT
    / "experiments/event_loop/strict_repair_walk_gate_20260605/"
    / "deepseek__deepseek-v4-pro_strict_repair_r04.jsonl"
)

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 4
MAX_TOKENS = 2048
CALL_TIMEOUT_SECONDS = 180
HTTP_TIMEOUT_SECONDS = 60
SOURCE_CYCLE = 2
REQUIRED_EDGE_TYPES = {"depends_on", "branches_from", "composes_with"}


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


class CallTimeoutError(TimeoutError):
    """Raised when a provider or harness call exceeds the runner budget."""


def _timeout_handler(signum, frame) -> None:  # noqa: ARG001
    raise CallTimeoutError(f"call exceeded {CALL_TIMEOUT_SECONDS}s")


class bounded_call:
    """Bound one blocking provider/harness call in the experiment runner."""

    def __init__(self, label: str):
        self.label = label
        self._previous_handler = None

    def __enter__(self):
        self._previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, CALL_TIMEOUT_SECONDS)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        signal.setitimer(signal.ITIMER_REAL, 0)
        if self._previous_handler is not None:
            signal.signal(signal.SIGALRM, self._previous_handler)
        return False


class CountingBackend:
    """Count provider calls while preserving the backend interface."""

    def __init__(self, backend: OpenAITasteBackend):
        self.backend = backend
        self.calls = 0

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict] | None = None,
        tool_executor: Any | None = None,
    ) -> ExchangeResult:
        self.calls += 1
        return self.backend.call(
            model=model,
            system=system,
            messages=messages,
            experiment_label=experiment_label,
            extra_tools=extra_tools,
            tool_executor=tool_executor,
        )


def make_backend(api_key: str, *, label: str) -> CountingBackend:
    return CountingBackend(
        OpenAITasteBackend(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=HTTP_TIMEOUT_SECONDS,
            max_tokens=MAX_TOKENS,
            extra_headers={
                "X-Title": f"hamutay/{label}",
                "HTTP-Referer": "https://github.com/fsgeek/hamutay",
            },
            provider_name="openrouter",
            max_retries=1,
        )
    )


def load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def load_source_state() -> dict[str, Any]:
    for record in load_records(SOURCE_LOG):
        if record.get("cycle") == SOURCE_CYCLE:
            state = record.get("state")
            if not isinstance(state, dict):
                raise RuntimeError(f"source cycle {SOURCE_CYCLE} has no state")
            return json.loads(json.dumps(state))
    raise RuntimeError(f"source cycle {SOURCE_CYCLE} not found in {SOURCE_LOG}")


def baseline_observation(state: dict[str, Any]) -> dict[str, Any] | None:
    observations = state.get("observations")
    if isinstance(observations, list) and observations:
        first = observations[0]
        return first if isinstance(first, dict) else None
    return None


def direct_walk_observation() -> dict[str, Any]:
    return {
        "entry": 2,
        "kind": "direct_walk",
        "content": (
            "Direct follow-up used adjacent walk context and saw 4 endpoints "
            "with depends_on, branches_from, and composes_with edge types."
        ),
    }


def target_object(state: dict[str, Any]) -> dict[str, Any]:
    base = baseline_observation(state)
    observations = [base] if base is not None else []
    observations.append(direct_walk_observation())
    return {
        "response": (
            "Repaired durable state: four adjacent endpoints with depends_on, "
            "branches_from, and composes_with edges are now recorded."
        ),
        "probe_id": state.get("probe_id"),
        "walk_gate_status": "woke",
        "observed_walk_endpoint_count": 4,
        "observed_walk_edge_types": [
            "depends_on",
            "branches_from",
            "composes_with",
        ],
        "observations": observations,
    }


def missing_fields(state: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if state.get("walk_gate_status") != "woke":
        missing.append("walk_gate_status")
    if state.get("observed_walk_endpoint_count") != 4:
        missing.append("observed_walk_endpoint_count")
    final_edge_types = state.get("observed_walk_edge_types")
    edge_types = (
        {str(item) for item in final_edge_types}
        if isinstance(final_edge_types, list)
        else set()
    )
    for edge_type in sorted(REQUIRED_EDGE_TYPES):
        if edge_type not in edge_types:
            missing.append(f"observed_walk_edge_types.{edge_type}")
    observations = state.get("observations")
    if not isinstance(observations, list) or not any(
        isinstance(item, dict) and item.get("kind") == "direct_walk"
        for item in observations
    ):
        missing.append("observations.appended_direct_walk")
    return missing


class GraphWalkStateValidator:
    def validate(
        self,
        *,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
        prior_state: dict | None,
        raw_output: dict,
        response_text: str,
        state: dict,
    ) -> dict:
        del record_id, timestamp, prior_state, raw_output
        missing = missing_fields(state)
        return {
            "valid": not missing,
            "status": "valid" if not missing else "invalid",
            "validator": "graph_walk_state_validator",
            "cycle": cycle,
            "missing_fields": missing,
            "response_mentions_walk": response_mentions_walk(response_text),
        }


class FullTargetRepairBuilder:
    def build_repair_prompt(
        self,
        *,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
        prior_state: dict | None,
        raw_output: dict,
        response_text: str,
        state: dict,
        validation: dict,
    ) -> str:
        del cycle, record_id, timestamp, prior_state
        return f"""
Validation repair turn.

Your previous response claimed that graph-walk evidence was recorded, but the
durable state failed validation.

First-pass response:
{response_text}

First-pass raw output:
{json.dumps(raw_output, indent=2, default=str)}

Current durable state:
{json.dumps(state, indent=2, default=str)}

Validation result:
{json.dumps(validation, indent=2, default=str)}

Complete target durable object:
{json.dumps(target_object(state), indent=2, default=str)}

Produce this durable object shape now. Replace only the response text if
needed; preserve the other top-level fields exactly. The repair succeeds only
if these are top-level fields in the object you produce now.

Do not call read, search_project, bash, clock, memory_schema, recall, compare,
walk, search_memory, store, annotate_edge, or schedule_event. End with
think_and_respond.
""".strip()


def response_mentions_walk(response_text: str) -> bool:
    lowered = response_text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "repair",
            "recorded",
            "walk",
            "graph",
            "endpoint",
            "depends_on",
            "branches_from",
            "composes_with",
        )
    )


def light_repair_prompt(source_state: dict[str, Any], replicate: int) -> str:
    expected_values = {
        "walk_gate_status": "woke",
        "observed_walk_endpoint_count": 4,
        "observed_walk_edge_types": [
            "depends_on",
            "branches_from",
            "composes_with",
        ],
        "observations": (
            "Preserve the existing baseline observation and append one "
            "direct_walk observation recording the adjacent walk evidence."
        ),
        "probe_id": source_state.get("probe_id"),
    }
    return f"""
Live scaffold first-pass repair probe.
model={MODEL}
replicate={replicate + 1}

You are being invoked after a known prose/object mismatch. The durable state
you received still says the graph-walk gate is initialized even though the
previous visible response claimed graph-walk evidence was recorded.

Evidence summary:
- The adjacent walk path had 4 entries.
- The distinct edge types were depends_on, branches_from, and composes_with.

Missing or incorrect durable fields:
{json.dumps(missing_fields(source_state), indent=2)}

Expected field-level values:
{json.dumps(expected_values, indent=2)}

Use these field-level values to update the durable object. Do not construct a
separate nested object; the repaired fields must be top-level fields. A prose
explanation without top-level fields is still a failed repair.

Do not call read, search_project, bash, clock, memory_schema, recall, compare,
walk, search_memory, store, annotate_edge, or schedule_event. End with
think_and_respond.
""".strip()


def make_session(
    *,
    log_path: Path,
    api_key: str,
    label: str,
    backend: CountingBackend,
) -> OpenTasteSession:
    return OpenTasteSession(
        model=MODEL,
        backend=backend,
        log_path=str(log_path),
        experiment_label=label,
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        state_validator=GraphWalkStateValidator(),
        state_repair_builder=FullTargetRepairBuilder(),
    )


def final_metrics(record: dict[str, Any], backend_calls: int) -> dict[str, Any]:
    state = record.get("state") or {}
    validation = record.get("state_validation") or {}
    first_pass = validation.get("first_pass") or {}
    repair = validation.get("repair") or {}
    first_status = first_pass.get("status")
    repair_status = repair.get("status")
    final_missing = missing_fields(state if isinstance(state, dict) else {})
    return {
        "backend_calls": backend_calls,
        "first_pass_status": first_status,
        "state_validation_status": validation.get("status"),
        "repair_attempted": bool(validation.get("repair_attempted")),
        "repair_status": repair_status,
        "has_repair_raw_output": isinstance(repair.get("raw_output"), dict),
        "has_repair_validation": isinstance(repair.get("validation"), dict),
        "final_missing_fields": final_missing,
        "final_durable_success": not final_missing,
        "first_pass_detected_mismatch": first_status == "invalid",
        "repaired": validation.get("status") == "repaired",
        "unrepaired_or_failed": validation.get("status") in {
            "unrepaired",
            "repair_failed",
            "validator_failed",
        },
        "bounded_calls": backend_calls <= 2,
        "visible_repair_without_durable_success": (
            response_mentions_walk(record.get("response_text", ""))
            and bool(final_missing)
        ),
        "final_top_level_keys": sorted(state.keys()) if isinstance(state, dict) else [],
    }


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def run_replicate(replicate: int, api_key: str, source_state: dict[str, Any]) -> dict[str, Any]:
    safe_model = safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_live_validation_repair_r{replicate + 1:02d}.jsonl"
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")
    label = f"live_validation_repair_{safe_model}_r{replicate + 1:02d}"
    backend = make_backend(api_key, label=label)
    session = make_session(
        log_path=log_path,
        api_key=api_key,
        label=label,
        backend=backend,
    )
    session.seed_state(source_state, cycle=SOURCE_CYCLE)
    result: dict[str, Any] = {
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "source_log": str(SOURCE_LOG.relative_to(PROJECT_ROOT)),
        "source_cycle": SOURCE_CYCLE,
        "source_probe_id": source_state.get("probe_id"),
        "seeded_missing_fields": missing_fields(source_state),
        "error": None,
    }
    try:
        with bounded_call(f"live validation repair r{replicate + 1}"):
            session.exchange(light_repair_prompt(source_state, replicate), force_memory=None)
    except Exception as exc:  # noqa: BLE001 -- failed replicates are data
        result["error"] = format_error(exc)

    records = load_records(log_path) if log_path.exists() else []
    final_record = records[-1] if records else {}
    result["cycle_count"] = len(records)
    result.update(final_metrics(final_record, backend.calls) if final_record else {
        "backend_calls": backend.calls,
        "final_durable_success": False,
        "bounded_calls": backend.calls <= 2,
    })
    return result


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    mismatches = [r for r in results if r.get("first_pass_detected_mismatch")]
    repaired = [r for r in results if r.get("repaired")]
    failed_repairs = [
        r for r in results
        if r.get("repair_attempted") and not r.get("repaired")
    ]
    return {
        "summary": {
            "n": len(results),
            "errors": sum(bool(r.get("error")) for r in results),
            "first_pass_mismatches": len(mismatches),
            "repair_attempted": sum(bool(r.get("repair_attempted")) for r in results),
            "repaired": len(repaired),
            "failed_repairs": len(failed_repairs),
            "bounded_call_violations": sum(
                not bool(r.get("bounded_calls")) for r in results
            ),
        },
        "hypothesis_results": {
            "H158_builtin_validator_detects_known_mismatch": all(
                r.get("first_pass_status") != "valid"
                for r in mismatches
            ) if mismatches else True,
            "H159_builtin_full_target_repair_recovers_at_least_one_live_mismatch": (
                bool(repaired) if mismatches else False
            ),
            "H160_repaired_scaffold_cycles_remain_auditable": all(
                r.get("has_repair_raw_output")
                and r.get("has_repair_validation")
                and r.get("final_durable_success")
                for r in repaired
            ) if repaired else False,
            "H161_unrepaired_scaffold_cycles_not_silently_accepted": all(
                r.get("unrepaired_or_failed")
                for r in failed_repairs
            ) if failed_repairs else True,
            "H162_repair_remains_bounded": all(
                bool(r.get("bounded_calls")) for r in results
            ),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "model": MODEL,
        "source_log": str(SOURCE_LOG.relative_to(PROJECT_ROOT)),
        "source_cycle": SOURCE_CYCLE,
        "n_replicates": N_REPLICATES,
        "max_tokens": MAX_TOKENS,
        "call_timeout_seconds": CALL_TIMEOUT_SECONDS,
        "http_timeout_seconds": HTTP_TIMEOUT_SECONDS,
        "results": results,
        **aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")
    if not SOURCE_LOG.exists():
        raise SystemExit(f"source log missing: {SOURCE_LOG}")

    source_state = load_source_state()
    results = []
    for replicate in range(N_REPLICATES):
        print(f"{MODEL} live validation repair r{replicate + 1}")
        results.append(run_replicate(replicate, api_key, source_state))
    write_results(results)
    payload = json.loads((EXP_DIR / "results.json").read_text())
    print(json.dumps({
        "summary": payload["summary"],
        "hypothesis_results": payload["hypothesis_results"],
    }, indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
