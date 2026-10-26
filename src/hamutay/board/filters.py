"""A door's board filter: structured, normalized, deterministic (contract §5).

The filter lives in the door's own event store as `board_filter` records with a
generation that increases by one per set or clear; the latest generation is the
filter in force. `board_pass` records end a subscription. The resident writes
them only through the tools; the coverage they govern is computed by the
framework from the store, never edited by the resident.
"""
from __future__ import annotations

from datetime import datetime

from hamutay.assembly.ledger import iso

from .ids import STORE_LOCK_WINDOW_S, canonical_label, norm
from .records import KINDS, TAG_RE

FILTER_FIELDS = ("kinds", "tags_any", "owners_any", "keywords_any")
FIELD_MAX = 16
KEYWORD_MIN, KEYWORD_MAX = 3, 64


class FilterRefused(ValueError):
    pass


def normalize_filter(raw: dict) -> dict:
    """The filter as stored: all four fields present, each a list ([] = unconstrained)."""
    if not isinstance(raw, dict):
        raise FilterRefused("a filter is an object with kinds, tags_any, owners_any, keywords_any")
    unknown = sorted(set(raw) - set(FILTER_FIELDS))
    if unknown:
        raise FilterRefused(f"unknown filter field(s) {unknown}; fields are {', '.join(FILTER_FIELDS)}")
    out: dict[str, list[str]] = {}
    for f in FILTER_FIELDS:
        v = raw.get(f)
        if v is None:
            out[f] = []
            continue
        if not isinstance(v, list):
            raise FilterRefused(f"{f} must be a list or null")
        if len(v) > FIELD_MAX:
            raise FilterRefused(f"{f} has {len(v)} elements; at most {FIELD_MAX}")
        vals: list[str] = []
        for x in v:
            if not isinstance(x, str):
                raise FilterRefused(f"{f}: element {x!r} is not a string")
            n = norm(x)
            if not n:
                raise FilterRefused(f"{f}: a blank element is refused, not ignored")
            if f == "kinds" and n not in KINDS:
                raise FilterRefused(f"kinds: {x!r} is not one of {', '.join(KINDS)}")
            if f == "tags_any" and not TAG_RE.match(n):
                raise FilterRefused(f"tags_any: {x!r} normalizes to {n!r}, which is not [a-z0-9-]{{1,32}}")
            if f == "keywords_any" and not (KEYWORD_MIN <= len(n) <= KEYWORD_MAX):
                raise FilterRefused(f"keywords_any: {x!r} must be {KEYWORD_MIN}..{KEYWORD_MAX} characters "
                                    "after normalization")
            if f == "owners_any":
                try:
                    n = canonical_label(n)
                except ValueError as e:
                    raise FilterRefused(f"owners_any: {e}")
            if n not in vals:
                vals.append(n)
        out[f] = vals
    return out


def matches_nothing(f: dict | None) -> bool:
    return f is None or not any(f.get(k) for k in FILTER_FIELDS)


def match(f: dict | None, opening: dict) -> dict | None:
    """The clause that matched (each constraining field -> the elements that hit), or None.

    AND across fields, OR within a field; an empty field does not constrain; a
    filter with every field empty matches nothing. Keywords are case-insensitive
    substrings of the normalized title or what.
    """
    if matches_nothing(f):
        return None
    clause: dict[str, list[str]] = {}
    if f["kinds"]:
        hit = [k for k in f["kinds"] if k == opening["kind"]]
        if not hit:
            return None
        clause["kinds"] = hit
    if f["tags_any"]:
        hit = [t for t in f["tags_any"] if t in opening["tags"]]
        if not hit:
            return None
        clause["tags_any"] = hit
    if f["owners_any"]:
        hit = [o for o in f["owners_any"] if o == opening["owner"]]
        if not hit:
            return None
        clause["owners_any"] = hit
    if f["keywords_any"]:
        hay = norm(opening["title"]) + "\n" + norm(opening["what"])
        hit = [k for k in f["keywords_any"] if k in hay]
        if not hit:
            return None
        clause["keywords_any"] = hit
    return clause


def current_filter(records: list[dict]) -> tuple[int, dict | None]:
    """(generation, filter) in force: the latest board_filter record; (0, None) if none was ever set."""
    gen, f = 0, None
    for r in records:
        if r.get("record_type") == "board_filter" and isinstance(r.get("generation"), int) \
                and r["generation"] > gen:
            gen, f = r["generation"], r.get("filter")
    if f is not None and not isinstance(f, dict):
        f = None
    return gen, f


def passed_ids(records: list[dict]) -> set[str]:
    return {str(r.get("opportunity_id")) for r in records if r.get("record_type") == "board_pass"}


def _write_filter(store, door: str, f: dict | None, now: datetime) -> dict:
    def derive(records):
        gen, _ = current_filter(records)
        return [{"record_type": "board_filter", "door": door, "generation": gen + 1, "filter": f,
                 "recorded_at": iso(now)}]
    written = store.append_derived(derive, timeout_s=STORE_LOCK_WINDOW_S)
    return written[0]


def set_filter(store, door: str, raw: dict, now: datetime) -> dict:
    f = normalize_filter(raw)
    rec = _write_filter(store, door, f, now)
    out = {"generation": rec["generation"], "filter": f}
    if matches_nothing(f):
        out["note"] = "every field is empty: this filter matches nothing (list all seven kinds to match everything)"
    return out


def clear_filter(store, door: str, now: datetime) -> dict:
    rec = _write_filter(store, door, None, now)
    return {"generation": rec["generation"], "filter": None,
            "note": "no filter: the board will not wake you, and updates to entries you were shown stop"}


def pass_entry(store, door: str, opportunity_id: str, now: datetime) -> dict:
    oid = str(opportunity_id)

    def derive(records):
        if oid in passed_ids(records):
            return []
        return [{"record_type": "board_pass", "door": door, "opportunity_id": oid, "recorded_at": iso(now)}]
    written = store.append_derived(derive, timeout_s=STORE_LOCK_WINDOW_S)
    return {"passed": True, "opportunity_id": oid, "already_passed": not written}
