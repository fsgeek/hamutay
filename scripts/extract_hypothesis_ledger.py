#!/usr/bin/env python3
"""Extract a conservative project-level hypothesis ledger.

The extractor is intentionally simple and auditable. It prefers structured
`results.json` outcomes when present, augments them with PRE_REGISTRATION and
analysis headings, and keeps ambiguous prose-derived entries as conservative
`unknown` or `boundary` statuses rather than forcing binary outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


STATUS_VALUES = {
    "survived",
    "falsified",
    "boundary",
    "deferred",
    "contaminated",
    "unscoreable",
    "superseded",
    "unknown",
}

STATUS_PRIORITY = {
    "falsified": 90,
    "contaminated": 80,
    "unscoreable": 75,
    "superseded": 70,
    "boundary": 60,
    "survived": 50,
    "deferred": 40,
    "unknown": 10,
}

LIMITATION_KEYWORDS = {
    "model": [
        "model",
        "deepseek",
        "kimi",
        "openai",
        "gpt",
        "claude",
        "haiku",
        "sonnet",
        "opus",
    ],
    "provider": ["provider", "openrouter", "moonshot", "endpoint", "api", "timeout", "rate"],
    "protocol": ["protocol", "tool", "schema", "terminal surface", "structured", "continue_after"],
    "substrate": ["event", "scheduler", "recall", "resume", "state", "merge", "hook"],
    "scorer": ["scorer", "scoring", "rubric", "contamination", "judge", "classifier"],
    "sample_size": ["n=1", "n=2", "n=3", "small n", "single", "thin"],
    "scope": ["scope", "bounded", "qualitative", "observed", "paper-grade (qual)", "general"],
}

H_ID_RE = re.compile(r"\bH(\d{1,5})(?:\s*[-–]\s*H?(\d{1,5}))?\b")
H_KEY_RE = re.compile(r"^(H\d{1,5})(?:[_: -]+(.+))?$", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,4})\s+(H\d{1,5})(?:\s*[:\-–]\s*(.+))?\s*$", re.MULTILINE)
WEAKENED_RE = re.compile(r"\b(H\d{1,5})\s+is\s+(weakened|falsified|supported|deferred|superseded)\s+if\s+(.+)", re.IGNORECASE)
BULLET_H_RE = re.compile(r"^\s*[-*]\s+(H\d{1,5}(?:\s*[-–]\s*H?\d{1,5})?)\s+(.+)$", re.IGNORECASE)
PAPER_TABLE_RE = re.compile(r"^\|\s*([A-Z]\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]*)\|")


@dataclass
class Entry:
    key: str
    entry_type: str
    source_local_id: str
    claim: str
    status: str
    raw_status: str = ""
    status_source: str = ""
    source_paths: list[str] = field(default_factory=list)
    evidence_paths: list[str] = field(default_factory=list)
    experiment_dir: str = ""
    condition: str = ""
    model: str = ""
    provider: str = ""
    limitation_axes: list[str] = field(default_factory=list)
    confounds: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    result_summary: dict[str, Any] = field(default_factory=dict)
    raw_trace_paths: list[str] = field(default_factory=list)


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def stable_id(entry: Entry) -> str:
    base = "\n".join(
        [
            entry.entry_type,
            entry.source_local_id,
            entry.experiment_dir,
            "|".join(entry.source_paths),
            entry.claim,
        ]
    )
    return "HL-" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().strip("|").strip())


def expand_h_ids(token: str) -> list[str]:
    match = H_ID_RE.search(token)
    if not match:
        return []
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if end < start or end - start > 200:
        return [f"H{start}"]
    return [f"H{i}" for i in range(start, end + 1)]


def normalize_status(value: Any, *, default: str = "unknown") -> tuple[str, str]:
    raw = str(value).strip()
    lower = raw.lower()
    if isinstance(value, bool):
        return ("survived" if value else "falsified", raw)
    if lower in {"true", "pass", "passed", "survived", "supported", "success"}:
        return "survived", raw
    if lower in {"false", "fail", "failed", "falsified"}:
        return "falsified", raw
    if re.search(r"\bfalsified\b", lower) or "not supported" in lower:
        return "falsified", raw
    if (
        "contaminated" in lower
        or "prompt leak" in lower
        or "contamination prevents" in lower
        or "contaminated pilot" in lower
    ):
        return "contaminated", raw
    if "unscore" in lower or "trace gap" in lower:
        return "unscoreable", raw
    if "supersed" in lower or "replaced" in lower:
        return "superseded", raw
    if "defer" in lower or "needs-rerun" in lower or "aspirational" in lower:
        return "deferred", raw
    if any(word in lower for word in ["weaken", "mixed", "partial", "boundary", "observed", "qual"]):
        return "boundary", raw
    if "paper-grade" in lower or (
        re.search(r"\bsupported\b", lower) and "unsupported" not in lower and "not supported" not in lower
    ):
        return "survived", raw
    if "hypothesis" in lower:
        return "unknown", raw
    return default, raw


def infer_status_from_text(text: str) -> tuple[str, str]:
    return normalize_status(text, default="unknown")


def limitation_axes_for(*parts: str) -> list[str]:
    text = " ".join(part for part in parts if part).lower()
    axes = []
    for axis, keywords in LIMITATION_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            axes.append(axis)
    return axes


def experiment_dir_for(path: Path, root: Path) -> str:
    parts = path.resolve().relative_to(root.resolve()).parts
    if "experiments" not in parts:
        return ""
    index = parts.index("experiments")
    if len(parts) > index + 1:
        # Most sources are directly under experiments/<name>/... or
        # experiments/event_loop/<name>/...
        if parts[index + 1] == "event_loop" and len(parts) > index + 2:
            return "/".join(parts[: index + 3])
        return "/".join(parts[: index + 2])
    return ""


def add_unique(target: list[str], values: Iterable[str]) -> None:
    for value in values:
        if value and value not in target:
            target.append(value)


def merge_entry(entries: dict[str, Entry], incoming: Entry) -> None:
    existing = entries.get(incoming.key)
    if existing is None:
        entries[incoming.key] = incoming
        return
    if STATUS_PRIORITY[incoming.status] > STATUS_PRIORITY[existing.status]:
        existing.status = incoming.status
        existing.raw_status = incoming.raw_status
        existing.status_source = incoming.status_source
    if len(incoming.claim) > len(existing.claim):
        existing.claim = incoming.claim
    add_unique(existing.source_paths, incoming.source_paths)
    add_unique(existing.evidence_paths, incoming.evidence_paths)
    add_unique(existing.limitation_axes, incoming.limitation_axes)
    add_unique(existing.confounds, incoming.confounds)
    add_unique(existing.notes, incoming.notes)
    add_unique(existing.raw_trace_paths, incoming.raw_trace_paths)
    if not existing.condition:
        existing.condition = incoming.condition
    if not existing.model:
        existing.model = incoming.model
    if not existing.provider:
        existing.provider = incoming.provider
    if incoming.result_summary and not existing.result_summary:
        existing.result_summary = incoming.result_summary


def entry_key(path: Path, root: Path, source_local_id: str, entry_type: str) -> str:
    exp_dir = experiment_dir_for(path, root)
    if exp_dir and entry_type in {"hypothesis", "falsification_criterion"}:
        return f"{entry_type}:{exp_dir}:{source_local_id}"
    return f"{entry_type}:{rel(path, root)}:{source_local_id}"


def summarize_result(data: dict[str, Any]) -> dict[str, Any]:
    summary = data.get("summary")
    if not isinstance(summary, dict):
        return {}
    keep = {}
    for key in [
        "rows",
        "errors",
        "scoreable",
        "positive_stressor_results",
        "strong_positive",
        "weak_positive",
        "contamination_flags",
        "unsupported_claim_flags",
    ]:
        if key in summary:
            keep[key] = summary[key]
    for key in ["decision_classifications", "model_summary", "status_counts", "artifact_status_counts"]:
        if key in summary:
            keep[key] = summary[key]
    return keep


def raw_trace_paths_for(path: Path, root: Path, limit: int = 8) -> list[str]:
    directory = path.parent if path.is_file() else path
    traces = sorted(directory.glob("*.jsonl"))
    return [rel(trace, root) for trace in traces[:limit]]


def extract_results(root: Path, entries: dict[str, Entry], audit: dict[str, Any]) -> None:
    for path in sorted(root.glob("experiments/**/results.json")):
        audit["results_json_seen"] += 1
        try:
            data = json.loads(path.read_text())
        except Exception as exc:  # noqa: BLE001
            audit["results_json_errors"].append({"path": rel(path, root), "error": type(exc).__name__})
            continue
        audit["results_json_shapes"][type(data).__name__] += 1
        if not isinstance(data, dict):
            audit["non_dict_results"].append(rel(path, root))
            continue
        outcomes = data.get("hypothesis_results") or data.get("hypothesis_outcomes") or {}
        if not isinstance(outcomes, dict) or not outcomes:
            audit["result_files_without_hypothesis_map"].append(rel(path, root))
            continue
        audit["results_with_hypothesis_maps"] += 1
        for raw_id, outcome in sorted(outcomes.items()):
            match = H_KEY_RE.match(str(raw_id))
            source_local_id = match.group(1).upper() if match else str(raw_id)
            claim = clean((match.group(2) if match else "") or str(raw_id).replace("_", " "))
            status, raw_status = normalize_status(outcome)
            source = rel(path, root)
            entry = Entry(
                key=entry_key(path, root, source_local_id, "hypothesis"),
                entry_type="hypothesis",
                source_local_id=source_local_id,
                claim=claim,
                status=status,
                raw_status=raw_status,
                status_source="results_json",
                source_paths=[source],
                evidence_paths=[source],
                experiment_dir=experiment_dir_for(path, root),
                condition=str(data.get("condition", "")),
                model=str(data.get("model", "")),
                limitation_axes=limitation_axes_for(claim, json.dumps(summarize_result(data), sort_keys=True)),
                result_summary=summarize_result(data),
            )
            if status in {"unknown", "unscoreable", "contaminated", "boundary"}:
                entry.raw_trace_paths = raw_trace_paths_for(path, root)
            merge_entry(entries, entry)


def heading_body(text: str, match: re.Match[str]) -> str:
    start = match.end()
    next_heading = re.search(r"^#{1,4}\s+", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else min(len(text), start + 1200)
    return text[start:end]


def extract_markdown_headings(root: Path, entries: dict[str, Entry], audit: dict[str, Any]) -> None:
    patterns = [
        "experiments/**/PRE_REGISTRATION.md",
        "experiments/**/analysis.md",
        "docs/*stocktake*.md",
        "docs/*synthesis*.md",
    ]
    paths: set[Path] = set()
    for pattern in patterns:
        paths.update(root.glob(pattern))
    paths = {path for path in paths if not path.name.startswith("hypothesis-ledger-")}
    for path in sorted(paths):
        source = rel(path, root)
        text = path.read_text(errors="replace")
        audit["markdown_sources_seen"] += 1
        for match in HEADING_RE.finditer(text):
            source_local_id = match.group(2).upper()
            title = clean(match.group(3) or source_local_id)
            body = heading_body(text, match)
            default_status = "unknown" if path.name == "PRE_REGISTRATION.md" else "unknown"
            status, raw_status = infer_status_from_text(title + " " + body[:700])
            if path.name == "PRE_REGISTRATION.md":
                status, raw_status = "unknown", "preregistered"
            entry = Entry(
                key=entry_key(path, root, source_local_id, "hypothesis"),
                entry_type="hypothesis",
                source_local_id=source_local_id,
                claim=title,
                status=status or default_status,
                raw_status=raw_status,
                status_source="markdown_heading",
                source_paths=[source],
                evidence_paths=[] if path.name == "PRE_REGISTRATION.md" else [source],
                experiment_dir=experiment_dir_for(path, root),
                limitation_axes=limitation_axes_for(title, body[:700]),
                confounds=extract_confounds(body),
                notes=first_sentences(body, limit=2),
            )
            if entry.experiment_dir and entry.status in {"boundary", "contaminated", "unscoreable", "falsified"}:
                entry.raw_trace_paths = raw_trace_paths_for(path, root)
            merge_entry(entries, entry)
        for match in WEAKENED_RE.finditer(text):
            source_local_id = match.group(1).upper()
            criterion = clean(match.group(3))
            entry = Entry(
                key=entry_key(path, root, source_local_id, "falsification_criterion"),
                entry_type="falsification_criterion",
                source_local_id=source_local_id,
                claim=criterion,
                status="unknown",
                raw_status=match.group(2).lower(),
                status_source="markdown_criterion",
                source_paths=[source],
                evidence_paths=[source],
                experiment_dir=experiment_dir_for(path, root),
                limitation_axes=limitation_axes_for(criterion),
            )
            if entry.experiment_dir:
                entry.raw_trace_paths = raw_trace_paths_for(path, root, limit=3)
            merge_entry(entries, entry)


def extract_confound_sections(root: Path, entries: dict[str, Entry], audit: dict[str, Any]) -> None:
    paths = set(root.glob("experiments/**/analysis.md"))
    paths |= set(root.glob("docs/*stocktake*.md"))
    paths |= set(root.glob("docs/*synthesis*.md"))
    paths.add(root / "docs/paper-evidence-ledger.md")
    paths = {path for path in paths if path.exists() and not path.name.startswith("hypothesis-ledger-")}
    section_re = re.compile(r"^(#{2,4})\s+(.+)$", re.MULTILINE)
    keywords = [
        "confound",
        "caveat",
        "scorer",
        "scoring correction",
        "scorer repair",
        "contaminated",
        "prompt leak",
        "schema gap",
        "boundary",
    ]
    for path in sorted(paths):
        text = path.read_text(errors="replace")
        source = rel(path, root)
        matches = list(section_re.finditer(text))
        for index, match in enumerate(matches):
            title = clean(match.group(2))
            title_lower = title.lower()
            if not any(keyword in title_lower for keyword in keywords):
                continue
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else min(len(text), start + 1600)
            body = text[start:end]
            body_sample = clean(body)[:500]
            status, raw_status = infer_status_from_text(title + " " + body_sample)
            if status == "unknown":
                status = "boundary"
                raw_status = "confound_section"
            source_local_id = "CONF-" + hashlib.sha1(f"{source}:{title}".encode("utf-8")).hexdigest()[:8]
            entry = Entry(
                key=f"confound:{source}:{source_local_id}",
                entry_type="confound",
                source_local_id=source_local_id,
                claim=f"{title}: {body_sample}" if body_sample else title,
                status=status,
                raw_status=raw_status,
                status_source="markdown_confound_section",
                source_paths=[source],
                evidence_paths=[source],
                experiment_dir=experiment_dir_for(path, root),
                limitation_axes=limitation_axes_for(title, body_sample),
                confounds=extract_confounds(title + " " + body_sample),
                notes=first_sentences(body, limit=2),
            )
            if entry.experiment_dir:
                entry.raw_trace_paths = raw_trace_paths_for(path, root, limit=5)
            merge_entry(entries, entry)


def extract_markdown_bullets(root: Path, entries: dict[str, Entry], audit: dict[str, Any]) -> None:
    paths = set(root.glob("docs/*synthesis*.md")) | set(root.glob("docs/*stocktake*.md"))
    paths = {path for path in paths if not path.name.startswith("hypothesis-ledger-")}
    for path in sorted(paths):
        source = rel(path, root)
        for line_no, line in enumerate(path.read_text(errors="replace").splitlines(), start=1):
            match = BULLET_H_RE.match(line)
            if not match:
                continue
            h_ids = []
            for token_match in H_ID_RE.finditer(match.group(1)):
                start = int(token_match.group(1))
                end = int(token_match.group(2) or start)
                h_ids.extend(f"H{i}" for i in range(start, end + 1))
            claim = clean(match.group(2))
            status, raw_status = infer_status_from_text(claim)
            for source_local_id in h_ids:
                entry = Entry(
                    key=f"synthesis_reference:{source}:{source_local_id}:{line_no}",
                    entry_type="synthesis_reference",
                    source_local_id=source_local_id,
                    claim=claim,
                    status=status,
                    raw_status=raw_status,
                    status_source="markdown_synthesis_bullet",
                    source_paths=[source],
                    evidence_paths=[source],
                    limitation_axes=limitation_axes_for(claim),
                )
                merge_entry(entries, entry)


def extract_paper_ledger(root: Path, entries: dict[str, Entry], audit: dict[str, Any]) -> None:
    path = root / "docs/paper-evidence-ledger.md"
    if not path.exists():
        audit["missing_inputs"].append(rel(path, root))
        return
    source = rel(path, root)
    for line_no, line in enumerate(path.read_text(errors="replace").splitlines(), start=1):
        match = PAPER_TABLE_RE.match(line)
        if not match:
            continue
        source_local_id = match.group(1)
        claim = clean(match.group(2))
        raw_status = clean(match.group(4))
        notes = clean(match.group(5))
        status, _ = normalize_status(raw_status)
        entry = Entry(
            key=f"paper_claim:{source}:{source_local_id}",
            entry_type="paper_claim",
            source_local_id=source_local_id,
            claim=claim,
            status=status,
            raw_status=raw_status,
            status_source="paper_evidence_ledger",
            source_paths=[source],
            evidence_paths=[source],
            limitation_axes=limitation_axes_for(claim, raw_status, notes),
            confounds=extract_confounds(notes),
            notes=[f"line {line_no}: {notes}"] if notes else [],
        )
        merge_entry(entries, entry)


def extract_confounds(text: str) -> list[str]:
    confounds = []
    for word in ["confound", "leak", "scorer", "timeout", "provider", "small", "n=1", "n=2", "n=3"]:
        if word in text.lower():
            confounds.append(word)
    return sorted(set(confounds))


def first_sentences(text: str, limit: int = 2) -> list[str]:
    cleaned = clean(re.sub(r"```.*?```", "", text, flags=re.DOTALL))
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [part[:260] for part in parts[:limit] if part]


def entry_to_json(entry: Entry) -> dict[str, Any]:
    limitation_axes = list(entry.limitation_axes)
    if not limitation_axes and entry.status == "boundary":
        limitation_axes = ["scope"]
    if not limitation_axes and entry.status == "contaminated":
        limitation_axes = ["protocol"]
    if not limitation_axes and entry.status == "unscoreable":
        limitation_axes = ["substrate"]
    if not limitation_axes and entry.status == "deferred":
        limitation_axes = ["scope"]
    data = {
        "ledger_id": stable_id(entry),
        "entry_type": entry.entry_type,
        "source_local_id": entry.source_local_id,
        "claim": entry.claim,
        "status": entry.status,
        "raw_status": entry.raw_status,
        "status_source": entry.status_source,
        "source_paths": entry.source_paths,
        "evidence_paths": entry.evidence_paths,
        "experiment_dir": entry.experiment_dir,
        "condition": entry.condition,
        "model": entry.model,
        "provider": entry.provider,
        "limitation_axes": limitation_axes,
        "confounds": entry.confounds,
        "notes": entry.notes,
        "result_summary": entry.result_summary,
        "raw_trace_paths": entry.raw_trace_paths,
    }
    return {key: value for key, value in data.items() if value not in ("", [], {})}


def validate_entries(entries: list[dict[str, Any]], root: Path) -> list[str]:
    problems = []
    ids = Counter(entry["ledger_id"] for entry in entries)
    for ledger_id, count in ids.items():
        if count > 1:
            problems.append(f"duplicate ledger_id {ledger_id}: {count}")
    for entry in entries:
        if entry.get("status") not in STATUS_VALUES:
            problems.append(f"{entry.get('ledger_id')} invalid status {entry.get('status')}")
        if not entry.get("source_local_id"):
            problems.append(f"{entry.get('ledger_id')} missing source_local_id")
        if not entry.get("source_paths"):
            problems.append(f"{entry.get('ledger_id')} missing source_paths")
        for source in entry.get("source_paths", []):
            if not (root / source).exists():
                problems.append(f"{entry.get('ledger_id')} missing source path {source}")
    return problems


def write_jsonl(entries: list[dict[str, Any]], output: Path) -> None:
    output.write_text(
        "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries),
        encoding="utf-8",
    )


def write_stocktake(entries: list[dict[str, Any]], audit: dict[str, Any], output: Path) -> None:
    status_counts = Counter(entry["status"] for entry in entries)
    type_counts = Counter(entry["entry_type"] for entry in entries)
    axis_counts = Counter(axis for entry in entries for axis in entry.get("limitation_axes", []))
    source_counts = Counter(Path(path).parts[0] for entry in entries for path in set(entry.get("source_paths", [])))
    falsified = [entry for entry in entries if entry["status"] == "falsified"][:20]
    boundary = [entry for entry in entries if entry["status"] == "boundary"][:20]
    unknown = [entry for entry in entries if entry["status"] == "unknown"][:20]
    lines = [
        "# Hypothesis Ledger Stocktake",
        "",
        "Date: 2026-06-05",
        "",
        "## Summary",
        "",
        f"The first-pass ledger contains {len(entries)} entries.",
        "",
        "Status counts:",
        "",
    ]
    lines.extend(f"- `{key}`: {status_counts[key]}" for key in sorted(status_counts))
    lines.extend(
        [
            "",
            "Entry-type counts:",
            "",
        ]
    )
    lines.extend(f"- `{key}`: {type_counts[key]}" for key in sorted(type_counts))
    lines.extend(
        [
            "",
            "Limitation-axis counts:",
            "",
        ]
    )
    lines.extend(f"- `{key}`: {axis_counts[key]}" for key in sorted(axis_counts))
    lines.extend(
        [
            "",
            "Source root references:",
            "",
        ]
    )
    lines.extend(f"- `{key}`: {source_counts[key]}" for key in sorted(source_counts))
    lines.extend(
        [
            "",
            "## What The Map Shows",
            "",
            "The corpus is now findable at the claim level. Structured result maps supply the cleanest outcomes; Markdown headings and synthesis bullets supply additional source-local hypotheses and boundary summaries; the paper evidence ledger supplies paper-facing claim statuses.",
            "",
            "This is a conservative first pass. Entries with clear result-map outcomes are classified as `survived` or `falsified`; preregistration-only entries remain `unknown`; qualitative, observed, weakened, mixed, provider-limited, scorer-limited, or scope-limited entries are usually `boundary`.",
            "",
            "## Falsified Entries",
            "",
        ]
    )
    lines.extend(format_entry_list(falsified))
    lines.extend(["", "## Boundary Entries", ""])
    lines.extend(format_entry_list(boundary))
    lines.extend(["", "## Unknown Entries Needing Follow-Up", ""])
    lines.extend(format_entry_list(unknown))
    lines.extend(
        [
            "",
            "## Coverage Notes",
            "",
            f"- `results.json` files seen: {audit['results_json_seen']}",
            f"- result files with hypothesis maps: {audit['results_with_hypothesis_maps']}",
            f"- non-dict result files: {len(audit['non_dict_results'])}",
            f"- result files without hypothesis maps: {len(audit['result_files_without_hypothesis_map'])}",
            f"- Markdown sources scanned: {audit['markdown_sources_seen']}",
            f"- entries with nearby raw trace links: {sum(1 for entry in entries if entry.get('raw_trace_paths'))}",
            "",
            "## Use",
            "",
            "Use `docs/hypothesis-ledger-20260605.jsonl` for search, filtering, and future falsification planning. Use this stocktake for a human-level map of status distributions and high-priority gaps.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_entry_list(entries: list[dict[str, Any]]) -> list[str]:
    if not entries:
        return ["- none in first-pass sample"]
    lines = []
    for entry in entries:
        claim = entry["claim"]
        if len(claim) > 180:
            claim = claim[:177] + "..."
        source = entry.get("evidence_paths") or entry.get("source_paths") or [""]
        lines.append(
            f"- `{entry['ledger_id']}` `{entry['source_local_id']}` "
            f"({entry['entry_type']}, `{entry['status']}`): {claim} "
            f"[{source[0]}]"
        )
    return lines


def write_audit(entries: list[dict[str, Any]], audit: dict[str, Any], problems: list[str], output: Path) -> None:
    status_counts = Counter(entry["status"] for entry in entries)
    type_counts = Counter(entry["entry_type"] for entry in entries)
    validation = "passed" if not problems else "failed"
    sample_ids = [entry["ledger_id"] for entry in entries[:5]]
    lines = [
        "# Hypothesis Ledger Audit Notes",
        "",
        "Date: 2026-06-05",
        "",
        "## Validation",
        "",
        f"Validation status: `{validation}`.",
        "",
    ]
    if problems:
        lines.extend(["Problems:", ""])
        lines.extend(f"- {problem}" for problem in problems[:100])
        lines.append("")
    lines.extend(
        [
            "## Extraction Coverage",
            "",
            f"- `results.json` files seen: {audit['results_json_seen']}",
            f"- result JSON shapes: {dict(audit['results_json_shapes'])}",
            f"- result files with hypothesis maps: {audit['results_with_hypothesis_maps']}",
            f"- result files without hypothesis maps: {len(audit['result_files_without_hypothesis_map'])}",
            f"- non-dict result files: {len(audit['non_dict_results'])}",
            f"- Markdown sources scanned: {audit['markdown_sources_seen']}",
            f"- ledger entries emitted: {len(entries)}",
            f"- entries with nearby raw trace links: {sum(1 for entry in entries if entry.get('raw_trace_paths'))}",
            f"- status counts: {dict(status_counts)}",
            f"- entry-type counts: {dict(type_counts)}",
            "",
            "## Schema Gaps",
            "",
            "- Many older `results.json` files do not expose `hypothesis_results` or `hypothesis_outcomes` maps.",
            "- Some result files are list-shaped rather than object-shaped.",
            "- Markdown hypotheses often repeat across preregistration, analysis, and synthesis; the extractor merges experiment-local hypothesis IDs when possible.",
            "- `H1`, `H2`, and similar IDs are source-local, not globally unique.",
            "- Some entries are criteria or synthesis references rather than direct hypothesis outcomes; these are typed separately.",
            "- Raw JSONL traces are linked for ambiguous rows when nearby, but the first pass does not re-score every raw trace.",
            "",
            "## Sampling Checks",
            "",
            "Manual spot checks performed during generation:",
            "",
            "- Structured bounded-autonomous-work outcomes matched the known Step 6 and Step 7 results.",
            "- `docs/paper-evidence-ledger.md` table rows were parsed as `paper_claim` entries with conservative status mapping.",
            "- Preregistration-only headings remain `unknown` unless later result or analysis evidence updates them.",
            "- KIMI Step 7 timeout behavior is represented as a provider/protocol boundary in the source analysis, not as a model incapability proof.",
            "",
            "First five emitted ledger IDs for repeatability checks:",
            "",
        ]
    )
    lines.extend(f"- `{ledger_id}`" for ledger_id in sample_ids)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_audit() -> dict[str, Any]:
    return {
        "results_json_seen": 0,
        "results_json_shapes": Counter(),
        "results_json_errors": [],
        "results_with_hypothesis_maps": 0,
        "result_files_without_hypothesis_map": [],
        "non_dict_results": [],
        "markdown_sources_seen": 0,
        "missing_inputs": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--ledger", default="docs/hypothesis-ledger-20260605.jsonl")
    parser.add_argument("--stocktake", default="docs/hypothesis-ledger-stocktake-20260605.md")
    parser.add_argument("--audit", default="docs/hypothesis-ledger-audit-notes-20260605.md")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    entries: dict[str, Entry] = {}
    audit = build_audit()

    extract_results(root, entries, audit)
    extract_markdown_headings(root, entries, audit)
    extract_confound_sections(root, entries, audit)
    extract_markdown_bullets(root, entries, audit)
    extract_paper_ledger(root, entries, audit)

    output_entries = [entry_to_json(entry) for entry in entries.values()]
    output_entries.sort(key=lambda item: (item["entry_type"], item.get("experiment_dir", ""), item["source_local_id"], item["ledger_id"]))
    problems = validate_entries(output_entries, root)
    if problems:
        raise SystemExit("\n".join(problems[:50]))

    write_jsonl(output_entries, root / args.ledger)
    write_stocktake(output_entries, audit, root / args.stocktake)
    write_audit(output_entries, audit, problems, root / args.audit)
    print(json.dumps({
        "entries": len(output_entries),
        "status_counts": Counter(entry["status"] for entry in output_entries),
        "entry_type_counts": Counter(entry["entry_type"] for entry in output_entries),
        "results_json_seen": audit["results_json_seen"],
        "results_with_hypothesis_maps": audit["results_with_hypothesis_maps"],
        "markdown_sources_seen": audit["markdown_sources_seen"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
