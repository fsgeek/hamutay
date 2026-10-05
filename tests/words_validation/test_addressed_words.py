"""Addressed reads: identity, provenance, and fully declared information loss."""

import hashlib
import json

import pytest


def assert_refused(result):
    assert isinstance(result, dict)
    assert result.get("error") or (
        result.get("status") in {"error", "invalid", "unreachable"}
        and result.get("reason")
    )
    assert "words" not in result, "An invalid address must not yield a guessed record"


def omitted_count(value):
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    assert isinstance(value, dict), "Truncation needs a numeric omitted-character count"
    candidates = [
        number
        for key, number in value.items()
        if "omit" in key.lower() and isinstance(number, int) and not isinstance(number, bool)
    ]
    assert len(candidates) == 1, f"Missing/unambiguous omitted count: {value!r}"
    return candidates[0]


@pytest.mark.parametrize("address", [{"cycle": 17}, {"record_id": "synthetic-record-17"}, {"line": 2}], ids=["cycle", "record_id", "line"])
def test_each_single_address_returns_the_exact_record(words_tools, record, write_log, claim_notice, address):
    target = record()
    path, _ = write_log(record(91), target, record(18))
    result = words_tools[0](address, log_path=str(path))

    assert result["status"] == "ok"
    assert result["claim_notice"] == claim_notice
    assert result["words"]["incoming"] == target["user_message"]
    assert result["words"]["reply"] == target["response_text"]
    assert result["words"]["tool_calls"] == []
    provenance = result["provenance"]
    for name in ("cycle", "record_id", "timestamp", "model"):
        assert provenance[name] == target[name]
    assert provenance["line"] == 2
    assert provenance["log_path"] == str(path)


@pytest.mark.parametrize("address", [{}, {"cycle": 17, "record_id": "synthetic-record-17"}, {"cycle": 17, "line": 1}, {"record_id": "synthetic-record-17", "line": 1}, {"cycle": 17, "record_id": "synthetic-record-17", "line": 1}], ids=["none", "cycle-and-id", "cycle-and-line", "id-and-line", "all-three"])
def test_zero_or_multiple_addresses_are_refused(words_tools, record, write_log, address):
    path, _ = write_log(record())
    assert_refused(words_tools[0](address, log_path=str(path)))


def test_cycle_zero_is_a_valid_address(words_tools, record, write_log):
    path, _ = write_log(record(0), record(1))
    result = words_tools[0]({"cycle": 0}, log_path=str(path))
    assert result["status"] == "ok"
    assert result["provenance"]["cycle"] == 0


def test_duplicate_cycle_lists_every_physical_line_and_never_picks_one(words_tools, record, write_log):
    first = record(457, record_id="first-457", response_text="first candidate")
    second = record(457, record_id="second-457", timestamp="2026-10-05T14:00:00Z", response_text="second candidate")
    path, _ = write_log(first, b"not JSON\n", record(456), second)
    result = words_tools[0]({"cycle": 457}, log_path=str(path))

    assert result["status"] == "ambiguous"
    assert "words" not in result
    assert "provenance" not in result, "Ambiguity must not identify one chosen record"
    assert sorted(result["candidates"], key=lambda value: value["line"]) == [
        {"record_id": first["record_id"], "timestamp": first["timestamp"], "line": 1},
        {"record_id": second["record_id"], "timestamp": second["timestamp"], "line": 4},
    ]
    explanation = json.dumps({key: value for key, value in result.items() if key != "candidates"})
    assert "record_id" in explanation and "line" in explanation, "Ask for an unambiguous address"


@pytest.mark.parametrize("address", [{"record_id": "second-457"}, {"line": 3}], ids=["record_id", "line"])
def test_duplicate_cycle_can_be_disambiguated_by_id_or_line(words_tools, record, write_log, address):
    path, _ = write_log(record(457, record_id="first-457"), record(99), record(457, record_id="second-457", response_text="the requested one"))
    result = words_tools[0](address, log_path=str(path))
    assert result["status"] == "ok"
    assert result["provenance"]["line"] == 3
    assert result["provenance"]["record_id"] == "second-457"
    assert result["words"]["reply"] == "the requested one"


@pytest.mark.parametrize("address", [{"cycle": 999}, {"record_id": "does-not-exist"}, {"line": 5}, {"line": 2}, {"line": 3}], ids=["missing-cycle", "missing-id", "beyond-eof", "blank-line", "malformed-line"])
def test_unreachable_addresses_report_a_reason_and_no_words(words_tools, record, write_log, address):
    path, _ = write_log(record(), b" \t\n", b'{"cycle": unfinished\n', record(18))
    result = words_tools[0](address, log_path=str(path))
    assert result["status"] == "unreachable"
    assert isinstance(result["reason"], str) and result["reason"].strip()
    assert "words" not in result


@pytest.mark.parametrize("address", [{"cycle": 17}, {"record_id": "synthetic-record-17"}], ids=["cycle-scan", "id-scan"])
def test_scan_skips_and_counts_unparseable_lines(words_tools, record, write_log, labeled_values, address):
    path, _ = write_log(b"broken before\n", record(), b'{"broken":\n', record(18))
    result = words_tools[0](address, log_path=str(path))
    assert result["status"] == "ok"
    assert result["provenance"]["line"] == 2
    counters = [value for key, value in labeled_values(result) if any(label in key for label in ("skip", "unparseable", "malformed", "parse_error", "invalid_line")) and isinstance(value, int) and not isinstance(value, bool)]
    assert 2 in counters, "Scan must count malformed lines even after the matching record"


@pytest.mark.parametrize("ending", [b"\n", b"\r\n", b""], ids=["lf", "crlf", "unterminated-final-line"])
def test_provenance_hashes_the_original_utf8_line_bytes(words_tools, record, write_log, ending):
    target = record(user_message="Piñata: λ, 雨, café.")
    raw = ("  " + json.dumps(target, ensure_ascii=False, indent=None, separators=(", ", ": ")) + " \t").encode("utf-8") + ending
    path, _ = write_log(b"unparseable prefix\n", raw)
    result = words_tools[0]({"line": 2}, log_path=str(path))
    assert result["status"] == "ok"
    provenance = result["provenance"]
    assert provenance["line"] == 2
    assert provenance["record_sha256"] == hashlib.sha256(raw).hexdigest(), (
        "Hash the stored bytes, including whitespace and any line terminator; "
        f"declared provenance: {provenance!r}"
    )
    for key, declaration in provenance.items():
        if "hash" in key.lower() and any(word in key.lower() for word in ("convention", "scope", "basis")):
            description = str(declaration).lower()
            assert not any(contradiction in description for contradiction in ("excluding newline", "newline excluded", "stripped newline", "without newline")), (
                "Declared hash convention must agree with hashing the stored raw line"
            )


def test_line_address_reads_old_records_without_record_id(words_tools, record, write_log):
    old = record(2)
    del old["record_id"]
    del old["model"]
    path, _ = write_log(record(9), old)
    result = words_tools[0]({"line": 2}, log_path=str(path))
    assert result["status"] == "ok"
    assert result["provenance"]["line"] == 2
    assert result["provenance"]["cycle"] == 2
    assert result["provenance"].get("record_id") is None
    assert result["words"]["reply"] == old["response_text"]


@pytest.mark.parametrize("empty_reply", ["", None], ids=["empty", "null"])
def test_interim_fallback_preserves_every_fragment_and_names_its_source(words_tools, record, write_log, labeled_values, empty_reply):
    fragments = ["First provisional sentence.", "Second provisional sentence.", "Last provisional sentence."]
    path, _ = write_log(record(response_text=empty_reply, interim_text=fragments))
    result = words_tools[0]({"cycle": 17}, log_path=str(path))
    assert result["status"] == "ok"
    reply = result["words"]["reply"]
    if isinstance(reply, list):
        assert reply == fragments
    else:
        assert isinstance(reply, str)
        cursor = 0
        for fragment in fragments:
            position = reply.find(fragment, cursor)
            assert position >= cursor, "All interim fragments must survive in order"
            cursor = position + len(fragment)
    assert any(value == "interim_text" and any(label in key for label in ("source", "field", "used")) for key, value in labeled_values(result)), "Fallback must say that interim_text supplied the reply"


def test_nonempty_response_wins_over_interim_and_names_its_source(words_tools, record, write_log, labeled_values):
    path, _ = write_log(record(response_text="Final reply", interim_text=["superseded provisional reply"]))
    result = words_tools[0]({"cycle": 17}, log_path=str(path))
    assert result["words"]["reply"] == "Final reply"
    assert any(value == "response_text" and any(label in key for label in ("source", "field", "used")) for key, value in labeled_values(result))


def test_tool_calls_expose_only_names_parameters_and_summaries(words_tools, record, write_log):
    activity = [
        {"tool": "synthetic_probe", "parameters": {"query": "public query", "limit": 2}, "result_summary": "Two synthetic results.", "result": {"private_blob": "NEVER_EXPOSE_FULL_RESULT"}},
        {"tool": "synthetic_clock", "parameters": {}, "result_summary": "Synthetic timestamp.", "full_result": "NEVER_EXPOSE_FULL_RESULT"},
    ]
    path, _ = write_log(record(tool_activity_full=activity))
    result = words_tools[0]({"cycle": 17, "fields": ["tool_calls"]}, log_path=str(path))
    calls = result["words"]["tool_calls"]
    assert isinstance(calls, list) and len(calls) == 2
    for original, summary in zip(activity, calls, strict=True):
        name_keys = set(summary) & {"tool", "name", "tool_name"}
        assert len(name_keys) == 1
        assert summary[next(iter(name_keys))] == original["tool"]
        assert summary["parameters"] == original["parameters"]
        assert summary["result_summary"] == original["result_summary"]
        assert set(summary) == name_keys | {"parameters", "result_summary"}
    assert "NEVER_EXPOSE_FULL_RESULT" not in json.dumps(result)


@pytest.mark.parametrize("fields", [["incoming"], ["reply"], ["tool_calls"], ["incoming", "reply"]])
def test_field_selection_returns_only_requested_word_fields(words_tools, record, write_log, fields):
    path, _ = write_log(record())
    result = words_tools[0]({"cycle": 17, "fields": fields}, log_path=str(path))
    assert result["status"] == "ok"
    # Source labels may accompany the selected fields, but no unrequested payload.
    assert set(result["words"]) & {"incoming", "reply", "tool_calls"} == set(fields)


def test_small_budget_reports_exact_character_loss_in_every_cut_field(words_tools, record, write_log):
    originals = {"incoming": "ñ" * 1100 + "incoming-end", "reply": "雨" * 1300 + "reply-end"}
    path, _ = write_log(record(user_message=originals["incoming"], response_text=originals["reply"]))
    result = words_tools[0]({"cycle": 17, "fields": ["incoming", "reply"], "max_chars": 80}, log_path=str(path))
    assert result["status"] == "ok"
    assert isinstance(result["truncated"], dict)
    returned_length = 0
    for field, original in originals.items():
        returned = result["words"][field]
        assert isinstance(returned, str)
        returned_length += len(returned)
        retained = 0
        for old_char, new_char in zip(original, returned):
            if old_char != new_char:
                break
            retained += 1
        assert retained < len(original)
        assert field in result["truncated"], f"Silent loss in {field}"
        assert omitted_count(result["truncated"][field]) == len(original) - retained
    assert returned_length <= 80, "max_chars is a total content budget, counted as characters"


def test_large_budget_returns_all_text_with_no_reported_loss(words_tools, record, write_log):
    target = record(user_message="Complete incoming café", response_text="Complete reply 雨")
    path, _ = write_log(target)
    result = words_tools[0]({"cycle": 17, "fields": ["incoming", "reply"], "max_chars": 20000}, log_path=str(path))
    assert result["words"]["incoming"] == target["user_message"]
    assert result["words"]["reply"] == target["response_text"]
    for field in ("incoming", "reply"):
        if field in result["truncated"]:
            assert omitted_count(result["truncated"][field]) == 0
