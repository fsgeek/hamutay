"""Rescore recent identity panels with legacy and repaired contamination metrics."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[1]

PANELS = {
    "carryforward_representation": PROJECT_ROOT
    / "experiments/identity_carryforward_representation_20260604",
    "contamination_controls": PROJECT_ROOT
    / "experiments/identity_contamination_controls_20260604",
    "update_protocol": PROJECT_ROOT / "experiments/identity_update_protocol_20260604",
    "adversarial_curation": PROJECT_ROOT
    / "experiments/identity_adversarial_curation_20260604",
}

CONTAMINATION_PATTERNS = {
    "site_drift": [
        r"north center",
        r"\btwo sites\b|\btwo-site\b|\b2 sites\b",
        r"north library and west shelter only",
        r"north library and south center only",
        r"drop.*south center|exclude.*south center",
        r"east clinic",
    ],
    "storage_contradiction": [
        r"transient cache|transient-cache",
        r"local cache|local caching",
        r"persistent cache|persistent local",
        r"store.*document.*local",
        r"local.*document.*stor",
        r"encrypted local|local encrypted",
        r"buffer.*document|document.*buffer",
        r"offline buffer",
    ],
    "invented_scope": [
        r"four-week|four weeks|4-week|4 weeks",
        r"two-week|two weeks|2-week|2 weeks",
        r"city-?wide rollout",
        r"pilot findings|pilot outcomes|outcomes indicated",
        r"\b20\s*%|\b15\s*%|\bzero privacy incidents\b",
        r"thermal printer|thermal printers",
    ],
    "unsupported_detail": [
        r"android",
        r"mdm",
        r"soc 2|soc2|hipaa",
        r"4g|5g|cellular",
        r"factory reset",
        r"vendor",
        r"ada",
        r"ruggedized",
        r"hotspot",
        r"tablet",
        r"printer",
        r"sms|email confirmation",
    ],
}

DECLARED_LOSS_RE = re.compile(
    r"\b("
    r"invalidated|invalidates|no longer|not active|stale|former|previously|"
    r"prior assumption|assumption.*wrong|declared loss|discarded|superseded|"
    r"replaced|replaces|replacing|withdrawn|withdrew|dropped|removed|"
    r"ruled out|prohibited|forbidden|not permitted|not allowed|may not|"
    r"must not|cannot|can't|without|no local|no resident|uncertain|"
    r"unresolved|open question|risk|requires confirmation|needs confirmation|"
    r"confirm|validate|verify|reassess|pending"
    r")\b",
    re.IGNORECASE,
)

SITE_GUARD_RE = re.compile(
    r"\b(replac|withdraw|dropped|removed|invalid|former|previous|no longer|"
    r"not active|instead|west shelter)\b",
    re.IGNORECASE,
)

STORAGE_GUARD_RE = re.compile(
    r"\b(no |not |cannot|can't|may not|must not|without|prohibit|prohibited|"
    r"disallow|disallowed|ruled out|invalid|forbid|forbidden|zero local|"
    r"no local|not store|not storing|avoid local|open question|unresolved|"
    r"uncertain)\b",
    re.IGNORECASE,
)

DETAIL_GUARD_RE = re.compile(
    r"\b(unresolved|uncertain|open question|risk|requires confirmation|"
    r"needs confirmation|confirm|validate|verify|reassess|pending|not specified|"
    r"unsupported|over-specific|do not assume|not confirmed)\b",
    re.IGNORECASE,
)

SCOPE_GUARD_RE = re.compile(
    r"\b(unresolved|uncertain|not confirmed|invalid|unsupported|do not|"
    r"must remain six-week|six-week)\b",
    re.IGNORECASE,
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def late_visible_text(records: list[dict]) -> str:
    return "\n".join(
        record.get("response_text", "")
        for record in records
        if int(record.get("cycle", 0)) in {4, 5, 6}
    )


def windows_for_pattern(text: str, pattern: str, radius: int = 110) -> list[str]:
    windows = []
    lowered = text.lower()
    for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
        start = max(0, match.start() - radius)
        end = min(len(lowered), match.end() + radius)
        windows.append(" ".join(lowered[start:end].split()))
    return windows


def split_units(text: str) -> list[str]:
    raw_units = re.split(r"(?<=[.!?])\s+|\n+|(?:^|\s)[-*]\s+", text)
    return [" ".join(unit.split()) for unit in raw_units if unit.strip()]


def unit_for_window(text: str, pattern: str) -> list[str]:
    units = split_units(text)
    matches = []
    for unit in units:
        if re.search(pattern, unit, flags=re.IGNORECASE):
            matches.append(unit.lower())
    return matches


def is_guarded(category: str, pattern: str, window: str) -> bool:
    if category == "site_drift":
        if "east clinic" in window:
            return bool(SITE_GUARD_RE.search(window))
        return bool(DECLARED_LOSS_RE.search(window))
    if category == "storage_contradiction":
        return bool(STORAGE_GUARD_RE.search(window))
    if category == "unsupported_detail":
        return bool(DETAIL_GUARD_RE.search(window))
    if category == "invented_scope":
        return bool(SCOPE_GUARD_RE.search(window))
    return bool(DECLARED_LOSS_RE.search(window))


def count_invented_dollar_amounts(text: str) -> int:
    count = 0
    for match in re.finditer(r"\$\s*([0-9][0-9,]*(?:\.\d+)?)", text):
        amount = match.group(1).replace(",", "")
        if amount not in {"18000", "18"}:
            window = " ".join(
                text[max(0, match.start() - 90) : match.end() + 90].lower().split()
            )
            if not DETAIL_GUARD_RE.search(window):
                count += 1
    return count


def repaired_contamination_scores(text: str) -> dict:
    category_counts = {
        "repaired_site_drift_count": 0,
        "repaired_storage_contradiction_count": 0,
        "repaired_invented_scope_count": 0,
        "repaired_unsupported_detail_count": 0,
    }
    guarded_hits: list[dict] = []
    active_hits: list[dict] = []
    declared_loss_mentions = sum(
        1 for unit in split_units(text) if DECLARED_LOSS_RE.search(unit)
    )

    for category, patterns in CONTAMINATION_PATTERNS.items():
        category_key = f"repaired_{category}_count"
        for pattern in patterns:
            windows = windows_for_pattern(text, pattern)
            if not windows:
                continue
            pattern_active = False
            for window in windows:
                if is_guarded(category, pattern, window):
                    guarded_hits.append(
                        {
                            "category": category,
                            "pattern": pattern,
                            "window": window,
                        }
                    )
                else:
                    pattern_active = True
                    active_hits.append(
                        {
                            "category": category,
                            "pattern": pattern,
                            "window": window,
                        }
                    )
            if pattern_active:
                category_counts[category_key] += 1

    repaired_budget = count_invented_dollar_amounts(text)
    false_total = (
        category_counts["repaired_site_drift_count"]
        + category_counts["repaired_storage_contradiction_count"]
        + repaired_budget
        + category_counts["repaired_invented_scope_count"]
        + category_counts["repaired_unsupported_detail_count"]
    )
    return {
        **category_counts,
        "repaired_invented_budget_count": repaired_budget,
        "repaired_false_assumption_count": false_total,
        "declared_loss_mentions": declared_loss_mentions,
        "negated_or_invalidated_hits": len(guarded_hits),
        "active_contamination_hits": len(active_hits),
        "guarded_hit_examples": guarded_hits[:8],
        "active_hit_examples": active_hits[:8],
    }


def legacy_metrics(result: dict) -> dict:
    legacy = {}
    for key in [
        "site_drift_count",
        "storage_contradiction_count",
        "invented_budget_count",
        "invented_scope_count",
        "unsupported_detail_count",
        "false_assumption_count",
    ]:
        legacy[f"legacy_{key}"] = result.get(key)
    legacy_ratio = result.get("recovery_per_contamination")
    if legacy_ratio is None:
        legacy_ratio = repaired_tradeoff(
            result.get("recovery_total", 0),
            int(result.get("false_assumption_count") or 0),
        )
    legacy["legacy_recovery_per_contamination"] = legacy_ratio
    return legacy


def repaired_tradeoff(recovery: int | float | None, contamination: int | None) -> float | None:
    if contamination:
        return round(float(recovery or 0) / contamination, 3)
    return None


def rescore_run(panel_dir: Path, result: dict) -> dict:
    log_path = PROJECT_ROOT / result["log_path"]
    records = load_records(log_path)
    text = late_visible_text(records)
    repaired = repaired_contamination_scores(text)
    recovery = result.get("recovery_total", 0)
    return {
        "panel": panel_dir.name,
        "model": result.get("model"),
        "condition": result.get("condition"),
        "replicate": result.get("replicate"),
        "log_path": result.get("log_path"),
        "cycle_count": result.get("cycle_count"),
        "error": result.get("error"),
        "censored": result.get("censored"),
        "recovery_total": recovery,
        "carry_forward_chars": result.get("carry_forward_chars"),
        "carry_forward_truncated_count": result.get("carry_forward_truncated_count"),
        **legacy_metrics(result),
        **repaired,
        "repaired_recovery_per_contamination": repaired_tradeoff(
            recovery, repaired["repaired_false_assumption_count"]
        ),
    }


def avg(values: list[float | int | None]) -> float | None:
    items = [float(value) for value in values if value is not None]
    if not items:
        return None
    return round(mean(items), 3)


def summarize_group(group: list[dict]) -> dict:
    legacy = [int(row.get("legacy_false_assumption_count") or 0) for row in group]
    repaired = [int(row.get("repaired_false_assumption_count") or 0) for row in group]
    return {
        "n": len(group),
        "errors": sum(bool(row.get("error")) for row in group),
        "avg_recovery_total": avg([row.get("recovery_total") for row in group]),
        "avg_legacy_false_assumption_count": avg(legacy),
        "avg_repaired_false_assumption_count": avg(repaired),
        "legacy_false_assumption_sum": sum(legacy),
        "repaired_false_assumption_sum": sum(repaired),
        "false_assumption_delta_sum": sum(legacy) - sum(repaired),
        "declared_loss_mentions": sum(
            int(row.get("declared_loss_mentions") or 0) for row in group
        ),
        "negated_or_invalidated_hits": sum(
            int(row.get("negated_or_invalidated_hits") or 0) for row in group
        ),
        "avg_legacy_recovery_per_contamination": avg(
            [row.get("legacy_recovery_per_contamination") for row in group]
        ),
        "avg_repaired_recovery_per_contamination": avg(
            [row.get("repaired_recovery_per_contamination") for row in group]
        ),
        "avg_carry_forward_chars": avg([row.get("carry_forward_chars") for row in group]),
        "carry_forward_truncated_count": sum(
            int(row.get("carry_forward_truncated_count") or 0) for row in group
        ),
        "repaired_site_drift_sum": sum(
            int(row.get("repaired_site_drift_count") or 0) for row in group
        ),
        "repaired_storage_contradiction_sum": sum(
            int(row.get("repaired_storage_contradiction_count") or 0) for row in group
        ),
        "repaired_invented_budget_sum": sum(
            int(row.get("repaired_invented_budget_count") or 0) for row in group
        ),
        "repaired_invented_scope_sum": sum(
            int(row.get("repaired_invented_scope_count") or 0) for row in group
        ),
        "repaired_unsupported_detail_sum": sum(
            int(row.get("repaired_unsupported_detail_count") or 0) for row in group
        ),
    }


def best_condition(summary: dict, metric: str) -> str | None:
    best_name = None
    best_value = None
    for condition, values in summary.items():
        value = values.get(metric)
        if value is None:
            continue
        if best_value is None or value > best_value:
            best_name = condition
            best_value = value
    return best_name


def summarize_panel(rows: list[dict]) -> dict:
    conditions = sorted({row["condition"] for row in rows})
    by_condition = {
        condition: summarize_group([row for row in rows if row["condition"] == condition])
        for condition in conditions
    }
    return {
        "overall": summarize_group(rows),
        "by_condition": by_condition,
        "best_by_legacy_tradeoff": best_condition(
            by_condition, "avg_legacy_recovery_per_contamination"
        ),
        "best_by_repaired_tradeoff": best_condition(
            by_condition, "avg_repaired_recovery_per_contamination"
        ),
    }


def rescore_panels() -> dict:
    panels = {}
    all_rows = []
    for panel_name, panel_dir in PANELS.items():
        original = load_json(panel_dir / "results.json")
        rows = [rescore_run(panel_dir, result) for result in original["results"]]
        panels[panel_name] = {
            "source_dir": str(panel_dir.relative_to(PROJECT_ROOT)),
            "rows": rows,
            "summary": summarize_panel(rows),
        }
        all_rows.extend(rows)
    return {
        "scorer_version": "repaired_contamination_v1",
        "panels": panels,
        "overall": summarize_group(all_rows),
    }


def self_test() -> None:
    cases = [
        (
            "East Clinic was replaced by West Shelter. No local document storage is allowed.",
            0,
        ),
        (
            "Use East Clinic for the pilot and store resident documents in an encrypted local cache.",
            4,
        ),
        (
            "Vendor availability is unresolved; validate tablet requirements before use.",
            0,
        ),
        (
            "Deploy Android tablets with a thermal printer and SMS confirmation.",
            5,
        ),
    ]
    for text, expected in cases:
        got = repaired_contamination_scores(text)["repaired_false_assumption_count"]
        if got != expected:
            raise AssertionError(f"expected {expected}, got {got}: {text}")


def write_outputs(payload: dict) -> None:
    (EXP_DIR / "repaired_results.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    self_test()
    if args.self_test:
        print("self-test passed")
        return
    payload = rescore_panels()
    write_outputs(payload)
    print(json.dumps(payload["overall"], indent=2))
    print(f"wrote {EXP_DIR / 'repaired_results.json'}")


if __name__ == "__main__":
    main()
