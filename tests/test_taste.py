"""Tests for the self-curating tensor (taste.py).

Unit tests for schema, feedback, and update mechanics.
Does NOT make API calls — tests the harness logic only.
"""

from hamutay.taste import (
    SELF_CURATING_SCHEMA,
    _apply_updates,
    _generate_feedback,
)


class TestSchema:
    """Verify schema structure."""

    def test_schema_has_response_and_updated_regions(self):
        assert "response" in SELF_CURATING_SCHEMA["properties"]
        assert "updated_regions" in SELF_CURATING_SCHEMA["properties"]
        assert SELF_CURATING_SCHEMA["required"] == ["response", "updated_regions"]

    def test_strands_have_depends_on(self):
        strand_props = SELF_CURATING_SCHEMA["properties"]["strands"]["items"]["properties"]
        assert "depends_on" in strand_props
        assert strand_props["depends_on"]["type"] == "array"

    def test_losses_have_shed_from(self):
        loss_props = SELF_CURATING_SCHEMA["properties"]["declared_losses"]["items"]["properties"]
        assert "shed_from" in loss_props
        assert loss_props["shed_from"]["type"] == "string"


class TestApplyUpdates:
    """Verify default-stable update mechanics."""

    def test_first_cycle_initializes(self):
        raw = {
            "response": "Hello",
            "updated_regions": ["strands", "open_questions", "instructions_for_next"],
            "strands": [{"title": "Start", "content": "First strand", "key_claims": []}],
            "open_questions": ["What is this?"],
            "instructions_for_next": "Continue the conversation.",
        }
        tensor = _apply_updates(None, raw, cycle=1)
        assert tensor["cycle"] == 1
        assert len(tensor["strands"]) == 1
        assert tensor["strands"][0]["title"] == "Start"
        assert "response" not in tensor
        assert "updated_regions" not in tensor

    def test_default_stable_carries_forward(self):
        prior = {
            "cycle": 1,
            "strands": [{"title": "A", "content": "Content A", "key_claims": []}],
            "open_questions": ["Q1"],
            "instructions_for_next": "Do X",
        }
        # Only update strands, not open_questions or instructions_for_next
        raw = {
            "response": "Updated",
            "updated_regions": ["strands"],
            "strands": [
                {"title": "A+", "content": "Integrated content", "key_claims": []},
            ],
        }
        tensor = _apply_updates(prior, raw, cycle=2)
        assert tensor["strands"][0]["title"] == "A+"
        assert tensor["open_questions"] == ["Q1"]  # carried forward
        assert tensor["instructions_for_next"] == "Do X"  # carried forward

    def test_declared_losses_cleared_when_not_updated(self):
        """Bug fix: declared_losses should reset to empty each cycle
        unless explicitly updated. Otherwise default-stable carries
        them forward and the model re-declares old losses."""
        prior = {
            "cycle": 1,
            "strands": [{"title": "A", "content": "X", "key_claims": []}],
            "declared_losses": [
                {"what_was_lost": "Old loss", "why": "Test", "category": "authorial_choice"}
            ],
        }
        raw = {
            "response": "No changes to losses",
            "updated_regions": [],  # not updating declared_losses
        }
        tensor = _apply_updates(prior, raw, cycle=2)
        assert tensor["declared_losses"] == []  # cleared, not carried forward

    def test_declared_losses_preserved_when_updated(self):
        prior = {
            "cycle": 1,
            "declared_losses": [],
        }
        raw = {
            "response": "Shedding content",
            "updated_regions": ["declared_losses"],
            "declared_losses": [
                {
                    "what_was_lost": "Strand B",
                    "shed_from": "B",
                    "why": "No longer relevant",
                    "category": "authorial_choice",
                }
            ],
        }
        tensor = _apply_updates(prior, raw, cycle=2)
        assert len(tensor["declared_losses"]) == 1
        assert tensor["declared_losses"][0]["shed_from"] == "B"


class TestFeedback:
    """Verify harness feedback generation."""

    def test_no_feedback_on_none(self):
        assert _generate_feedback(None, cycle=1) == []

    def test_open_questions_critical_threshold(self):
        """Bug fix: >15 must fire before >10."""
        tensor = {"open_questions": list(range(16))}
        feedback = _generate_feedback(tensor, cycle=5)
        assert any("critically high" in f for f in feedback)

    def test_open_questions_excessive_threshold(self):
        tensor = {"open_questions": list(range(12))}
        feedback = _generate_feedback(tensor, cycle=5)
        assert any("excessive" in f for f in feedback)
        assert not any("critically high" in f for f in feedback)

    def test_goldilocks_feedback(self):
        tensor = {"open_questions": list(range(6))}
        feedback = _generate_feedback(tensor, cycle=5)
        assert any("good balance" in f for f in feedback)

    def test_sustained_zero_curation_warning(self):
        tensor = {
            "strands": [{"title": "A", "content": "X " * 3000, "key_claims": []}] * 3,
            "open_questions": [],
        }
        # No losses in last 5 cycles, tensor > 1500 tokens
        loss_history = [{"cycle": 1, "what_was_lost": "old", "why": "x", "category": "y"}]
        # At cycle 8, last loss was at cycle 1 (>5 cycles ago)
        feedback = _generate_feedback(tensor, cycle=8, loss_history=loss_history)
        assert any("No declared losses in the last 5 cycles" in f for f in feedback)

    def test_no_zero_curation_warning_when_recent_losses(self):
        tensor = {
            "strands": [{"title": "A", "content": "X" * 200, "key_claims": []}] * 3,
            "open_questions": [],
        }
        loss_history = [{"cycle": 7, "what_was_lost": "recent", "why": "x", "category": "y"}]
        feedback = _generate_feedback(tensor, cycle=8, loss_history=loss_history)
        assert not any("No declared losses" in f for f in feedback)
