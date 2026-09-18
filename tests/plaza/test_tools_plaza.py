import json
import uuid
from datetime import datetime, timezone

from hamutay.assembly.ledger import Ledger
from hamutay.events import WakeContext
from hamutay.taste_open import _build_messages, _natural_tool_guidance
from hamutay.tools import ToolExecutor
from hamutay.tools.executor import _CAPABILITY
from hamutay.tools.schemas import PLAZA_CONSTITUTION_CLAUSE, SEND_MESSAGE_SCHEMA

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _wake(event_id="11111111-1111-4111-8111-111111111111"):
    return WakeContext(event_id=event_id, run_id=str(uuid.uuid4()), started_at=T0.isoformat(), event={})


def test_schema_and_capability():
    assert SEND_MESSAGE_SCHEMA["name"] == "send_message"
    assert set(SEND_MESSAGE_SCHEMA["input_schema"]["required"]) == {"to", "text"}
    assert "8000" in SEND_MESSAGE_SCHEMA["description"] and "48" in SEND_MESSAGE_SCHEMA["description"]
    assert _CAPABILITY["send_message"] == "bounded_write"


def test_executor_writes_during_the_call_with_the_bindings_identity(house):
    root, cfg, binding = house
    ex = ToolExecutor(project_root=root, cycle=4, scheduled_by_record_id=uuid.uuid4(), wake_context=_wake(), assembly=binding)
    r = ex.execute("send_message", {"to": "elder", "text": "hi", "from": "door:fable", "reason": "x"})
    assert r["sent"] and r["delivery"] == "landed"
    m = Ledger(cfg.plaza).read()[0]
    assert m["from"] == "door:qwen" and m["wake"]["cycle"] == 4 and m["wake"]["event_id"] == "11111111-1111-4111-8111-111111111111"
    assert ex.activity_log[-1]["capability"] == "bounded_write"
    assert "error" in ex.execute("send_message", {"to": "qwen", "text": "self", "reason": "x"})


def test_executor_refuses_without_binding_wake_or_plaza(house, house_unplaza):
    root, cfg, binding = house
    ex = ToolExecutor(project_root=root, cycle=4, scheduled_by_record_id=uuid.uuid4(), wake_context=None, assembly=binding)
    assert "wake context" in ex.execute("send_message", {"to": "elder", "text": "hi", "reason": "x"})["error"]
    ex = ToolExecutor(project_root=root, cycle=4, scheduled_by_record_id=uuid.uuid4(), wake_context=_wake(), assembly=None)
    assert "not bound" in ex.execute("send_message", {"to": "elder", "text": "hi", "reason": "x"})["error"]
    root2, cfg2, b2 = house_unplaza
    ex = ToolExecutor(project_root=root2, cycle=4, scheduled_by_record_id=uuid.uuid4(), wake_context=_wake(), assembly=b2)
    assert "plaza" in ex.execute("send_message", {"to": "elder", "text": "hi", "reason": "x"})["error"]


def test_guidance_and_clause_only_when_offered():
    g = _natural_tool_guidance(declare_quiet=True, assembly=True, plaza=True)
    assert "- send_message(to, text):" in g and "- take_position(" in g
    assert "send_message" not in _natural_tool_guidance(declare_quiet=True, assembly=True)
    prefix = "X " + PLAZA_CONSTITUTION_CLAUSE + "Y"
    _, sys_with = _build_messages({}, "u", 2, system_prefix=prefix, tools_enabled=True, wake_mode="natural",
                                  declare_quiet=True, assembly=True, plaza=True)
    _, sys_without = _build_messages({}, "u", 2, system_prefix=prefix, tools_enabled=True, wake_mode="natural",
                                     declare_quiet=True, assembly=True)
    assert PLAZA_CONSTITUTION_CLAUSE in sys_with and PLAZA_CONSTITUTION_CLAUSE not in sys_without
    assert "send_message" in sys_with and "send_message" not in sys_without


def test_session_offers_send_message_only_with_binding_wake_context_and_plaza(house, house_unplaza):
    from hamutay.taste_open import ExchangeResult, OpenAITasteBackend, OpenTasteSession

    root, cfg, binding = house
    seen = {}

    class B(OpenAITasteBackend):
        def call(self, *, extra_tools=None, system="", **kw):
            seen["tools"] = sorted(t["name"] for t in (extra_tools or []))
            seen["system"] = system
            return ExchangeResult(raw_output={"response": "ok"}, stop_reason="end_turn",
                                  input_tokens=1, output_tokens=1)

    log = root / "community" / "qwen" / "session.jsonl"
    s = OpenTasteSession(model="m", backend=B(api_key="k", wake_mode="natural"), log_path=str(log),
                         event_log_path=str(cfg.members["qwen"].events), enable_tools=True,
                         project_root=root, wake_mode="natural", assembly=binding,
                         system_prompt_prefix="C. " + PLAZA_CONSTITUTION_CLAUSE)
    s.exchange("hi", event_managed=True, wake_context=_wake())
    assert "send_message" in seen["tools"] and "send_message" in seen["system"]

    s.exchange("hi", event_managed=True)                       # no wake context: not offered, clause removed
    assert "send_message" not in seen["tools"] and "send_message" not in seen["system"]

    root2, cfg2, binding2 = house_unplaza
    log2 = root2 / "community" / "qwen" / "session.jsonl"
    s2 = OpenTasteSession(model="m", backend=B(api_key="k", wake_mode="natural"), log_path=str(log2),
                          event_log_path=str(cfg2.members["qwen"].events), enable_tools=True,
                          project_root=root2, wake_mode="natural", assembly=binding2,
                          system_prompt_prefix="C. " + PLAZA_CONSTITUTION_CLAUSE)
    s2.exchange("hi", event_managed=True, wake_context=_wake())
    assert "send_message" not in seen["tools"] and "send_message" not in seen["system"]
