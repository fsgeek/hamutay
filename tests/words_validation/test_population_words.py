"""Population searches: counts, representative witnesses, and counterexamples."""

import pytest


def test_search_counts_occurrences_and_distinct_records_case_insensitively(words_tools, record, write_log, claim_notice):
    path, _ = write_log(
        record(1, user_message="LANTERN then lantern", response_text="One more Lantern"),
        record(2, user_message="lantern", response_text="unrelated"),
        record(3, user_message="unrelated", response_text="unrelated"),
    )
    result = words_tools[1]({"pattern": "lAnTeRn", "max_samples": 20}, log_path=str(path))
    assert result["claim_notice"] == claim_notice
    assert result["records_scanned"] == 3
    assert result["records_matched"] == 2
    assert result["matches_total"] == 4
    assert len(result["samples"]) == 2
    assert {(sample["record_id"], sample["field"]) for sample in result["samples"]} == {
        ("synthetic-record-1", "incoming"),
        ("synthetic-record-2", "incoming"),
    }
    for sample in result["samples"]:
        assert sample["cycle"] in {1, 2}
        assert "lantern" in sample["snippet"].lower()


def test_search_skips_and_counts_unparseable_lines(words_tools, record, write_log, labeled_values):
    path, _ = write_log(b"broken first\n", record(1, user_message="needle"), b'{"cycle":\n', record(2, response_text="needle"), b"broken last\n")
    result = words_tools[1]({"pattern": "needle"}, log_path=str(path))
    assert result["records_scanned"] == 2
    assert result["records_matched"] == 2
    assert result["matches_total"] == 2
    counters = [value for key, value in labeled_values(result) if any(label in key for label in ("skip", "unparseable", "malformed", "parse_error", "invalid_line")) and isinstance(value, int) and not isinstance(value, bool)]
    assert 3 in counters, "Population scans must report skipped malformed lines"


def test_samples_span_the_matched_population_instead_of_taking_its_prefix(words_tools, record, write_log):
    # Wide gaps prevent accidentally treating cycles as dense record offsets.
    cycles = [7 + 13 * index for index in range(20)]
    records = [record(cycle, user_message=f"population witness {index}", response_text="no match") for index, cycle in enumerate(cycles)]
    path, _ = write_log(*records)
    result = words_tools[1]({"pattern": "population witness", "max_samples": 4}, log_path=str(path))
    assert result["records_matched"] == result["matches_total"] == 20
    assert len(result["samples"]) == 4
    order = {value["record_id"]: index for index, value in enumerate(records)}
    positions = [order[sample["record_id"]] for sample in result["samples"]]
    assert len(set(positions)) == 4
    assert min(positions) <= 4 and max(positions) >= 15, positions


def test_default_sample_limit_is_five_and_still_spans_the_population(words_tools, record, write_log):
    path, _ = write_log(*(record(cycle, user_message="matched token", response_text="no match") for cycle in range(1, 22)))
    result = words_tools[1]({"pattern": "matched token"}, log_path=str(path))
    assert result["matches_total"] == 21
    assert len(result["samples"]) == 5
    cycles = [sample["cycle"] for sample in result["samples"]]
    assert min(cycles) <= 5 and max(cycles) >= 17


def test_multiword_near_misses_show_all_words_without_the_exact_phrase(words_tools, record, write_log):
    path, _ = write_log(
        record(1, user_message="silver lantern", response_text="unrelated"),
        record(2, user_message="A SILVER bracket conceals the LANTERN.", response_text="unrelated"),
        record(3, user_message="lantern before silver", response_text="unrelated"),
        record(4, user_message="silver alone", response_text="unrelated"),
        record(5, user_message="lantern alone", response_text="unrelated"),
    )
    result = words_tools[1]({"pattern": "silver lantern", "max_samples": 5}, log_path=str(path))
    assert result["records_scanned"] == 5
    assert result["records_matched"] == result["matches_total"] == 1
    assert {sample["record_id"] for sample in result["samples"]} == {"synthetic-record-1"}
    assert {miss["record_id"] for miss in result["near_misses"]} == {"synthetic-record-2", "synthetic-record-3"}
    for miss in result["near_misses"]:
        assert miss["cycle"] in {2, 3}
        snippet = miss["snippet"].lower()
        assert "silver" in snippet and "lantern" in snippet
        assert "silver lantern" not in snippet


def test_near_misses_are_capped_per_record_and_single_words_have_none(words_tools, record, write_log):
    path, _ = write_log(*(record(cycle, user_message="silver distant lantern", response_text="lantern then silver") for cycle in range(1, 10)))
    multi = words_tools[1]({"pattern": "silver lantern", "max_samples": 3}, log_path=str(path))
    assert multi["matches_total"] == multi["records_matched"] == 0
    assert multi["samples"] == []
    assert len(multi["near_misses"]) == 3
    assert len({miss["record_id"] for miss in multi["near_misses"]}) == 3
    single = words_tools[1]({"pattern": "silver", "max_samples": 3}, log_path=str(path))
    assert single["near_misses"] == []


@pytest.mark.parametrize("bounds, expected", [({"from_cycle": 3}, {3, 4, 5}), ({"to_cycle": 3}, {1, 2, 3}), ({"from_cycle": 2, "to_cycle": 4}, {2, 3, 4}), ({"from_cycle": 3, "to_cycle": 3}, {3})], ids=["lower", "upper", "both", "single-cycle"])
def test_cycle_bounds_are_inclusive_and_apply_to_matches_and_near_misses(words_tools, record, write_log, bounds, expected):
    records = []
    for cycle in [5, 1, 4, 2, 3]:
        records.append(record(cycle, record_id=f"exact-{cycle}", user_message="silver lantern", response_text="unrelated"))
        records.append(record(cycle, record_id=f"near-{cycle}", user_message="silver distant lantern", response_text="unrelated"))
    path, _ = write_log(*records)
    result = words_tools[1]({"pattern": "silver lantern", "max_samples": 20, **bounds}, log_path=str(path))
    assert result["records_matched"] == result["matches_total"] == len(expected)
    assert {sample["record_id"] for sample in result["samples"]} == {f"exact-{cycle}" for cycle in expected}
    assert {miss["record_id"] for miss in result["near_misses"]} == {f"near-{cycle}" for cycle in expected}


@pytest.mark.parametrize("fields, expected_ids", [(["incoming"], {"synthetic-record-1"}), (["reply"], {"synthetic-record-2"})], ids=["incoming-only", "reply-only"])
def test_search_honors_selected_fields(words_tools, record, write_log, fields, expected_ids):
    path, _ = write_log(record(1, user_message="needle", response_text="unrelated"), record(2, user_message="unrelated", response_text="needle"))
    result = words_tools[1]({"pattern": "needle", "fields": fields}, log_path=str(path))
    assert result["records_matched"] == result["matches_total"] == 1
    assert {sample["record_id"] for sample in result["samples"]} == expected_ids
    assert all(sample["field"] == fields[0] for sample in result["samples"])


def test_default_search_does_not_match_tool_activity(words_tools, record, write_log):
    path, _ = write_log(record(user_message="unrelated", response_text="unrelated", tool_activity_full=[{"tool": "synthetic_probe", "parameters": {"query": "needle"}, "result_summary": "needle in tool activity"}]))
    result = words_tools[1]({"pattern": "needle"}, log_path=str(path))
    assert result["records_scanned"] == 1
    assert result["records_matched"] == result["matches_total"] == 0
    assert result["samples"] == []


def test_search_snippet_is_bounded_context_around_the_hit(words_tools, record, write_log):
    before, phrase, after = "L" * 450, "silver lantern", "R" * 450
    path, _ = write_log(record(user_message=before + phrase + after, response_text="unrelated"))
    result = words_tools[1]({"pattern": phrase}, log_path=str(path))
    assert result["matches_total"] == 1
    assert len(result["samples"]) == 1
    sample = result["samples"][0]
    assert sample["cycle"] == 17 and sample["record_id"] == "synthetic-record-17"
    assert sample["field"] == "incoming"
    snippet = sample["snippet"]
    assert "L" * 150 + phrase + "R" * 150 in snippet
    assert len(snippet) <= 300 + len(phrase) + 12


def test_empty_and_no_match_searches_keep_the_notice_and_zero_counts(words_tools, record, write_log, claim_notice):
    for lines, count in [((), 0), ((record(),), 1)]:
        path, _ = write_log(*lines)
        result = words_tools[1]({"pattern": "absent phrase"}, log_path=str(path))
        assert result["claim_notice"] == claim_notice
        assert result["records_scanned"] == count
        assert result["records_matched"] == result["matches_total"] == 0
        assert result["samples"] == result["near_misses"] == []
