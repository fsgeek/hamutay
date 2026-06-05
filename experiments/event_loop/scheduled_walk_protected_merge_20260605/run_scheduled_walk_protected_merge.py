"""Run strict scheduled-walk gate with live protected merge enabled."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from hamutay.apacheta_bridge import ApachetaBridge
from hamutay.taste_open import OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
STRICT_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/scheduled_walk_strict_continuity_20260605/"
    / "run_scheduled_walk_strict_continuity.py"
)
PROTECTED_STATE_FIELDS = {"cycle", "_activity_log"}


def load_strict_runner():
    spec = importlib.util.spec_from_file_location(
        "scheduled_walk_strict_continuity_base",
        STRICT_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load strict runner from {STRICT_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_protected_session(
    *,
    model: str,
    log_path: Path,
    label: str,
    bridge: ApachetaBridge,
    backend: Any,
) -> OpenTasteSession:
    return OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(log_path),
        experiment_label=label.replace(
            "scheduled_walk_strict_continuity",
            "scheduled_walk_protected_merge",
        ),
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=bridge,
        protected_state_fields=PROTECTED_STATE_FIELDS,
    )


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _diagnostics_from_record(record: dict) -> list[dict]:
    diagnostics: list[dict] = []
    top_level = record.get("state_merge_diagnostics")
    if isinstance(top_level, dict):
        diagnostics.append(top_level)
    validation = record.get("state_validation")
    if isinstance(validation, dict):
        repair = validation.get("repair")
        if isinstance(repair, dict):
            repair_diagnostic = repair.get("state_merge_diagnostics")
            if isinstance(repair_diagnostic, dict):
                diagnostics.append(repair_diagnostic)
    return diagnostics


def augment_results() -> None:
    results_path = EXP_DIR / "results.json"
    if not results_path.exists():
        return
    payload = json.loads(results_path.read_text())
    results = payload.get("results")
    if not isinstance(results, list):
        return

    for result in results:
        log_path = PROJECT_ROOT / str(result.get("log_path", ""))
        records = load_records(log_path)
        final_record = records[-1] if records else {}
        diagnostics = _diagnostics_from_record(final_record)
        ignored_updates = sorted({
            key
            for diagnostic in diagnostics
            for key in diagnostic.get("ignored_protected_updates", [])
        })
        ignored_deletions = sorted({
            key
            for diagnostic in diagnostics
            for key in diagnostic.get("ignored_protected_deletions", [])
        })
        result["protected_state_fields"] = sorted(PROTECTED_STATE_FIELDS)
        result["protected_merge_diagnostic_count"] = len(diagnostics)
        result["ignored_protected_updates"] = ignored_updates
        result["ignored_protected_deletions"] = ignored_deletions
        result["ignored_protected_attempt_count"] = sum(
            int(diagnostic.get("ignored_protected_attempt_count", 0))
            for diagnostic in diagnostics
        )

    summary = payload.setdefault("summary", {}).setdefault("summary", {})
    valid = [r for r in results if r.get("init_valid")]
    summary["protected_merge_diagnostic_count"] = sum(
        int(r.get("protected_merge_diagnostic_count") or 0) for r in valid
    )
    summary["ignored_protected_attempt_count"] = sum(
        int(r.get("ignored_protected_attempt_count") or 0) for r in valid
    )
    summary["ignored_protected_update_replicates"] = sum(
        bool(r.get("ignored_protected_updates")) for r in valid
    )
    summary["ignored_protected_deletion_replicates"] = sum(
        bool(r.get("ignored_protected_deletions")) for r in valid
    )
    payload["protected_state_fields"] = sorted(PROTECTED_STATE_FIELDS)
    results_path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    strict_runner = load_strict_runner()
    strict_runner.EXP_DIR = EXP_DIR
    strict_runner.PROJECT_ROOT = PROJECT_ROOT
    strict_runner.make_session = make_protected_session
    strict_runner.main()
    augment_results()


if __name__ == "__main__":
    main()
