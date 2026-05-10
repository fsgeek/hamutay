"""Unit tests for taste_open harness logic.

Does NOT make API calls — uses fake backends where transport is needed.

Covers:
- _apply_updates default-stable-via-key-presence protocol
- _truncate_largest_tool_results context-budget recovery helper
- OpenTasteSession.exchange cycle-counter rollback on failure
"""

import json

import pytest

from hamutay.taste_open import (
    ExchangeResult,
    OpenTasteSession,
    _apply_updates,
    _estimate_tool_result_tokens,
    _truncate_largest_tool_results,
)


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


class TestTruncateLargestToolResults:
    """The recovery helper for prompt-too-long errors. Replaces the
    biggest tool_result content blocks with declared-loss stubs so the
    instance reading them next cycle knows perception was elided rather
    than empty."""

    def _make_conversation(self, sizes: list[int]) -> list[dict]:
        """Build a conversation with one tool_result block per `size`."""
        blocks = [
            {
                "type": "tool_result",
                "tool_use_id": f"tu_{i}",
                "content": "x" * size,
            }
            for i, size in enumerate(sizes)
        ]
        return [{"role": "user", "content": blocks}]

    def test_targets_largest_first(self):
        conv = self._make_conversation([100, 50_000, 200, 5_000])
        _truncate_largest_tool_results(conv, target_drop_tokens=10_000)
        blocks = conv[0]["content"]
        # The 50K block should have been truncated; the small ones spared.
        assert "truncated" in blocks[1]["content"]
        assert blocks[0]["content"] == "x" * 100
        assert blocks[2]["content"] == "x" * 200

    def test_stub_declares_original_size(self):
        conv = self._make_conversation([100_000])
        _truncate_largest_tool_results(conv, target_drop_tokens=10_000)
        stub = json.loads(conv[0]["content"][0]["content"])
        assert stub["truncated"] is True
        assert stub["original_size_chars"] == 100_000
        assert "context budget" in stub["reason"]

    def test_returns_estimated_tokens_dropped(self):
        conv = self._make_conversation([400_000])
        dropped = _truncate_largest_tool_results(conv, target_drop_tokens=50_000)
        # 400K chars → ~100K tokens at 4 chars/token. Stub overhead trims
        # a small amount; assert "approximately the right magnitude."
        assert dropped > 50_000
        assert dropped < 110_000

    def test_no_op_when_no_tool_results(self):
        conv = [{"role": "user", "content": "a string, not a block list"}]
        dropped = _truncate_largest_tool_results(conv, target_drop_tokens=1_000)
        assert dropped == 0

    def test_stops_when_target_met(self):
        conv = self._make_conversation([50_000, 50_000, 50_000])
        _truncate_largest_tool_results(conv, target_drop_tokens=8_000)
        blocks = conv[0]["content"]
        truncated_count = sum(
            1 for b in blocks if "truncated" in str(b["content"])
        )
        # 8K-token target ≈ 32K chars. One 50K block more than satisfies it.
        assert truncated_count == 1


class TestEstimateToolResultTokens:
    def test_string_content(self):
        results = [{"content": "x" * 4_000}]
        # 4 chars per token estimate.
        assert _estimate_tool_result_tokens(results) == 1_000

    def test_dict_content_uses_json_size(self):
        results = [{"content": {"a": "x" * 100}}]
        # JSON-serialized form is what the API actually sees.
        approx = _estimate_tool_result_tokens(results)
        assert approx > 0
        assert approx < 100  # well under 100 tokens for 100 chars + braces


class _RaisingBackend:
    """Backend that raises on every call. Used to verify cycle rollback."""

    def __init__(self, exc: Exception):
        self._exc = exc
        self.calls = 0

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict] | None = None,
        tool_executor=None,
    ) -> ExchangeResult:
        del model, system, messages, experiment_label, extra_tools, tool_executor
        self.calls += 1
        raise self._exc


class _CannedBackend:
    """Backend that returns a fixed ExchangeResult. Used for happy-path
    cycle counting tests."""

    def __init__(self, raw_output: dict):
        self._raw_output = raw_output
        self.calls = 0

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict] | None = None,
        tool_executor=None,
    ) -> ExchangeResult:
        del model, system, messages, experiment_label, extra_tools, tool_executor
        self.calls += 1
        return ExchangeResult(
            raw_output=self._raw_output,
            stop_reason="tool_use",
            input_tokens=10,
            output_tokens=20,
        )


class TestExchangeCycleRollback:
    """A failed API call must not leave self._cycle ahead of state["cycle"].
    Without rollback, the next successful exchange would skip a number and
    the JSONL/Apacheta record stream would carry a phantom cycle gap.
    """

    def test_cycle_does_not_advance_when_backend_raises(self):
        backend = _RaisingBackend(RuntimeError("simulated API failure"))
        session = OpenTasteSession(
            backend=backend, experiment_label="rollback_test"
        )
        assert session.cycle == 0
        with pytest.raises(RuntimeError, match="simulated"):
            session.exchange("hello")
        assert session.cycle == 0
        # And a subsequent call still starts from 1, not 2.
        backend2 = _CannedBackend({"response": "ok"})
        session._backend = backend2
        session.exchange("again")
        assert session.cycle == 1

    def test_cycle_advances_normally_on_success(self):
        backend = _CannedBackend({"response": "ok"})
        session = OpenTasteSession(
            backend=backend, experiment_label="happy_path_test"
        )
        session.exchange("first")
        assert session.cycle == 1
        session.exchange("second")
        assert session.cycle == 2
