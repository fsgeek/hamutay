"""Normalize event-loop scheduler result rows into a common envelope."""

from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "scheduler_result_envelope.v1"

INIT_KEYS = {
    "init_valid",
    "init_failure_reasons",
    "init_validation_status",
    "init_first_pass_status",
    "init_repair_attempted",
    "init_repaired",
    "init_repair_status",
    "init_repair_valid",
    "init_has_repair_validation",
    "init_has_repair_raw_output",
    "init_repair_failures",
}

SCHEDULER_KEYS = {
    "schedule_valid",
    "scheduled_event_count",
    "direct_scheduled_event_count",
    "valid_schedule_attempts",
    "event_completed",
    "event_persisted",
    "event_result_status",
    "event_count_in_cycle_log",
    "wake_status_woke",
    "expected_wake_cycle",
    "walk_context_event_count",
    "event_context_has_walk_path",
}

WAKE_KEYS = {
    "state_validation_status",
    "first_pass_validation_status",
    "repair_attempted",
    "repair_status",
    "repaired",
    "has_repair_validation",
    "has_repair_raw_output",
    "bounded_wake_calls",
}

ELIGIBLE_INITIALIZATION_CLASSES = {
    "first_pass_valid",
    "valid_legacy",
    "repaired_valid",
}


def _present(row: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in sorted(keys) if key in row}


def scheduler_relevant(row: dict[str, Any]) -> bool:
    return any(key in row for key in SCHEDULER_KEYS)


def event_completed(row: dict[str, Any]) -> bool:
    return row.get("event_completed") is True or row.get("event_result_status") == "completed"


def classify_initialization(row: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    used: list[str] = []
    missing: list[str] = []

    if row.get("init_repair_valid") is True:
        used.append("init_repair_valid=True")
        return "repaired_valid", used, missing

    if row.get("init_validation_status") == "repaired":
        used.append("init_validation_status=repaired")
        return "repaired_valid", used, missing

    if row.get("init_repaired") is True and row.get("init_repair_status") == "valid":
        used.extend(["init_repaired=True", "init_repair_status=valid"])
        return "repaired_valid", used, missing

    if row.get("init_validation_status") == "valid":
        used.append("init_validation_status=valid")
        return "first_pass_valid", used, missing

    if row.get("init_first_pass_status") == "valid":
        used.append("init_first_pass_status=valid")
        return "first_pass_valid", used, missing

    if row.get("init_valid") is False:
        used.append("init_valid=False")
        if row.get("init_failure_reasons"):
            used.append("init_failure_reasons")
        return "failed_or_culled", used, missing

    if row.get("init_valid") is True:
        used.append("init_valid=True")
        missing.extend(["init_validation_status", "init_first_pass_status"])
        return "valid_legacy", used, missing

    if scheduler_relevant(row):
        used.append("scheduler_surface_present")
        missing.append("initialization_evidence")
        return "unclassifiable", used, missing

    return "not_scheduler_scored", used, missing


def wake_summary(row: dict[str, Any], *, relevant: bool) -> dict[str, Any]:
    event_log_scoring = row.get("event_log_scoring")
    event_log_scoring = event_log_scoring if isinstance(event_log_scoring, dict) else {}

    validation_status = event_log_scoring.get("wake_validation_status")
    first_pass_status = event_log_scoring.get("wake_first_pass_status")
    repair_status = event_log_scoring.get("wake_repair_status")
    repair_attempted = event_log_scoring.get("wake_repair_attempted")
    repaired = event_log_scoring.get("wake_repaired")
    source = "event_log_scoring" if validation_status is not None else None

    if validation_status is None and row.get("state_validation_status") is not None:
        validation_status = row.get("state_validation_status")
        first_pass_status = row.get("first_pass_validation_status")
        repair_status = row.get("repair_status")
        repair_attempted = row.get("repair_attempted")
        repaired = row.get("repaired")
        source = "session_state_validation"

    if source is None:
        source = "absent" if relevant else "not_applicable"

    return {
        "validation_status": validation_status,
        "first_pass_status": first_pass_status,
        "repair_attempted": repair_attempted,
        "repair_status": repair_status,
        "repaired": repaired,
        "source": source,
        "fields": _present(row, WAKE_KEYS),
        "event_log_scoring": event_log_scoring or None,
    }


def normalize_row(
    *,
    experiment: str,
    result_index: int,
    results_path: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    relevant = scheduler_relevant(row)
    init_class, init_used, init_missing = classify_initialization(row)
    scheduler_score_eligible = init_class in ELIGIBLE_INITIALIZATION_CLASSES

    evidence_used = list(init_used)
    if relevant:
        evidence_used.append("scheduler_surface")
    if row.get("event_log_scoring") is not None:
        evidence_used.append("event_log_scoring")
    elif row.get("state_validation_status") is not None:
        evidence_used.append("state_validation_status")

    evidence_missing = list(init_missing)
    if relevant and row.get("event_log_scoring") is None and row.get("state_validation_status") is None:
        evidence_missing.append("wake_validation_provenance")

    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "experiment": experiment,
            "result_index": result_index,
            "results_path": results_path,
        },
        "identity": {
            "model": row.get("model"),
            "replicate": row.get("replicate"),
            "arm": row.get("arm"),
            "variant": row.get("variant"),
        },
        "initialization": {
            "class": init_class,
            "scheduler_score_eligible": scheduler_score_eligible,
            "fields": _present(row, INIT_KEYS),
        },
        "scheduler": {
            "relevant": relevant,
            "event_completed": event_completed(row),
            "fields": _present(row, SCHEDULER_KEYS),
        },
        "wake": wake_summary(row, relevant=relevant),
        "logs": {
            "log_path": row.get("log_path"),
            "event_log_path": row.get("event_log_path"),
            "source_log": row.get("source_log"),
        },
        "errors": {
            "error": row.get("error"),
            "context_error_count": row.get("context_error_count"),
        },
        "evidence": {
            "used": evidence_used,
            "missing": sorted(set(evidence_missing)),
        },
    }
