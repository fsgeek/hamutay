"""Words tools: reading what was said, from the door's own session log.

`recall`/`search_memory` read the STATE object. The words of each cycle (the
incoming message, the reply, the tool activity) live only in the session log.
These two read-only tools return them:

- tool_recall_words: an addressed read (one cycle or one record_id).
- tool_search_words: a population search (a case-insensitive substring).

What comes back is a claim made then, not recovered truth: every result
carries CLAIM_NOTICE. Nothing is guessed: a duplicated cycle comes back
ambiguous with its candidates, a missing one unreachable. Anything cut is
declared, per field. The log is read fresh on every call; no reading is
cached for another question.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

CLAIM_NOTICE = (
    "This is what was said at this cycle, as recorded in your log. It is a "
    "claim made then, not verified truth: check it against other records "
    "before relying on it."
)

WORD_FIELDS = ("incoming", "reply", "tool_calls")
_DEFAULT_MAX_CHARS = 20000
_DEFAULT_MAX_SAMPLES = 5
_SNIPPET_RADIUS = 150


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _scan(log_path: str, counter: dict) -> Iterator[tuple[int, bytes, dict]]:
    """Yield (1-based line, raw line bytes without newline, record).

    Unparseable lines (and lines that are not JSON objects) are skipped and
    counted in counter["unparseable_lines"].
    """
    with open(log_path, "rb") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.rstrip(b"\n")
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                counter["unparseable_lines"] += 1
                continue
            if not isinstance(record, dict):
                counter["unparseable_lines"] += 1
                continue
            yield lineno, raw, record


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def _reply(record: dict) -> tuple[str, str | None]:
    """The reply and the field it came from: response_text, else interim_text."""
    text = _text(record.get("response_text"))
    if text:
        return text, "response_text"
    interim = record.get("interim_text")
    if isinstance(interim, list):
        text = "\n\n".join(_text(part) for part in interim if part)
    else:
        text = _text(interim)
    if text:
        return text, "interim_text"
    return "", None


def _tool_calls(record: dict) -> list[dict] | None:
    """Compact tool activity: name, parameters, result_summary. Never results.

    None when the record carries no tool activity field at all (or null);
    framework events in the log (entries without a tool name) are left out.
    """
    activity = record.get("tool_activity_full")
    if not isinstance(activity, list):
        return None
    return [
        {
            "tool": entry.get("tool"),
            "parameters": entry.get("parameters"),
            "result_summary": entry.get("result_summary"),
        }
        for entry in activity
        if isinstance(entry, dict) and "tool" in entry
    ]


def _check_fields(fields, default: tuple[str, ...]) -> tuple[list[str] | None, str | None]:
    if fields is None:
        return list(default), None
    if (
        not isinstance(fields, list)
        or not fields
        or not all(isinstance(f, str) and f in WORD_FIELDS for f in fields)
    ):
        return None, f"fields must be a non-empty subset of {list(WORD_FIELDS)}"
    return list(dict.fromkeys(fields)), None


def tool_recall_words(tool_input: dict, *, log_path: str) -> dict:
    """Return the words of one cycle record, addressed by cycle or record_id."""
    cycle = tool_input.get("cycle")
    record_id = tool_input.get("record_id")
    if (cycle is None) == (record_id is None):
        return {"error": "recall_words: give exactly one of cycle or record_id"}
    if cycle is not None and not _is_int(cycle):
        return {"error": "recall_words: cycle must be an integer"}
    if record_id is not None and not isinstance(record_id, str):
        return {"error": "recall_words: record_id must be a string"}
    fields, err = _check_fields(tool_input.get("fields"), WORD_FIELDS)
    if err:
        return {"error": f"recall_words: {err}"}
    max_chars = tool_input.get("max_chars", _DEFAULT_MAX_CHARS)
    if not _is_int(max_chars) or max_chars <= 0:
        return {"error": "recall_words: max_chars must be a positive integer"}

    address = {"cycle": cycle} if cycle is not None else {"record_id": record_id}
    if not Path(log_path).is_file():
        return {
            "status": "unreachable",
            "reason": f"the session log is not readable at {log_path}",
            "address": address,
        }

    counter = {"unparseable_lines": 0}
    hits: list[tuple[int, bytes, dict]] = []
    for lineno, raw, record in _scan(log_path, counter):
        if cycle is not None:
            if _is_int(record.get("cycle")) and record["cycle"] == cycle:
                hits.append((lineno, raw, record))
        elif record.get("record_id") == record_id:
            hits.append((lineno, raw, record))

    if not hits:
        return {
            "status": "unreachable",
            "reason": (
                f"no record in this log has {next(iter(address))} "
                f"{next(iter(address.values()))!r}"
            ),
            "address": address,
            "unparseable_lines": counter["unparseable_lines"],
        }
    if len(hits) > 1:
        return {
            "status": "ambiguous",
            "reason": (
                f"{len(hits)} records share this address; none was chosen. "
                "Call again with one candidate's record_id."
            ),
            "address": address,
            "candidates": [
                {"record_id": r.get("record_id"), "timestamp": r.get("timestamp"), "line": n}
                for n, _, r in hits
            ],
            "unparseable_lines": counter["unparseable_lines"],
        }

    lineno, raw, record = hits[0]
    provenance = {
        "cycle": record.get("cycle"),
        "record_id": record.get("record_id"),
        "timestamp": record.get("timestamp"),
    }
    if "model" in record:
        provenance["model"] = record["model"]
    provenance.update(
        log_path=log_path,
        line=lineno,
        record_sha256=hashlib.sha256(raw).hexdigest(),
        record_sha256_of="the line's bytes as stored, without its trailing newline",
    )

    share = max_chars // len(fields)
    words: dict = {}
    truncated: dict = {}
    for field in fields:
        if field == "incoming":
            text = _text(record.get("user_message"))
            words["incoming"] = text[:share]
            if len(text) > share:
                truncated["incoming"] = len(text) - share
        elif field == "reply":
            text, source = _reply(record)
            words["reply"] = text[:share]
            words["reply_source"] = source
            if len(text) > share:
                truncated["reply"] = len(text) - share
        else:
            calls = _tool_calls(record)
            if calls is None:
                words["tool_calls"] = None
                words["tool_calls_source"] = None
                continue
            words["tool_calls_source"] = "tool_activity_full"
            total = len(json.dumps(calls, default=str))
            kept: list[dict] = []
            used = 2  # the list's brackets
            for call in calls:
                size = len(json.dumps(call, default=str)) + 2
                if used + size > share:
                    break
                kept.append(call)
                used += size
            words["tool_calls"] = kept
            if len(kept) < len(calls):
                truncated["tool_calls"] = total - len(json.dumps(kept, default=str))
                truncated["tool_calls_entries_omitted"] = len(calls) - len(kept)

    return {
        "status": "ok",
        "claim_notice": CLAIM_NOTICE,
        "provenance": provenance,
        "words": words,
        "truncated": truncated,
        "unparseable_lines": counter["unparseable_lines"],
    }


def _field_texts(record: dict, fields: list[str]) -> list[tuple[str, str]]:
    out = []
    for field in fields:
        if field == "incoming":
            out.append(("incoming", _text(record.get("user_message"))))
        elif field == "reply":
            out.append(("reply", _reply(record)[0]))
        else:
            calls = _tool_calls(record)
            out.append(("tool_calls", json.dumps(calls, default=str) if calls else ""))
    return out


def _snippet(text: str, start: int, length: int) -> str:
    lo = max(0, start - _SNIPPET_RADIUS)
    hi = min(len(text), start + length + _SNIPPET_RADIUS)
    return text[lo:hi]


def _spread(items: list, k: int) -> list:
    """Up to k items spread evenly across the list, first and last included."""
    if len(items) <= k:
        return list(items)
    if k == 1:
        return [items[0]]
    idx = sorted({round(i * (len(items) - 1) / (k - 1)) for i in range(k)})
    return [items[i] for i in idx]


def tool_search_words(tool_input: dict, *, log_path: str) -> dict:
    """Count and sample where a substring was said, across this log."""
    pattern = tool_input.get("pattern")
    if not isinstance(pattern, str) or not pattern.strip():
        return {"error": "search_words: pattern must be a non-empty string"}
    fields, err = _check_fields(tool_input.get("fields"), ("incoming", "reply"))
    if err:
        return {"error": f"search_words: {err}"}
    max_samples = tool_input.get("max_samples", _DEFAULT_MAX_SAMPLES)
    if not _is_int(max_samples) or max_samples <= 0:
        return {"error": "search_words: max_samples must be a positive integer"}
    from_cycle = tool_input.get("from_cycle")
    to_cycle = tool_input.get("to_cycle")
    for name, bound in (("from_cycle", from_cycle), ("to_cycle", to_cycle)):
        if bound is not None and not _is_int(bound):
            return {"error": f"search_words: {name} must be an integer"}
    if not Path(log_path).is_file():
        return {
            "status": "unreachable",
            "reason": f"the session log is not readable at {log_path}",
        }

    needle = pattern.lower()
    words = needle.split()
    counter = {"unparseable_lines": 0}
    scanned = 0
    matches_total = 0
    matched: list[dict] = []
    near: list[dict] = []
    for _, _, record in _scan(log_path, counter):
        if from_cycle is not None or to_cycle is not None:
            c = record.get("cycle")
            if not _is_int(c):
                continue
            if from_cycle is not None and c < from_cycle:
                continue
            if to_cycle is not None and c > to_cycle:
                continue
        scanned += 1
        texts = _field_texts(record, fields)
        first = None
        count = 0
        for field, text in texts:
            low = text.lower()
            n = low.count(needle)
            if n and first is None:
                pos = low.find(needle)
                first = {
                    "cycle": record.get("cycle"),
                    "record_id": record.get("record_id"),
                    "field": field,
                    "snippet": _snippet(text, pos, len(pattern)),
                }
            count += n
        if count:
            matches_total += count
            matched.append(first)
        elif len(words) >= 2:
            combined = "\n".join(t.lower() for _, t in texts)
            if all(w in combined for w in words):
                field, text = next(
                    (f, t) for f, t in texts if words[0] in t.lower()
                )
                pos = text.lower().find(words[0])
                near.append({
                    "cycle": record.get("cycle"),
                    "record_id": record.get("record_id"),
                    "field": field,
                    "snippet": _snippet(text, pos, len(words[0])),
                })

    return {
        "status": "ok",
        "claim_notice": CLAIM_NOTICE,
        "pattern": pattern,
        "fields": fields,
        "log_path": log_path,
        "records_scanned": scanned,
        "records_matched": len(matched),
        "matches_total": matches_total,
        "samples": _spread(matched, max_samples),
        "near_misses": _spread(near, max_samples),
        "near_misses_total": len(near),
        "unparseable_lines": counter["unparseable_lines"],
    }
