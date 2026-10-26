import pytest

from hamutay.board.filters import FilterRefused, clear_filter, current_filter, match, normalize_filter, set_filter
from hamutay.events import EventStore

from .conftest import T0

OPENING = {"kind": "review", "tags": ["paper", "memory"], "owner": "custodian",
           "title": "Read the Draft", "what": "Memory as Rewrite needs readers."}


def test_normalization_nfkc_casefold_trim_dedupe():
    f = normalize_filter({"kinds": [" REVIEW ", "review"], "tags_any": ["Ｐａｐｅｒ"],
                          "owners_any": ["Door:Elder"], "keywords_any": ["  Draft "]})
    assert f == {"kinds": ["review"], "tags_any": ["paper"], "owners_any": ["door:elder"], "keywords_any": ["draft"]}
    assert normalize_filter({}) == {"kinds": [], "tags_any": [], "owners_any": [], "keywords_any": []}
    assert normalize_filter({"kinds": None})["kinds"] == []


@pytest.mark.parametrize("raw", [
    {"keywords_any": [""]}, {"keywords_any": ["  "]}, {"keywords_any": ["ab"]}, {"keywords_any": ["x" * 65]},
    {"tags_any": ["no spaces"]}, {"kinds": ["party"]}, {"owners_any": ["someone"]},
    {"kinds": "review"}, {"colour": ["red"]}, {"keywords_any": [f"kw{i:02d}" for i in range(17)]},
    {"keywords_any": [3]},
])
def test_normalization_refuses(raw):
    with pytest.raises(FilterRefused):
        normalize_filter(raw)


def test_match_and_across_or_within_and_clause():
    f = normalize_filter({"kinds": ["review", "design"], "keywords_any": ["draft", "nothing"]})
    assert match(f, OPENING) == {"kinds": ["review"], "keywords_any": ["draft"]}
    assert match(normalize_filter({"kinds": ["review"], "owners_any": ["tony"]}), OPENING) is None
    assert match(normalize_filter({"tags_any": ["memory", "x"]}), OPENING) == {"tags_any": ["memory"]}
    assert match(normalize_filter({"keywords_any": ["REWRITE"]}), OPENING) == {"keywords_any": ["rewrite"]}
    assert match(normalize_filter({}), OPENING) is None                  # all-empty matches nothing
    assert match(None, OPENING) is None


def test_generations_increase_and_clear_is_a_generation(tmp_path):
    st = EventStore(tmp_path / "e.jsonl")
    assert current_filter(st.read_records()) == (0, None)
    r1 = set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    assert r1["generation"] == 1 and r1["filter"]["kinds"] == ["review"]
    assert clear_filter(st, "qwen", T0)["generation"] == 2
    assert current_filter(st.read_records()) == (2, None)
    r3 = set_filter(st, "qwen", {}, T0)
    assert r3["generation"] == 3 and "matches nothing" in r3["note"]
