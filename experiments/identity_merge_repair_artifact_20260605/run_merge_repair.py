"""Build deterministic repair artifacts from captured merge failures."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[1]
INPUT_GLOB = "experiments/identity_merge_replay_20260605/*.jsonl"


def load_records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def captured_failure_records() -> list[tuple[Path, dict]]:
    records = []
    for path in sorted(PROJECT_ROOT.glob(INPUT_GLOB)):
        for record in load_records(path):
            if (
                record.get("status") == "failed"
                and record.get("failure_classification", {}).get("failure_stage")
                == "state_merge"
            ):
                records.append((path, record))
    return records


def normalize_heading(line: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", line.lower()).strip()


def section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    target = normalize_heading(heading)
    start = None
    for index, line in enumerate(lines):
        if target in normalize_heading(line):
            start = index + 1
            break
    if start is None:
        return []
    collected = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped == "---" and collected:
            break
        if stripped.startswith("###") and collected:
            break
        collected.append(line)
    return collected


def clean_markup(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    return " ".join(text.split()).strip()


def extract_numbered_items(lines: list[str]) -> list[dict]:
    items = []
    current: dict | None = None
    for line in lines:
        stripped = line.strip()
        match = re.match(r"^\d+\.\s+(.*)", stripped)
        if match:
            if current is not None:
                items.append(current)
            current = {"text": clean_markup(match.group(1)), "support": ""}
            continue
        if current is None:
            continue
        evidence = re.match(r"^-\s+Evidence\s*:\s*(.*)", clean_markup(stripped), re.I)
        if evidence:
            current["support"] = evidence.group(1).strip()
        elif stripped.startswith("-"):
            detail = clean_markup(stripped.lstrip("- "))
            current["support"] = (
                f"{current['support']} {detail}".strip()
                if current["support"]
                else detail
            )
    if current is not None:
        items.append(current)
    return items


def extract_bullet_items(lines: list[str]) -> list[dict]:
    items = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        text = clean_markup(stripped.lstrip("- "))
        if text:
            items.append({"text": text, "support": ""})
    return items


def candidate_row(
    *,
    kind: str,
    item: dict,
    source_field: str,
    source: dict,
) -> dict:
    return {
        "row_type": kind,
        "status": "candidate",
        "text": item["text"],
        "support": item.get("support") or "",
        "source_log_path": source["log_path"],
        "source_cycle": source["cycle"],
        "source_record_id": source["record_id"],
        "source_field": source_field,
        "accepted": False,
    }


def contamination_warnings(text: str, source: dict) -> list[dict]:
    warnings = []
    marker_re = re.compile(
        r"expected cost|contingency|hardware|cellular plans|\$\s?\d",
        re.I,
    )
    for line in text.splitlines():
        stripped = clean_markup(line.strip().lstrip("- "))
        if not stripped or not marker_re.search(stripped):
            continue
        if "$18k" in stripped.lower() or "$18,000" in stripped:
            continue
        warnings.append(
            {
                "row_type": "contamination_warning",
                "status": "candidate",
                "text": stripped,
                "warning_type": "unsupported_budget_or_cost_detail",
                "source_log_path": source["log_path"],
                "source_cycle": source["cycle"],
                "source_record_id": source["record_id"],
                "source_field": "response_text",
                "accepted": False,
            }
        )
    return warnings


def build_repair_artifact(path: Path, record: dict) -> dict:
    source = {
        "log_path": str(path.relative_to(PROJECT_ROOT)),
        "cycle": record.get("cycle"),
        "record_id": record.get("record_id"),
    }
    response_text = str(record.get("response_text") or "")
    invalidated = [
        candidate_row(
            kind="invalidated_assumption",
            item=item,
            source_field="response_text.Invalidated Assumptions",
            source=source,
        )
        for item in extract_numbered_items(
            section_lines(response_text, "Invalidated Assumptions")
        )
    ]
    constraints = [
        candidate_row(
            kind="constraint",
            item=item,
            source_field="response_text.New Constraints",
            source=source,
        )
        for item in extract_bullet_items(section_lines(response_text, "New Constraints"))
    ]
    goals = [
        candidate_row(
            kind="goal",
            item=item,
            source_field="response_text.Updated Goals",
            source=source,
        )
        for item in extract_bullet_items(section_lines(response_text, "Updated Goals"))
    ]
    next_actions = [
        candidate_row(
            kind="next_action",
            item=item,
            source_field="response_text.Next Actions",
            source=source,
        )
        for item in extract_numbered_items(section_lines(response_text, "Next Actions"))
    ]
    warnings = contamination_warnings(response_text, source)
    return {
        "record_type": "protocol_recovery",
        "recovery_type": "merge_failure_candidate_extraction",
        "status": "candidate",
        "accepted_state": None,
        "live_policy": "strict_reject",
        "source": source,
        "failure_classification": record.get("failure_classification"),
        "overlap_keys": record.get("failure_classification", {}).get(
            "overlap_keys", []
        ),
        "candidate_rows": invalidated + constraints + goals + next_actions,
        "contamination_warnings": warnings,
        "raw_update_excerpt": {
            "deleted_regions": record.get("deleted_regions"),
            "overlap_values": {
                key: record.get("raw_output", {}).get(key)
                for key in record.get("failure_classification", {}).get(
                    "overlap_keys", []
                )
            },
        },
    }


def summarize(artifacts: list[dict]) -> dict:
    candidate_rows = [row for artifact in artifacts for row in artifact["candidate_rows"]]
    warning_rows = [
        row for artifact in artifacts for row in artifact["contamination_warnings"]
    ]
    by_type: dict[str, int] = {}
    for row in candidate_rows + warning_rows:
        row_type = row["row_type"]
        by_type[row_type] = by_type.get(row_type, 0) + 1
    return {
        "failure_records_processed": len(artifacts),
        "candidate_rows": len(candidate_rows),
        "contamination_warnings": len(warning_rows),
        "candidate_rows_by_type": by_type,
        "accepted_state_count": sum(
            artifact.get("accepted_state") is not None for artifact in artifacts
        ),
        "live_policies": sorted({artifact.get("live_policy") for artifact in artifacts}),
        "all_rows_candidate": all(
            row.get("status") == "candidate" and row.get("accepted") is False
            for row in candidate_rows + warning_rows
        ),
    }


def run() -> None:
    artifacts = [
        build_repair_artifact(path, record)
        for path, record in captured_failure_records()
    ]
    payload = {
        "input_glob": INPUT_GLOB,
        "artifacts": artifacts,
        "summary": summarize(artifacts),
    }
    (EXP_DIR / "repair_results.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], indent=2))
    print(f"wrote {EXP_DIR / 'repair_results.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic repair artifacts from merge failures."
    )
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()
