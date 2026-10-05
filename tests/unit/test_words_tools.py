"""Tests for recall_words / search_words — reading what was said, from the
door's own session log (plan 2026-10-05-recall-words).

Fixtures are small synthetic JSONL mirroring the real cycle-record shape
(cycle, record_id, timestamp, model, user_message, response_text,
interim_text as list[str] | None, tool_activity_full as a list of activity
entries). No resident text.
"""

import hashlib
import json

from hamutay.tools.words import CLAIM_NOTICE, tool_recall_words, tool_search_words

_NOTICE = (
    "This is what was said at this cycle, as recorded in your log. It is a "
    "claim made then, not verified truth: check it against other records "
    "before relying on it."
)


def _rec(cycle, rid, *, incoming="", reply="", interim=None, tools=None, **extra):
    r = {
        "timestamp": f"2026-01-01T00:{cycle:02d}:00+00:00",
        "cycle": cycle,
        "record_id": rid,
        "model": "test-model",
        "interim_text": interim,
        "user_message": incoming,
        "response_text": reply,
        "state": {"big": "state is not words"},
        "tool_activity_full": tools,
    }
    r.update(extra)
    return r


def _activity(tool, params, summary):
    return {
        "cycle": 1, "timestamp": "t", "tool": tool, "capability": "read_only",
        "parameters": params, "reason": None, "exit_code": None,
        "result_summary": summary, "result_hash": "h", "duration_ms": 1,
        "result": {"content": "FULL RESULT BODY " * 50},
    }


def _write(tmp_path, records, *, raw_lines=()):
    path = tmp_path / "session.jsonl"
    lines = [json.dumps(r) for r in records]
    for pos, raw in raw_lines:
        lines.insert(pos, raw)
    path.write_text("".join(line + "\n" for line in lines))
    return path, lines


def test_claim_notice_is_exact():
    assert CLAIM_NOTICE == _NOTICE


# --- recall_words ---------------------------------------------------------


def test_recall_by_cycle_ok(tmp_path):
    tools = [_activity("read", {"path": "a.txt"}, "read a.txt (3 lines)")]
    path, lines = _write(tmp_path, [
        _rec(1, "r1", incoming="first knock", reply="first answer"),
        _rec(2, "r2", incoming="second knock", reply="second answer", tools=tools),
    ])
    out = tool_recall_words({"cycle": 2}, log_path=str(path))
    assert out["status"] == "ok"
    assert out["claim_notice"] == _NOTICE
    prov = out["provenance"]
    assert prov["cycle"] == 2 and prov["record_id"] == "r2"
    assert prov["timestamp"] == "2026-01-01T00:02:00+00:00"
    assert prov["model"] == "test-model"
    assert prov["log_path"] == str(path)
    assert prov["line"] == 2
    w = out["words"]
    assert w["incoming"] == "second knock"
    assert w["reply"] == "second answer"
    assert w["reply_source"] == "response_text"
    assert w["tool_calls"] == [
        {"tool": "read", "parameters": {"path": "a.txt"},
         "result_summary": "read a.txt (3 lines)"}
    ]
    # Never full results.
    assert "FULL RESULT BODY" not in json.dumps(out)
    assert "state is not words" not in json.dumps(out)
    assert out["truncated"] == {}


def test_recall_by_record_id_ok(tmp_path):
    path, _ = _write(tmp_path, [
        _rec(1, "r1", incoming="a", reply="b"),
        _rec(2, "r2", incoming="c", reply="d"),
    ])
    out = tool_recall_words({"record_id": "r1"}, log_path=str(path))
    assert out["status"] == "ok"
    assert out["provenance"]["cycle"] == 1 and out["provenance"]["line"] == 1
    assert out["words"]["incoming"] == "a"


def test_recall_ambiguous_duplicate_cycle_never_picks(tmp_path):
    path, _ = _write(tmp_path, [
        _rec(456, "r0", incoming="x", reply="y"),
        _rec(457, "rA", incoming="one", reply="uno"),
        _rec(457, "rB", incoming="two", reply="dos"),
    ])
    out = tool_recall_words({"cycle": 457}, log_path=str(path))
    assert out["status"] == "ambiguous"
    assert "words" not in out
    assert out["candidates"] == [
        {"record_id": "rA", "timestamp": _rec(457, "")["timestamp"], "line": 2},
        {"record_id": "rB", "timestamp": _rec(457, "")["timestamp"], "line": 3},
    ]
    assert "record_id" in out["reason"]
    # The record_id resolves it.
    again = tool_recall_words({"record_id": "rB"}, log_path=str(path))
    assert again["status"] == "ok" and again["words"]["incoming"] == "two"


def test_recall_unreachable(tmp_path):
    path, _ = _write(tmp_path, [_rec(1, "r1", incoming="a", reply="b")])
    out = tool_recall_words({"cycle": 99}, log_path=str(path))
    assert out["status"] == "unreachable" and out["reason"]
    assert "words" not in out
    out = tool_recall_words({"record_id": "nope"}, log_path=str(path))
    assert out["status"] == "unreachable"
    out = tool_recall_words({"cycle": 1}, log_path=str(tmp_path / "missing.jsonl"))
    assert out["status"] == "unreachable"


def test_recall_needs_exactly_one_address(tmp_path):
    path, _ = _write(tmp_path, [_rec(1, "r1")])
    assert "error" in tool_recall_words({}, log_path=str(path))
    assert "error" in tool_recall_words({"cycle": 1, "record_id": "r1"}, log_path=str(path))
    assert "error" in tool_recall_words({"cycle": "1"}, log_path=str(path))
    assert "error" in tool_recall_words({"cycle": 1, "fields": ["state"]}, log_path=str(path))


def test_unparseable_line_skipped_and_counted(tmp_path):
    path, _ = _write(
        tmp_path,
        [_rec(1, "r1", incoming="a", reply="b"), _rec(2, "r2", incoming="c", reply="d")],
        raw_lines=[(1, '{"cycle": 2, "torn')],
    )
    out = tool_recall_words({"cycle": 2}, log_path=str(path))
    assert out["status"] == "ok"
    assert out["unparseable_lines"] == 1
    assert out["provenance"]["line"] == 3


def test_reply_falls_back_to_interim_text_and_says_so(tmp_path):
    path, _ = _write(tmp_path, [
        _rec(1, "r1", incoming="a", reply="", interim=["thinking aloud", "more"]),
    ])
    out = tool_recall_words({"cycle": 1}, log_path=str(path))
    assert out["words"]["reply_source"] == "interim_text"
    assert "thinking aloud" in out["words"]["reply"] and "more" in out["words"]["reply"]


def test_fields_subset(tmp_path):
    path, _ = _write(tmp_path, [_rec(1, "r1", incoming="a", reply="b")])
    out = tool_recall_words({"cycle": 1, "fields": ["reply"]}, log_path=str(path))
    assert set(k for k in out["words"] if not k.endswith("_source")) == {"reply"}


def test_truncation_is_declared(tmp_path):
    path, _ = _write(tmp_path, [_rec(1, "r1", incoming="i" * 1000, reply="r" * 50)])
    out = tool_recall_words(
        {"cycle": 1, "fields": ["incoming", "reply"], "max_chars": 200},
        log_path=str(path),
    )
    assert out["status"] == "ok"
    assert len(out["words"]["incoming"]) == 100
    assert out["words"]["reply"] == "r" * 50
    assert out["truncated"] == {"incoming": 900}


def test_record_sha256_is_the_line_hash(tmp_path):
    path, lines = _write(tmp_path, [_rec(1, "r1", incoming="a"), _rec(2, "r2", incoming="b")])
    out = tool_recall_words({"cycle": 2}, log_path=str(path))
    assert out["provenance"]["record_sha256"] == hashlib.sha256((lines[1] + "\n").encode()).hexdigest()


# --- search_words ---------------------------------------------------------


def _population(tmp_path):
    recs = []
    for c in range(1, 21):
        reply = f"cycle {c} says the dark window" if c % 2 == 0 else f"cycle {c} quiet"
        if c in (5, 15):
            reply = f"cycle {c}: the window was dark"  # every word, not the phrase
        recs.append(_rec(c, f"r{c}", incoming=f"knock {c}", reply=reply))
    return _write(tmp_path, recs)


def test_search_counts_and_notice(tmp_path):
    path, _ = _population(tmp_path)
    out = tool_search_words({"pattern": "DARK WINDOW"}, log_path=str(path))
    assert out["claim_notice"] == _NOTICE
    assert out["records_scanned"] == 20
    assert out["records_matched"] == 10
    assert out["matches_total"] == 10


def test_search_samples_spread_across_range(tmp_path):
    path, _ = _population(tmp_path)
    out = tool_search_words({"pattern": "dark window", "max_samples": 3}, log_path=str(path))
    cycles = [s["cycle"] for s in out["samples"]]
    assert len(cycles) == 3
    assert cycles[0] == 2 and cycles[-1] == 20  # not just the first N
    s = out["samples"][0]
    assert s["record_id"] == "r2" and s["field"] == "reply"
    assert "dark window" in s["snippet"]


def test_search_near_misses(tmp_path):
    path, _ = _population(tmp_path)
    out = tool_search_words({"pattern": "dark window"}, log_path=str(path))
    assert [n["cycle"] for n in out["near_misses"]] == [5, 15]
    assert out["near_misses_total"] == 2
    single = tool_search_words({"pattern": "dark"}, log_path=str(path))
    assert single["near_misses"] == []


def test_search_cycle_bounds_and_fields(tmp_path):
    path, _ = _population(tmp_path)
    out = tool_search_words(
        {"pattern": "dark window", "from_cycle": 5, "to_cycle": 10}, log_path=str(path)
    )
    assert out["records_scanned"] == 6
    assert out["records_matched"] == 3  # 6, 8, 10
    inc = tool_search_words({"pattern": "knock 7", "fields": ["incoming"]}, log_path=str(path))
    assert inc["records_matched"] == 1 and inc["samples"][0]["field"] == "incoming"


def test_search_snippet_is_bounded(tmp_path):
    path, _ = _write(tmp_path, [_rec(1, "r1", reply="a" * 1000 + "needle" + "b" * 1000)])
    out = tool_search_words({"pattern": "needle"}, log_path=str(path))
    snip = out["samples"][0]["snippet"]
    assert "needle" in snip and len(snip) <= 150 + len("needle") + 150


def test_search_counts_unparseable_and_requires_pattern(tmp_path):
    path, _ = _write(tmp_path, [_rec(1, "r1", reply="x")], raw_lines=[(0, "not json")])
    out = tool_search_words({"pattern": "x"}, log_path=str(path))
    assert out["unparseable_lines"] == 1 and out["records_scanned"] == 1
    assert "error" in tool_search_words({"pattern": ""}, log_path=str(path))


# --- addressing by line (records without a record_id) ----------------------


def test_recall_by_line_ok_for_records_without_record_id(tmp_path):
    a = _rec(7, None, incoming="old one", reply="a")
    b = _rec(7, None, incoming="old two", reply="b")
    del a["record_id"], b["record_id"]
    path, lines = _write(tmp_path, [a, b])
    amb = tool_recall_words({"cycle": 7}, log_path=str(path))
    assert amb["status"] == "ambiguous"
    assert [c["line"] for c in amb["candidates"]] == [1, 2]
    assert "line" in amb["reason"] and "record_id" in amb["reason"]
    out = tool_recall_words({"line": 2}, log_path=str(path))
    assert out["status"] == "ok"
    assert out["words"]["incoming"] == "old two"
    assert out["provenance"]["line"] == 2 and out["provenance"]["record_id"] is None
    assert out["provenance"]["record_sha256"] == hashlib.sha256((lines[1] + "\n").encode()).hexdigest()


def test_recall_by_line_unreachable(tmp_path):
    path, _ = _write(tmp_path, [_rec(1, "r1", incoming="a")], raw_lines=[(1, "{torn")])
    out = tool_recall_words({"line": 2}, log_path=str(path))
    assert out["status"] == "unreachable" and "unparseable" in out["reason"]
    out = tool_recall_words({"line": 9}, log_path=str(path))
    assert out["status"] == "unreachable" and "line 9" in out["reason"]
    out = tool_recall_words({"line": 0}, log_path=str(path))
    assert "error" in out


def test_recall_needs_exactly_one_of_three_addresses(tmp_path):
    path, _ = _write(tmp_path, [_rec(1, "r1")])
    assert "error" in tool_recall_words({"cycle": 1, "line": 1}, log_path=str(path))
    assert "error" in tool_recall_words({"record_id": "r1", "line": 1}, log_path=str(path))
    assert "error" in tool_recall_words({"line": "1"}, log_path=str(path))
