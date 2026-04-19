"""Unit tests for taste_open._apply_updates.

Does NOT make API calls — tests the harness logic only.

Exercises the default-stable-via-key-presence protocol: non-protocol keys
in raw_output are updates; unlisted keys carry forward; overlap between
updates and deletions raises.
"""

import pytest

from hamutay.taste_open import _apply_updates


class TestApplyUpdatesKeyPresence:
    def test_presence_triggers_update(self):
        raw = {"response": "hi", "mood": "curious"}
        state = _apply_updates(None, raw, cycle=1)
        assert state["cycle"] == 1
        assert state["mood"] == "curious"
        assert "response" not in state

    def test_absent_key_carries_forward(self):
        prior = {"cycle": 1, "mood": "curious", "name": "Ada"}
        raw = {"response": "hi", "mood": "tired"}
        state = _apply_updates(prior, raw, cycle=2)
        assert state["mood"] == "tired"
        assert state["name"] == "Ada"

    def test_deleted_removes_key(self):
        prior = {"cycle": 1, "mood": "curious", "name": "Ada"}
        raw = {"response": "bye", "deleted_regions": ["name"]}
        state = _apply_updates(prior, raw, cycle=2)
        assert "name" not in state
        assert state["mood"] == "curious"

    def test_overlap_between_update_and_delete_raises(self):
        raw = {
            "response": "x",
            "mood": "curious",
            "deleted_regions": ["mood"],
        }
        with pytest.raises(ValueError, match="overlaps"):
            _apply_updates(None, raw, cycle=1)

    def test_legacy_updated_regions_does_not_leak_into_state(self):
        raw = {
            "response": "hi",
            "updated_regions": ["mood"],
            "mood": "curious",
        }
        state = _apply_updates(None, raw, cycle=1)
        assert "updated_regions" not in state
        assert state["mood"] == "curious"
