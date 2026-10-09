"""Spec test 1: strict stored schema and writer normalization."""
from uuid import uuid5, NAMESPACE_URL

import pytest

from hamutay.assembly.ledger import LedgerMalformed
from hamutay.plaza import records

from .helpers import BAD, FORBIDDEN, STAMP, api, message


def test_legacy_record_remains_valid():
    records.validate_plaza([message()], [1])


@pytest.mark.parametrize("value", ["a", "x" * 120, "anthropic/claude-haiku-4-5", "qwen3.8-27b-q4km", "ñ🦙"])
def test_valid_carriers_normalize_and_validate(value):
    assert api(records, "normalize_carrier")(value) == value
    records.validate_plaza([message(carrier=value)], [1])


@pytest.mark.parametrize("value", BAD)
def test_invalid_stored_carrier_is_rejected(value):
    with pytest.raises(LedgerMalformed):
        records.validate_plaza([message(carrier=value)], [1])


@pytest.mark.parametrize("value", BAD[:-2])
def test_invalid_raw_carrier_is_rejected(value):
    normalize = api(records, "normalize_carrier")
    with pytest.raises(ValueError):
        normalize(value)


@pytest.mark.parametrize("char", FORBIDDEN)
@pytest.mark.parametrize("position", ["leading", "middle", "trailing"])
def test_forbidden_categories_are_rejected_before_strip(char, position):
    raw = {"leading": char + "alias", "middle": "al" + char + "ias", "trailing": "alias" + char}[position]
    normalize = api(records, "normalize_carrier")
    with pytest.raises(ValueError):
        normalize(raw)
    with pytest.raises(LedgerMalformed):
        records.validate_plaza([message(carrier=raw)], [1])


@pytest.mark.parametrize("raw,want", [(" alias ", "alias"), ("\u2003alias\u00a0", "alias"), (" " + "x" * 120 + " ", "x" * 120)])
def test_noncontrol_whitespace_is_stripped_before_length_check(raw, want):
    assert api(records, "normalize_carrier")(raw) == want
    with pytest.raises(LedgerMalformed):
        records.validate_plaza([message(carrier=raw)], [1])


@pytest.mark.parametrize("carrier", [None, "alias"])
def test_build_message_optional_field(carrier):
    row = records.build_message(actor="tony", via="cli", to="plaza", text="hello", sent_at=STAMP,
                                idempotency_key=str(uuid5(NAMESPACE_URL, "builder")), delivery=None,
                                wake=None, carrier=carrier)
    if carrier is None:
        assert "carrier" not in row
    else:
        assert row["carrier"] == "alias"
    records.validate_plaza([{**row, "seq": 1, "created_at": STAMP}], [1])


@pytest.mark.parametrize("carrier", [False, True])
def test_unrelated_message_field_is_still_rejected(carrier):
    row = message(carrier="alias") if carrier else message()
    row["unrelated"] = "extra"
    with pytest.raises(LedgerMalformed):
        records.validate_plaza([row], [1])


def test_delivery_does_not_gain_carrier(house):
    _, cfg, _ = house
    row = message(cfg=cfg, to="door:elder")
    d = {"record_type": "delivery", "seq": 2, "created_at": STAMP,
         "message_id": row["message_id"], "door": "elder", "event_id": row["delivery"]["event_id"],
         "state": "landed", "landed_at": STAMP, "detail": None}
    records.validate_plaza([row, d], [1, 2])
    d["carrier"] = "alias"
    with pytest.raises(LedgerMalformed):
        records.validate_plaza([row, d], [1, 2])
