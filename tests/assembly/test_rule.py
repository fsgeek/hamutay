import pytest

from hamutay.assembly.rule import apply_caps, consent_v0

M = ["a", "b", "c", "d"]


def _r(active, round_n=1):
    return consent_v0(active, members=M, round_n=round_n, max_rounds=3, quorum=2)


def test_one_dissent_among_silence_extends_not_unresolved():
    assert _r({"a": "dissent", "b": None, "c": None, "d": None})[0] == "extended"


def test_dissent_at_last_round_is_unresolved():
    assert _r({"a": "dissent", "b": "assent", "c": "assent", "d": None}, round_n=3)[0] == "unresolved"


def test_defer_is_an_objection():
    assert _r({"a": "defer", "b": "assent", "c": "assent", "d": "assent"})[0] == "extended"


def test_quorum_edge_two_of_four_assents():
    assert _r({"a": "assent", "b": "assent", "c": None, "d": None})[0] == "assented"
    assert _r({"a": "assent", "b": None, "c": None, "d": None})[0] == "unresolved"


def test_all_abstain_is_unresolved_and_abstain_plus_assent_assents():
    assert _r({"a": "abstain", "b": "abstain", "c": None, "d": None})[0] == "unresolved"
    assert _r({"a": "abstain", "b": "assent", "c": None, "d": None})[0] == "assented"


def test_trace_names_the_branch():
    out, trace = _r({"a": "dissent", "b": None, "c": None, "d": None})
    assert "objection" in trace and "a" in trace


@pytest.mark.parametrize("cap", ["not_offered", "running_at_cutoff", "unknown_at_cutoff"])
def test_caps_convert_assent_only(cap):
    kw = {"not_offered": [], "running_at_cutoff": [], "unknown_at_cutoff": []}
    kw[cap] = ["d"]
    assert apply_caps("assented", round_n=1, max_rounds=3, **kw) == ("extended", f"cap:{cap}:d")
    assert apply_caps("assented", round_n=3, max_rounds=3, **kw)[0] == "unresolved"
    assert apply_caps("extended", round_n=1, max_rounds=3, **kw) == ("extended", "")
    assert apply_caps("unresolved", round_n=1, max_rounds=3, **kw) == ("unresolved", "")


def test_no_caps_pass_through():
    assert apply_caps("assented", round_n=1, max_rounds=3, not_offered=[], running_at_cutoff=[],
                      unknown_at_cutoff=[]) == ("assented", "")
