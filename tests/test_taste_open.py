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

    def test_unprotected_cycle_can_be_overwritten_and_deleted(self):
        overwrite = _apply_updates(
            {"cycle": 1, "mood": "steady"},
            {"response": "hi", "cycle": 99},
            cycle=2,
        )
        assert overwrite["cycle"] == 99

        delete = _apply_updates(
            {"cycle": 1, "mood": "steady"},
            {"response": "hi", "deleted_regions": ["cycle"]},
            cycle=2,
        )
        assert "cycle" not in delete

    def test_protected_fields_ignore_model_update_and_delete(self):
        prior = {
            "cycle": 1,
            "_activity_log": [{"tool": "schedule_event"}],
            "mood": "steady",
        }
        raw = {
            "response": "hi",
            "cycle": 99,
            "_activity_log": [{"tool": "forged"}],
            "mood": "bright",
            "deleted_regions": ["cycle", "_activity_log"],
        }

        state = _apply_updates(
            prior,
            raw,
            cycle=2,
            protected_fields={"cycle", "_activity_log"},
        )

        assert state["cycle"] == 2
        assert state["_activity_log"] == [{"tool": "schedule_event"}]
        assert state["mood"] == "bright"

    def test_protected_fields_do_not_hide_unprotected_overlap(self):
        raw = {
            "response": "hi",
            "cycle": 99,
            "mood": "bright",
            "deleted_regions": ["cycle", "mood"],
        }
        with pytest.raises(ValueError, match="overlaps"):
            _apply_updates(
                {"cycle": 1, "mood": "steady"},
                raw,
                cycle=2,
                protected_fields={"cycle"},
            )

    def test_protected_fields_allow_unprotected_deletion(self):
        raw = {"response": "bye", "deleted_regions": ["name", "cycle"]}
        state = _apply_updates(
            {"cycle": 1, "mood": "steady", "name": "Ada"},
            raw,
            cycle=2,
            protected_fields={"cycle"},
        )
        assert state["cycle"] == 2
        assert state["mood"] == "steady"
        assert "name" not in state


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


class _SequenceBackend:
    """Backend that returns a sequence of ExchangeResult objects."""

    def __init__(self, results: list[ExchangeResult]):
        self._results = list(results)
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
        if not self._results:
            raise AssertionError("sequence backend exhausted")
        return self._results.pop(0)


class _RecoveryBuilder:
    def __init__(self):
        self.calls = []

    def recover(
        self,
        *,
        cycle,
        record_id,
        timestamp,
        prior_state,
        raw_output,
        response_text,
        failure_classification,
    ):
        self.calls.append(
            {
                "cycle": cycle,
                "record_id": record_id,
                "timestamp": timestamp,
                "prior_state": prior_state,
                "raw_output": raw_output,
                "response_text": response_text,
                "failure_classification": failure_classification,
            }
        )
        return {
            "accepted_state": None,
            "live_policy": "strict_reject",
            "candidate_rows": [
                {
                    "row_type": "protocol_note",
                    "status": "candidate",
                    "text": "captured overlap",
                    "accepted": False,
                }
            ],
        }


class _FailingRecoveryBuilder:
    def recover(self, **kwargs):
        del kwargs
        raise RuntimeError("repair boom")


class _RequiredRepairStateValidator:
    def __init__(self):
        self.calls = []

    def validate(
        self,
        *,
        cycle,
        record_id,
        timestamp,
        prior_state,
        raw_output,
        response_text,
        state,
    ):
        del record_id, timestamp, prior_state, raw_output, response_text
        missing = []
        if state.get("task_status") != "done":
            missing.append("task_status")
        if state.get("evidence_count") != 4:
            missing.append("evidence_count")
        artifact = {
            "valid": not missing,
            "status": "valid" if not missing else "invalid",
            "missing_fields": missing,
            "cycle_seen": cycle,
        }
        self.calls.append(artifact)
        return artifact


class _StaticStateRepairBuilder:
    def __init__(self, prompt: str = "Repair durable state now."):
        self.prompt = prompt
        self.calls = []

    def build_repair_prompt(self, **kwargs):
        self.calls.append(kwargs)
        return self.prompt


class _FailingStateValidator:
    def validate(self, **kwargs):
        del kwargs
        raise RuntimeError("validator boom")


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

    def test_merge_failure_is_logged_without_advancing_state(self, tmp_path):
        backend = _SequenceBackend([
            ExchangeResult(
                raw_output={
                    "response": "bad",
                    "mood": "new",
                    "deleted_regions": ["mood"],
                },
                stop_reason="tool_use",
                input_tokens=11,
                output_tokens=22,
            ),
            ExchangeResult(
                raw_output={"response": "ok", "mood": "steady"},
                stop_reason="tool_use",
                input_tokens=33,
                output_tokens=44,
            ),
        ])
        log_path = tmp_path / "session.jsonl"
        session = OpenTasteSession(
            backend=backend,
            experiment_label="merge_failure_capture_test",
            log_path=str(log_path),
        )

        with pytest.raises(ValueError, match="deleted_regions overlaps updates"):
            session.exchange("fail")

        assert session.cycle == 0
        assert session.state is None
        records = [
            json.loads(line)
            for line in log_path.read_text().splitlines()
            if line.strip()
        ]
        assert len(records) == 1
        failed = records[0]
        assert failed["cycle"] == 1
        assert failed["status"] == "failed"
        assert failed["raw_output"]["mood"] == "new"
        assert failed["state"] is None
        assert failed["usage"]["input_tokens"] == 11
        assert failed["failure_classification"]["failure_stage"] == "state_merge"
        assert failed["failure_classification"]["overlap_keys"] == ["mood"]
        assert "continuity_curation" not in failed
        assert failed["scheduled_events"] == []

        assert session.exchange("succeed") == "ok"
        assert session.cycle == 1
        assert session.state == {"cycle": 1, "mood": "steady"}
        records = [
            json.loads(line)
            for line in log_path.read_text().splitlines()
            if line.strip()
        ]
        assert len(records) == 2
        assert records[1]["cycle"] == 1
        assert "status" not in records[1]
        assert records[1]["state"]["mood"] == "steady"

    def test_protocol_recovery_hook_logs_candidate_artifact(self, tmp_path):
        backend = _SequenceBackend([
            ExchangeResult(
                raw_output={
                    "response": "bad",
                    "mood": "new",
                    "deleted_regions": ["mood"],
                },
                stop_reason="tool_use",
                input_tokens=11,
                output_tokens=22,
            ),
            ExchangeResult(
                raw_output={"response": "ok", "mood": "steady"},
                stop_reason="tool_use",
                input_tokens=33,
                output_tokens=44,
            ),
        ])
        builder = _RecoveryBuilder()
        log_path = tmp_path / "session.jsonl"
        session = OpenTasteSession(
            backend=backend,
            experiment_label="protocol_recovery_hook_test",
            log_path=str(log_path),
            protocol_recovery_builder=builder,
        )

        with pytest.raises(ValueError, match="deleted_regions overlaps updates"):
            session.exchange("fail")

        assert session.cycle == 0
        assert session.state is None
        assert len(builder.calls) == 1
        assert builder.calls[0]["cycle"] == 1
        assert builder.calls[0]["failure_classification"]["overlap_keys"] == ["mood"]
        records = [
            json.loads(line)
            for line in log_path.read_text().splitlines()
            if line.strip()
        ]
        failed = records[0]
        assert failed["protocol_recovery"]["status"] == "success"
        artifact = failed["protocol_recovery"]["artifact"]
        assert artifact["accepted_state"] is None
        assert artifact["live_policy"] == "strict_reject"
        assert artifact["candidate_rows"][0]["status"] == "candidate"
        assert "continuity_curation" not in failed

        assert session.exchange("succeed") == "ok"
        assert session.cycle == 1
        assert session.state == {"cycle": 1, "mood": "steady"}

    def test_protocol_recovery_hook_failure_is_logged_without_masking(self, tmp_path):
        backend = _SequenceBackend([
            ExchangeResult(
                raw_output={
                    "response": "bad",
                    "mood": "new",
                    "deleted_regions": ["mood"],
                },
                stop_reason="tool_use",
                input_tokens=11,
                output_tokens=22,
            )
        ])
        log_path = tmp_path / "session.jsonl"
        session = OpenTasteSession(
            backend=backend,
            experiment_label="protocol_recovery_failure_test",
            log_path=str(log_path),
            protocol_recovery_builder=_FailingRecoveryBuilder(),
        )

        with pytest.raises(ValueError, match="deleted_regions overlaps updates"):
            session.exchange("fail")

        records = [
            json.loads(line)
            for line in log_path.read_text().splitlines()
            if line.strip()
        ]
        failed = records[0]
        assert failed["failure_classification"]["error_type"] == "ValueError"
        assert failed["protocol_recovery"]["status"] == "failed"
        assert failed["protocol_recovery"]["error_type"] == "RuntimeError"
        assert failed["protocol_recovery"]["error"] == "repair boom"
        assert session.cycle == 0
        assert session.state is None


class TestStateValidationRepairScaffold:
    def test_no_validator_preserves_default_log_shape(self, tmp_path):
        backend = _CannedBackend({"response": "ok"})
        log_path = tmp_path / "session.jsonl"
        session = OpenTasteSession(
            backend=backend,
            experiment_label="state_validation_default_test",
            log_path=str(log_path),
        )

        assert session.exchange("first") == "ok"

        records = [
            json.loads(line)
            for line in log_path.read_text().splitlines()
            if line.strip()
        ]
        assert backend.calls == 1
        assert "state_validation" not in records[0]
        assert "repair_input_tokens" not in records[0]["usage"]
        assert "repair_output_tokens" not in records[0]["usage"]

    def test_first_pass_valid_state_logs_validation_without_repair(self, tmp_path):
        backend = _SequenceBackend([
            ExchangeResult(
                raw_output={
                    "response": "done",
                    "task_status": "done",
                    "evidence_count": 4,
                },
                stop_reason="tool_use",
                input_tokens=11,
                output_tokens=22,
            )
        ])
        validator = _RequiredRepairStateValidator()
        repair_builder = _StaticStateRepairBuilder()
        log_path = tmp_path / "session.jsonl"
        session = OpenTasteSession(
            backend=backend,
            experiment_label="state_validation_first_pass_test",
            log_path=str(log_path),
            state_validator=validator,
            state_repair_builder=repair_builder,
        )

        assert session.exchange("first") == "done"

        records = [
            json.loads(line)
            for line in log_path.read_text().splitlines()
            if line.strip()
        ]
        validation = records[0]["state_validation"]
        assert backend.calls == 1
        assert repair_builder.calls == []
        assert validation["status"] == "valid"
        assert validation["repair_attempted"] is False
        assert validation["first_pass"]["status"] == "valid"
        assert session.state["task_status"] == "done"

    def test_invalid_state_gets_one_model_authored_repair(self, tmp_path):
        backend = _SequenceBackend([
            ExchangeResult(
                raw_output={"response": "I recorded it."},
                stop_reason="tool_use",
                input_tokens=11,
                output_tokens=22,
            ),
            ExchangeResult(
                raw_output={
                    "response": "Repaired.",
                    "task_status": "done",
                    "evidence_count": 4,
                },
                stop_reason="tool_use",
                input_tokens=33,
                output_tokens=44,
            ),
        ])
        validator = _RequiredRepairStateValidator()
        repair_builder = _StaticStateRepairBuilder()
        log_path = tmp_path / "session.jsonl"
        session = OpenTasteSession(
            backend=backend,
            experiment_label="state_validation_repair_success_test",
            log_path=str(log_path),
            state_validator=validator,
            state_repair_builder=repair_builder,
        )

        assert session.exchange("first") == "Repaired."

        records = [
            json.loads(line)
            for line in log_path.read_text().splitlines()
            if line.strip()
        ]
        record = records[0]
        validation = record["state_validation"]
        assert backend.calls == 2
        assert len(repair_builder.calls) == 1
        assert validation["status"] == "repaired"
        assert validation["first_pass"]["status"] == "invalid"
        assert validation["repair_attempted"] is True
        assert validation["repair"]["status"] == "valid"
        assert validation["repair"]["raw_output"]["task_status"] == "done"
        assert record["raw_output"]["response"] == "Repaired."
        assert record["prior_state"] is None
        assert record["state"]["task_status"] == "done"
        assert record["usage"]["input_tokens"] == 44
        assert record["usage"]["output_tokens"] == 66
        assert record["usage"]["repair_input_tokens"] == 33
        assert record["usage"]["repair_output_tokens"] == 44

    def test_failed_repair_is_logged_as_unrepaired_and_bounded(self, tmp_path):
        backend = _SequenceBackend([
            ExchangeResult(
                raw_output={"response": "I recorded it."},
                stop_reason="tool_use",
                input_tokens=11,
                output_tokens=22,
            ),
            ExchangeResult(
                raw_output={"response": "Repair complete."},
                stop_reason="tool_use",
                input_tokens=33,
                output_tokens=44,
            ),
        ])
        validator = _RequiredRepairStateValidator()
        repair_builder = _StaticStateRepairBuilder()
        log_path = tmp_path / "session.jsonl"
        session = OpenTasteSession(
            backend=backend,
            experiment_label="state_validation_unrepaired_test",
            log_path=str(log_path),
            state_validator=validator,
            state_repair_builder=repair_builder,
        )

        assert session.exchange("first") == "Repair complete."

        records = [
            json.loads(line)
            for line in log_path.read_text().splitlines()
            if line.strip()
        ]
        record = records[0]
        validation = record["state_validation"]
        assert backend.calls == 2
        assert len(repair_builder.calls) == 1
        assert validation["status"] == "unrepaired"
        assert validation["repair"]["status"] == "invalid"
        assert record["state"] == {"cycle": 1}
        assert record["raw_output"]["response"] == "Repair complete."

    def test_validator_failure_is_logged_without_repair(self, tmp_path):
        backend = _SequenceBackend([
            ExchangeResult(
                raw_output={"response": "ok"},
                stop_reason="tool_use",
                input_tokens=11,
                output_tokens=22,
            )
        ])
        repair_builder = _StaticStateRepairBuilder()
        log_path = tmp_path / "session.jsonl"
        session = OpenTasteSession(
            backend=backend,
            experiment_label="state_validation_validator_failure_test",
            log_path=str(log_path),
            state_validator=_FailingStateValidator(),
            state_repair_builder=repair_builder,
        )

        assert session.exchange("first") == "ok"

        records = [
            json.loads(line)
            for line in log_path.read_text().splitlines()
            if line.strip()
        ]
        validation = records[0]["state_validation"]
        assert backend.calls == 1
        assert repair_builder.calls == []
        assert validation["status"] == "validator_failed"
        assert validation["first_pass"]["status"] == "validator_failed"
        assert "repair" not in validation


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


def test_anthropic_backend_returns_mixed_batch_tool_results_before_terminal_state():
    mixed = _FakeMessage(
        [
            _FakeBlock(
                btype="tool_use",
                name="read",
                input={"path": "README.md"},
                id="tu_read_1",
            ),
            _FakeBlock(
                btype="tool_use",
                name="think_and_respond",
                input={"response": "premature"},
                id="tu_tr_1",
            ),
        ],
        usage=_FakeUsage(input_tokens=100, output_tokens=50),
    )
    terminal = _FakeMessage(
        [
            _FakeBlock(
                btype="tool_use",
                name="think_and_respond",
                input={"response": "saw tool result"},
                id="tu_tr_2",
            )
        ],
        usage=_FakeUsage(input_tokens=200, output_tokens=80),
    )
    client = _FakeClient([mixed, terminal])
    backend = AnthropicTasteBackend(client=client, max_tokens=64_000)  # type: ignore[arg-type]
    executor = _FakeToolExecutor({"content": "readme"})

    result = backend._call_multi_turn(
        model="kimi-k2.6",
        system="sys",
        messages=[{"role": "user", "content": "read then respond"}],
        experiment_label="mixed_batch_test",
        extra_tools=[
            {"name": "read", "description": "d", "input_schema": {}}
        ],
        tool_executor=executor,
    )

    assert result.raw_output == {"response": "saw tool result"}
    assert executor.executed == [("read", {"path": "README.md"})]
    retry_messages = client.messages.sent_messages[1]
    assistant_content = retry_messages[-2]["content"]
    tool_uses = [
        block for block in assistant_content
        if block.get("type") == "tool_use"
    ]
    assert [block["id"] for block in tool_uses] == ["tu_read_1"]
    assert retry_messages[-1]["content"][0]["tool_use_id"] == "tu_read_1"


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
