"""Run the preregistered conditioned repair variant experiment."""

from __future__ import annotations

import json
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
SOURCE_LOG = (
    PROJECT_ROOT
    / "experiments/event_loop/strict_repair_walk_gate_20260605/"
    / "deepseek__deepseek-v4-pro_strict_repair_r04.jsonl"
)

MODEL = "deepseek/deepseek-v4-pro"
MAX_TOKENS = 2048
CALL_TIMEOUT_SECONDS = 180
HTTP_TIMEOUT_SECONDS = 60
SOURCE_CYCLE = 2
REPLICATES_PER_VARIANT = 2
VARIANTS = ("full_target", "field_values", "field_names_only")
REQUIRED_EDGE_TYPES = {"depends_on", "branches_from", "composes_with"}


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def make_backend(api_key: str, *, label: str) -> OpenAITasteBackend:
    return OpenAITasteBackend(
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


def baseline_observation(source_state: dict[str, Any]) -> dict[str, Any] | None:
    observations = source_state.get("observations")
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


def target_object(source_state: dict[str, Any]) -> dict[str, Any]:
    base = baseline_observation(source_state)
    observations = [base] if base is not None else []
    observations.append(direct_walk_observation())
    return {
        "response": (
            "Repaired durable state: four adjacent endpoints with depends_on, "
            "branches_from, and composes_with edges are now recorded."
        ),
        "probe_id": source_state.get("probe_id"),
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
    if not isinstance(observations, list) or len(observations) < 2:
        missing.append("observations.appended_direct_walk")
    return missing


def expected_field_values(source_state: dict[str, Any]) -> dict[str, Any]:
    return {
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


def repair_prompt(variant: str, source_state: dict[str, Any]) -> str:
    common = f"""
Conditioned repair variant: {variant}

You are being invoked after a known prose/object mismatch. The previous visible
response said graph-walk evidence was recorded, but the durable state below did
not actually carry that update.

Current durable state:
{json.dumps(source_state, indent=2, default=str)}

Missing or incorrect durable fields:
{json.dumps(missing_fields(source_state), indent=2)}

Evidence summary:
- The adjacent walk path had 4 entries.
- The distinct edge types were depends_on, branches_from, and composes_with.

The repair succeeds only if you author the missing information as top-level
fields in the object you produce this cycle. A prose explanation without those
top-level fields is still a failed repair.
""".strip()

    if variant == "full_target":
        variant_block = f"""
Complete target durable object:
{json.dumps(target_object(source_state), indent=2)}

Produce this durable object shape now. Replace only the response text if
needed; preserve the other top-level fields exactly.
""".strip()
    elif variant == "field_values":
        variant_block = f"""
Expected field-level values:
{json.dumps(expected_field_values(source_state), indent=2)}

Use these field-level values to update the durable object. Do not construct a
separate nested object; the repaired fields must be top-level fields.
""".strip()
    elif variant == "field_names_only":
        variant_block = """
Use the missing field names and evidence summary to repair the durable object.
Do not use a nested repair object. Preserve the existing probe_id and baseline
observation. Add the graph-walk evidence as top-level durable fields.
""".strip()
    else:
        raise ValueError(f"unknown variant: {variant}")

    return f"""
{common}

{variant_block}

Do not call read, search_project, bash, clock, memory_schema, recall, compare,
walk, search_memory, store, annotate_edge, or schedule_event. End with
think_and_respond.
""".strip()


def make_session(
    *,
    log_path: Path,
    api_key: str,
    label: str,
) -> OpenTasteSession:
    return OpenTasteSession(
        model=MODEL,
        backend=make_backend(api_key, label=label),
        log_path=str(log_path),
        experiment_label=label,
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
    )


def state_records_walk_evidence(state: dict[str, Any]) -> bool:
    observations = state.get("observations")
    final_edge_types = state.get("observed_walk_edge_types")
    edge_types = (
        {str(item) for item in final_edge_types}
        if isinstance(final_edge_types, list)
        else set()
    )
    return (
        state.get("walk_gate_status") == "woke"
        and state.get("observed_walk_endpoint_count") == 4
        and REQUIRED_EDGE_TYPES <= edge_types
        and isinstance(observations, list)
        and any(
            isinstance(item, dict) and item.get("kind") == "direct_walk"
            for item in observations
        )
    )


def repair_preserves_identity(
    *,
    state: dict[str, Any],
    source_state: dict[str, Any],
) -> bool:
    return (
        state.get("probe_id") == source_state.get("probe_id")
        and baseline_observation(state) == baseline_observation(source_state)
    )


def response_mentions_repair(response_text: str) -> bool:
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


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def run_variant_replicate(
    *,
    variant: str,
    replicate: int,
    api_key: str,
    source_state: dict[str, Any],
) -> dict[str, Any]:
    safe_model = safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{variant}_r{replicate + 1:02d}.jsonl"
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")

    label = f"conditioned_repair_{variant}_{safe_model}_r{replicate + 1:02d}"
    session = make_session(log_path=log_path, api_key=api_key, label=label)
    session.seed_state(source_state, cycle=SOURCE_CYCLE)

    result: dict[str, Any] = {
        "model": MODEL,
        "variant": variant,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "source_log": str(SOURCE_LOG.relative_to(PROJECT_ROOT)),
        "source_cycle": SOURCE_CYCLE,
        "source_probe_id": source_state.get("probe_id"),
        "seeded_walk_gate_status": source_state.get("walk_gate_status"),
        "seeded_missing_fields": missing_fields(source_state),
        "repair_prompt_class": variant,
        "error": None,
    }
    try:
        with bounded_call(f"{variant} r{replicate + 1} repair"):
            session.exchange(
                repair_prompt(variant, source_state),
                force_memory=None,
            )
    except Exception as exc:  # noqa: BLE001 -- failed replicates are data
        result["error"] = format_error(exc)

    records = load_records(log_path)
    final_record = records[-1] if records else {}
    final_state = final_record.get("state") or {}
    final_state = final_state if isinstance(final_state, dict) else {}
    durable_success = state_records_walk_evidence(final_state)
    visible_repair = response_mentions_repair(
        str(final_record.get("response_text", ""))
    )
    result.update({
        "cycle_count": len(records),
        "response_text": final_record.get("response_text", ""),
        "final_top_level_keys": sorted(final_state.keys()),
        "walk_gate_status": final_state.get("walk_gate_status"),
        "observed_walk_endpoint_count": final_state.get(
            "observed_walk_endpoint_count"
        ),
        "observed_walk_edge_types": final_state.get("observed_walk_edge_types"),
        "observation_count": (
            len(final_state["observations"])
            if isinstance(final_state.get("observations"), list)
            else None
        ),
        "durable_repair_success": durable_success,
        "repair_preserved_identity": (
            repair_preserves_identity(
                state=final_state,
                source_state=source_state,
            )
            if durable_success else False
        ),
        "visible_repair_prose": visible_repair,
        "visible_repair_without_durable_success": (
            visible_repair and not durable_success
        ),
        "remaining_missing_fields": missing_fields(final_state),
    })
    return result


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_variant = {
        variant: [r for r in results if r["variant"] == variant]
        for variant in VARIANTS
    }
    successes = [r for r in results if r.get("durable_repair_success")]
    return {
        "summary": {
            "n": len(results),
            "errors": sum(bool(r.get("error")) for r in results),
            "success_by_variant": {
                variant: sum(
                    bool(r.get("durable_repair_success"))
                    for r in variant_results
                )
                for variant, variant_results in by_variant.items()
            },
            "visible_repair_without_durable_success": sum(
                bool(r.get("visible_repair_without_durable_success"))
                for r in results
            ),
        },
        "hypothesis_results": {
            "H148_conditioned_full_target_repair_recovers_reliably": all(
                r.get("durable_repair_success")
                for r in by_variant["full_target"]
            ),
            "H149_conditioned_field_values_repair_can_recover": any(
                r.get("durable_repair_success")
                for r in by_variant["field_values"]
            ),
            "H150_conditioned_field_names_only_repair_can_recover": any(
                r.get("durable_repair_success")
                for r in by_variant["field_names_only"]
            ),
            "H151_repair_success_preserves_prior_identity_fields": (
                all(r.get("repair_preserved_identity") for r in successes)
                if successes else False
            ),
            "H152_variant_outcomes_are_auditable": all(
                key in result
                for result in results
                for key in (
                    "variant",
                    "source_cycle",
                    "seeded_missing_fields",
                    "repair_prompt_class",
                    "durable_repair_success",
                    "visible_repair_without_durable_success",
                )
            ),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "model": MODEL,
        "source_log": str(SOURCE_LOG.relative_to(PROJECT_ROOT)),
        "source_cycle": SOURCE_CYCLE,
        "variants": list(VARIANTS),
        "replicates_per_variant": REPLICATES_PER_VARIANT,
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
    results: list[dict[str, Any]] = []
    for variant in VARIANTS:
        for replicate in range(REPLICATES_PER_VARIANT):
            print(f"{MODEL} {variant} r{replicate + 1}")
            results.append(
                run_variant_replicate(
                    variant=variant,
                    replicate=replicate,
                    api_key=api_key,
                    source_state=source_state,
                )
            )
    write_results(results)
    payload = json.loads((EXP_DIR / "results.json").read_text())
    print(json.dumps({
        "summary": payload["summary"],
        "hypothesis_results": payload["hypothesis_results"],
    }, indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
