"""Probe operational literacy for identity-object state."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from hamutay.eval.state_activation_probe import _backend
from hamutay.eval.state_persistence_probe import _read_records
from hamutay.taste_open import OpenTasteSession


LITERACY_PREFIX = """\
Operational identity-object probe:

You are being tested on whether you can operate a durable identity object.
Use only the structured object you produce each cycle.
Do not use deleted_regions unless the user explicitly asks you to remove a
field. Replacing a field means writing the new value for that field, not
deleting it first.
"""


SEED_STATE = {
    "current_claim": "Scheduled reflection probably increases durable epistemic revision.",
    "revision_decision": "initialize",
    "evidence_register": [
        {
            "kind": "baseline",
            "observation": "Initial claim established before the probe.",
        }
    ],
    "state_use_norm": (
        "The identity object is the load-bearing continuity surface. "
        "Consequential epistemic changes belong in top-level fields."
    ),
    "continuity_contract": {
        "replace_me": "old",
        "preserve_me": "stable",
        "version": 1,
    },
}


EVENTS = [
    (
        "activate",
        "Counterevidence: a prior probe revised only in prose and did not update "
        "durable fields. Narrow current_claim, set revision_decision to revise, "
        "and append structured evidence. Response <=35 words.",
    ),
    (
        "replace",
        "Replace continuity_contract.replace_me with 'new'. Preserve "
        "continuity_contract.preserve_me and continuity_contract.version. Do not "
        "remove continuity_contract. Response <=25 words.",
    ),
    (
        "idle",
        "No new evidence has arrived. Preserve all durable fields unchanged "
        "except cycle bookkeeping. Response <=25 words.",
    ),
    (
        "generalize",
        "Add a new durable top-level field named boundary_condition with value "
        "'durable_update_required'. Preserve existing durable fields. "
        "Response <=25 words.",
    ),
    (
        "loss",
        "Declare a deferral rather than a revision: evidence is insufficient to "
        "claim memory injection improves continuity. Set revision_decision to "
        "defer and append structured evidence. Response <=35 words.",
    ),
]


LOAD_BEARING_FIELDS = {
    "current_claim",
    "revision_decision",
    "evidence_register",
    "state_use_norm",
    "continuity_contract",
}


@dataclass(frozen=True)
class CycleCheck:
    stage: str
    passed: bool
    reasons: list[str]
    response_snippet: str
    raw_update_keys: list[str]
    deleted_regions: list[str]
    evidence_type: str
    evidence_count: int


@dataclass(frozen=True)
class LiteracyResult:
    model: str
    condition: str
    replicate: int
    log_path: str
    cycles_observed: int
    passed_checks: int
    total_checks: int
    literacy_score: float
    delete_update_overlap: bool
    deleted_load_bearing_fields: bool
    response_state_mismatch: bool
    checks: list[CycleCheck]
    error: str | None


def _safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def _log_path(out_dir: Path, model: str, condition: str, replicate: int) -> Path:
    return out_dir / f"{_safe_model_name(model)}_{condition}_r{replicate:02d}.jsonl"


def _evidence_count(evidence: Any) -> int:
    if isinstance(evidence, list):
        return len(evidence)
    if isinstance(evidence, dict):
        return len(evidence)
    return 0


def _response_mentions_decision(response: str) -> bool:
    lowered = response.lower()
    return any(
        word in lowered
        for word in ("revise", "revised", "narrow", "defer", "deferred", "loss")
    )


def _deleted_regions(raw: dict[str, Any]) -> list[str]:
    deleted = raw.get("deleted_regions", [])
    return deleted if isinstance(deleted, list) else []


def _raw_update_keys(raw: dict[str, Any]) -> list[str]:
    return sorted(k for k in raw if k not in {"response", "deleted_regions", "updated_regions"})


def _has_delete_update_overlap(raw: dict[str, Any]) -> bool:
    return bool(set(_deleted_regions(raw)) & set(_raw_update_keys(raw)))


def _deleted_load_bearing(raw: dict[str, Any]) -> bool:
    return bool(set(_deleted_regions(raw)) & LOAD_BEARING_FIELDS)


def _state(record: dict[str, Any]) -> dict[str, Any]:
    state = record.get("state")
    return state if isinstance(state, dict) else {}


def _raw(record: dict[str, Any]) -> dict[str, Any]:
    raw = record.get("raw_output")
    return raw if isinstance(raw, dict) else {}


def _cycle_check(stage: str, record: dict[str, Any], previous: dict[str, Any]) -> CycleCheck:
    state = _state(record)
    raw = _raw(record)
    response = str(record.get("response_text") or raw.get("response") or "")
    evidence = state.get("evidence_register")
    evidence_count = _evidence_count(evidence)
    reasons: list[str] = []

    if _has_delete_update_overlap(raw):
        reasons.append("delete_update_overlap")
    if _deleted_load_bearing(raw):
        reasons.append("deleted_load_bearing")
    if "evidence_register" in state and not isinstance(evidence, list):
        reasons.append("evidence_register_not_list")

    if stage == "activate":
        if state.get("revision_decision") not in {"revise", "narrow"}:
            reasons.append("missing_revision_decision")
        if state.get("current_claim") == SEED_STATE["current_claim"]:
            reasons.append("claim_not_changed")
        if evidence_count < 2:
            reasons.append("evidence_not_appended")
        if _response_mentions_decision(response) and not (
            "current_claim" in raw and "revision_decision" in raw and "evidence_register" in raw
        ):
            reasons.append("response_state_mismatch")
    elif stage == "replace":
        contract = state.get("continuity_contract")
        if not isinstance(contract, dict):
            reasons.append("contract_not_dict")
        else:
            if contract.get("replace_me") != "new":
                reasons.append("replace_failed")
            if contract.get("preserve_me") != "stable":
                reasons.append("preserve_failed")
            if contract.get("version") != 1:
                reasons.append("version_changed")
        if "continuity_contract" in _deleted_regions(raw):
            reasons.append("replace_used_delete")
    elif stage == "idle":
        for key, previous_value in previous.items():
            if key == "cycle":
                continue
            if state.get(key) != previous_value:
                reasons.append(f"idle_changed_{key}")
    elif stage == "generalize":
        if state.get("boundary_condition") != "durable_update_required":
            reasons.append("new_field_missing")
        for key in LOAD_BEARING_FIELDS:
            if state.get(key) != previous.get(key):
                reasons.append(f"generalize_changed_{key}")
    elif stage == "loss":
        if state.get("revision_decision") != "defer":
            reasons.append("missing_defer_decision")
        if evidence_count <= _evidence_count(previous.get("evidence_register")):
            reasons.append("deferral_evidence_not_appended")
        if _response_mentions_decision(response) and "revision_decision" not in raw:
            reasons.append("defer_response_state_mismatch")

    return CycleCheck(
        stage=stage,
        passed=not reasons,
        reasons=reasons,
        response_snippet=response.replace("\n", " ")[:400],
        raw_update_keys=_raw_update_keys(raw),
        deleted_regions=_deleted_regions(raw),
        evidence_type=type(evidence).__name__,
        evidence_count=evidence_count,
    )


def run_condition(
    *,
    model: str,
    condition: str,
    replicate: int,
    out_dir: Path,
    max_tokens: int,
) -> LiteracyResult:
    if condition not in {"thin", "operational"}:
        raise ValueError(f"unsupported condition: {condition}")
    path = _log_path(out_dir, model, condition, replicate)
    prefix = LITERACY_PREFIX if condition == "operational" else ""
    session = OpenTasteSession(
        model=model,
        backend=_backend(model, max_tokens),
        log_path=str(path),
        experiment_label=f"identity_object_literacy_{condition}",
        system_prompt_prefix=prefix,
        enable_tools=False,
    )
    session.seed_state(SEED_STATE, cycle=0)

    previous = dict(SEED_STATE)
    checks: list[CycleCheck] = []
    error: str | None = None
    for stage, prompt in EVENTS:
        try:
            session.exchange(prompt)
            record = _read_records(path)[-1]
            check = _cycle_check(stage, record, previous)
            checks.append(check)
            previous = dict(_state(record))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            break

    records = _read_records(path)
    raw_records = [_raw(record) for record in records]
    passed = sum(check.passed for check in checks)
    total = len(EVENTS)
    return LiteracyResult(
        model=model,
        condition=condition,
        replicate=replicate,
        log_path=str(path),
        cycles_observed=len(records),
        passed_checks=passed,
        total_checks=total,
        literacy_score=passed / total,
        delete_update_overlap=any(_has_delete_update_overlap(raw) for raw in raw_records),
        deleted_load_bearing_fields=any(_deleted_load_bearing(raw) for raw in raw_records),
        response_state_mismatch=any(
            reason.endswith("response_state_mismatch")
            or reason == "response_state_mismatch"
            for check in checks
            for reason in check.reasons
        ),
        checks=checks,
        error=error,
    )


def summarize_results(results: list[LiteracyResult]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[LiteracyResult]] = {}
    for result in results:
        groups.setdefault((result.model, result.condition), []).append(result)

    summary: list[dict[str, Any]] = []
    for (model, condition), group in sorted(groups.items()):
        summary.append(
            {
                "model": model,
                "condition": condition,
                "replicates": len(group),
                "mean_literacy_score": sum(r.literacy_score for r in group) / len(group),
                "passed_runs": sum(r.passed_checks == r.total_checks for r in group),
                "delete_update_overlap": sum(r.delete_update_overlap for r in group),
                "deleted_load_bearing_fields": sum(r.deleted_load_bearing_fields for r in group),
                "response_state_mismatch": sum(r.response_state_mismatch for r in group),
                "errors": [r.error for r in group if r.error],
            }
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run identity-object literacy probe.")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--models",
        nargs="+",
        default=["deepseek/deepseek-v4-pro", "moonshotai/kimi-k2.6"],
    )
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=["thin", "operational"],
        choices=["thin", "operational"],
    )
    parser.add_argument("--replicates", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=6000)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[LiteracyResult] = []
    for model in args.models:
        for condition in args.conditions:
            for replicate in range(1, args.replicates + 1):
                result = run_condition(
                    model=model,
                    condition=condition,
                    replicate=replicate,
                    out_dir=out_dir,
                    max_tokens=args.max_tokens,
                )
                results.append(result)
                data = [asdict(result) for result in results]
                summary = summarize_results(results)
                (out_dir / "results.json").write_text(json.dumps(data, indent=2))
                (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    data = [asdict(result) for result in results]
    summary = summarize_results(results)
    print(json.dumps({"summary": summary, "results": data}, indent=2))


if __name__ == "__main__":
    main()
