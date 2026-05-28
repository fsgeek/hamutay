"""Unit tests for taste_open harness logic.

Does NOT make API calls — uses fake backends where transport is needed.

Covers:
- _apply_updates default-stable-via-key-presence protocol
- _truncate_largest_tool_results context-budget recovery helper
- OpenTasteSession.exchange cycle-counter rollback on failure
"""

import copy
import json

import anthropic
import httpx
import pytest

from hamutay.taste_open import (
    AnthropicTasteBackend,
    ExchangeResult,
    OpenTasteSession,
    _apply_updates,
    _estimate_tool_result_tokens,
    _is_context_limit_error,
    _parse_requested_vs_limit,
    _truncate_largest_tool_results,
)


def _byte_size_400() -> anthropic.BadRequestError:
    """The exact error class Moonshot/Kimi raises when the request body
    exceeds its 4 MiB ceiling. The message talks about *bytes*, not tokens —
    which is why the token-keyed recovery guard was blind to it."""
    body = {
        "error": {
            "type": "invalid_request_error",
            "message": (
                "Invalid request: total message size 11041058 "
                "exceeds limit 4194304"
            ),
        }
    }
    request = httpx.Request(
        "POST", "https://api.moonshot.ai/anthropic/v1/messages"
    )
    response = httpx.Response(400, request=request, json=body)
    return anthropic.BadRequestError(
        f"Error code: 400 - {body}", response=response, body=body
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

    def test_stub_keeps_loud_head_slice(self):
        # The dropped block keeps an orientation head + a loud declared loss,
        # not a pure-absence stub: the reach makes contact and the boundary
        # is honest about what was elided.
        original = "HEADMARKER" + ("z" * 100_000)
        conv = self._make_conversation([len(original)])
        conv[0]["content"][0]["content"] = original
        _truncate_largest_tool_results(conv, target_drop_tokens=10_000)
        stub = json.loads(conv[0]["content"][0]["content"])
        assert stub["head"].startswith("HEADMARKER")
        assert stub["shown_chars"] < stub["original_size_chars"]
        assert stub["elided_chars"] == stub["original_size_chars"] - stub["shown_chars"]
        assert "fetch_more" in "".join(stub.keys()) or stub.get("how_to_fetch_more")

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


class TestContextLimitErrorDetection:
    """The recovery guard must recognize the *byte-size* rejection, not just
    the token-limit phrasing. Kimi's 'total message size N exceeds limit M'
    crashed the framework because the guard was keyed only to token errors."""

    def test_recognizes_byte_size_rejection(self):
        assert _is_context_limit_error(_byte_size_400()) is True

    def test_recognizes_token_limit_phrasing(self):
        exc = RuntimeError("prompt is too long: 300000 tokens > 200000")
        assert _is_context_limit_error(exc) is True

    def test_ignores_unrelated_error(self):
        exc = RuntimeError("invalid api key")
        assert _is_context_limit_error(exc) is False


class TestParseRequestedVsLimit:
    def test_token_limit_format(self):
        exc = RuntimeError("... limit: 200000 (requested: 250000) ...")
        requested, limit = _parse_requested_vs_limit(exc)
        assert (requested, limit) == (250000, 200000)

    def test_byte_size_format_normalized_to_token_equivalents(self):
        # 'total message size 11041058 exceeds limit 4194304' is in *bytes*;
        # the helper normalizes to token-equivalents so the downstream drop
        # math (which multiplies by chars/token) stays in one unit.
        requested, limit = _parse_requested_vs_limit(_byte_size_400())
        assert requested is not None and limit is not None
        assert requested > limit
        # bytes // 4 (the chars/token estimate)
        assert limit == 4194304 // 4
        assert requested == 11041058 // 4


# --- Fakes mimicking the anthropic streaming client for _call_multi_turn ---


class _FakeBlock:
    def __init__(self, *, btype, name=None, input=None, id=None, text=None):
        self.type = btype
        self.name = name
        self.input = input
        self.id = id
        self.text = text

    def model_dump(self):
        if self.type == "tool_use":
            return {
                "type": "tool_use",
                "name": self.name,
                "input": self.input,
                "id": self.id,
            }
        return {"type": self.type, "text": self.text}


class _FakeUsage:
    def __init__(self, input_tokens=0, output_tokens=0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_read_input_tokens = 0
        self.cache_creation_input_tokens = 0


class _FakeMessage:
    def __init__(self, content, *, stop_reason="tool_use", usage=None):
        self.content = content
        self.stop_reason = stop_reason
        self.usage = usage or _FakeUsage()


class _FakeStreamCtx:
    def __init__(self, item):
        self._item = item

    def __enter__(self):
        if isinstance(self._item, Exception):
            raise self._item
        return self

    def __exit__(self, *_):
        return False

    def get_final_message(self):
        return self._item


class _FakeMessages:
    """Plays a scripted sequence of responses/exceptions; snapshots each
    outgoing `messages` payload so the test can inspect request sizes."""

    def __init__(self, script):
        self._script = list(script)
        self.calls = 0
        self.sent_messages = []

    def stream(self, **kwargs):
        self.sent_messages.append(copy.deepcopy(kwargs["messages"]))
        item = self._script[self.calls]
        self.calls += 1
        return _FakeStreamCtx(item)


class _FakeClient:
    def __init__(self, script):
        self.messages = _FakeMessages(script)


class _FakeToolExecutor:
    """Returns a fixed (large) result for any perception tool call."""

    def __init__(self, result):
        self._result = result
        self.activity_log = []
        self.executed = []

    def execute(self, name, tool_input):
        self.executed.append((name, tool_input))
        return self._result

    def log_event(self, event):
        self.activity_log.append(event)


class TestMultiTurnByteSizeRecovery:
    """End-to-end: a perception tool returns a large result, the next request
    is rejected for byte size, and the loop must recover (truncate + force a
    terminal turn) rather than crashing the cycle."""

    def _run(self):
        big = {"stdout": "L" * 300_000}
        perception = _FakeMessage(
            [
                _FakeBlock(
                    btype="tool_use",
                    name="read",
                    input={"path": "experiments/taste_open/other.jsonl"},
                    id="tu_read_1",
                )
            ],
            usage=_FakeUsage(input_tokens=100, output_tokens=50),
        )
        terminal = _FakeMessage(
            [
                _FakeBlock(
                    btype="tool_use",
                    name="think_and_respond",
                    input={"response": "that file was larger than I could hold"},
                    id="tu_tr_1",
                )
            ],
            usage=_FakeUsage(input_tokens=200, output_tokens=80),
        )
        client = _FakeClient([perception, _byte_size_400(), terminal])
        backend = AnthropicTasteBackend(client=client, max_tokens=64_000)  # type: ignore[arg-type]
        executor = _FakeToolExecutor(big)
        result = backend._call_multi_turn(
            model="kimi-k2.6",
            system="sys",
            messages=[{"role": "user", "content": "read the other log"}],
            experiment_label="bytesize_recovery_test",
            extra_tools=[
                {"name": "read", "description": "d", "input_schema": {}}
            ],
            tool_executor=executor,
        )
        return result, client

    def test_recovers_instead_of_raising(self):
        result, client = self._run()
        assert result.raw_output == {
            "response": "that file was larger than I could hold"
        }
        # perception, rejected request, retry-after-truncation = 3 stream calls.
        assert client.messages.calls == 3

    def test_retry_request_is_smaller_than_rejected_request(self):
        _, client = self._run()
        rejected = len(json.dumps(client.messages.sent_messages[1], default=str))
        retried = len(json.dumps(client.messages.sent_messages[2], default=str))
        assert retried < rejected
        assert retried < 50_000
