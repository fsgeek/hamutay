"""Spec test 2: heartbeat inheritance -> real session -> executor -> disk."""
import json
from uuid import uuid4

import pytest

from hamutay.events import WakeContext
from hamutay import heartbeat
from hamutay.context_policy import ContextPolicy
from hamutay.taste_open import ExchangeResult, OpenAITasteBackend, OpenTasteSession
from hamutay.tools import ToolExecutor

from .helpers import STAMP, disk_rows, gate


class SendingBackend(OpenAITasteBackend):
    """Replace only model inference; executor and persistence stay real."""
    def __init__(self):
        super().__init__(api_key="unused", wake_mode="natural")
        self.receipt = None

    def call(self, *, tool_executor, extra_tools, **kwargs):
        assert "send_message" in [t["name"] for t in extra_tools]
        self.receipt = tool_executor.execute("send_message", {
            "to": "plaza", "text": "door carrier post", "carrier": "model-spoof",
            "from": "guest:outsider"})
        return ExchangeResult(raw_output={"response": "sent", "state": {"observed": True}},
                              stop_reason="end_turn", input_tokens=1, output_tokens=1)


@pytest.mark.parametrize("model", [" anthropic/claude-haiku-4-5 ", " qwen3.8-27b-q4km "])
@pytest.mark.parametrize("launch_kind", ["fresh", "resumed", "override"])
def test_session_carrier_uses_effective_model_and_ignores_tool_input(house, monkeypatch, model, launch_kind):
    root, cfg, binding = house
    gate(cfg)
    log = cfg.members["qwen"].session
    if launch_kind != "fresh":
        inherited_model = "old-provider/old-model" if launch_kind == "override" else model
        log.write_text(json.dumps({"cycle": 3, "state": {"prior": True}, "model": inherited_model,
                                   "wake_mode": "natural", "launch": {
                                       "model": inherited_model, "provider": "openrouter", "tools": True,
                                       "base_url": None}}) + "\n")
    argv = ["--log-path", str(log), "--event-log-path", str(cfg.members["qwen"].events),
            "--project-root", str(root), "--api-key", "unused", "--no-persist",
            "--context-limit", "262144"]
    if launch_kind != "resumed":
        argv += ["--model", model]
    if launch_kind == "fresh":
        argv += ["--provider", "openrouter", "--wake-mode", "natural"]
    args = heartbeat.build_parser().parse_args(argv)
    # Keep heartbeat construction and argument forwarding real. Replace only
    # the external tokenizer probe and the provider's model inference call.
    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(lambda cls, *a, **kw: ContextPolicy.none()))
    monkeypatch.setattr(OpenAITasteBackend, "call", SendingBackend.call)
    session, backend, launch = heartbeat.build_session(args)
    session.exchange("post", event_managed=True, wake_context=WakeContext(
        event_id=str(uuid4()), run_id=str(uuid4()), started_at=STAMP, event={}))
    assert backend.receipt["sent"] is True
    row, = disk_rows(cfg)
    assert row["carrier"] == model.strip()
    assert row["from"] == "door:qwen" and row["via"] == "tool"


@pytest.mark.parametrize("model,enabled", [("alias\n", True), ("\u200d", True), ("", True), ("x" * 121, True), ("alias", False)])
def test_bad_model_or_absent_gate_still_sends_without_carrier(house, model, enabled):
    root, cfg, binding = house
    gate(cfg, enabled)
    backend = SendingBackend()
    session = OpenTasteSession(model=model, backend=backend, log_path=str(cfg.members["qwen"].session),
                               event_log_path=str(cfg.members["qwen"].events), enable_tools=True,
                               project_root=root, wake_mode="natural", assembly=binding,
                               memory_base_probability=0)
    session.exchange("post", event_managed=True, wake_context=WakeContext(
        event_id=str(uuid4()), run_id=str(uuid4()), started_at=STAMP, event={}))
    assert backend.receipt["sent"] is True
    row, = disk_rows(cfg)
    assert "carrier" not in row


def test_executor_interface_uses_harness_carrier(house):
    root, cfg, binding = house
    gate(cfg)
    executor = ToolExecutor(project_root=root, cycle=1, scheduled_by_record_id=uuid4(), assembly=binding,
                            wake_context=WakeContext(event_id=str(uuid4()), run_id=str(uuid4()),
                                                     started_at=STAMP, event={}), carrier="harness-alias")
    assert executor.execute("send_message", {"to": "plaza", "text": "hi", "carrier": "forged"})["sent"]
    assert disk_rows(cfg)[0]["carrier"] == "harness-alias"
