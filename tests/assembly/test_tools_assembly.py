import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from hamutay.assembly.binding import bind, load_members
from hamutay.assembly.convene import convene
from hamutay.assembly.ledger import Ledger, iso
from hamutay.assembly.position import PositionRefused, record_position
from hamutay.assembly.records import reduce
from hamutay.events import EventStore, WakeContext, build_inbound_event
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import ASSEMBLY_CONSTITUTION_CLAUSE, CONVENE_SCHEMA, TAKE_POSITION_SCHEMA

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


@pytest.fixture
def house(tmp_path):
    plaza = tmp_path / "community" / "plaza"; plaza.mkdir(parents=True)
    members = {d: {"session": f"community/{d}/session.jsonl", "events": f"community/{d}/session.jsonl.events.jsonl"}
               for d in ("qwen", "elder")}
    (plaza / "members.json").write_text(json.dumps({"ledger": "community/plaza/assembly.jsonl", "members": members}))
    for d in ("qwen", "elder"):
        (tmp_path / "community" / d).mkdir()
    cfg = load_members(tmp_path)
    binding, _ = bind(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)
    led = Ledger(cfg.ledger)
    q = convene(led, cfg, convener="custodian", text="q?", closes_in=timedelta(days=7), now=T0,
                proposal_procedure={"rule": "consent-v0"}, artifact={})
    return tmp_path, led, cfg, binding, q


def _wake(event_id="e", started=T0 + timedelta(hours=1)):
    return WakeContext(event_id=event_id, run_id=str(uuid4()), started_at=iso(started), event={})


def test_record_position_writes_during_the_call_and_binds_the_wake(house):
    root, led, cfg, binding, q = house
    w = _wake()
    p = record_position(led, binding=binding, wake=w, cycle=3, record_id=uuid4(), question_id=q["question_id"],
                        stance="dissent", reasons="not yet", now=T0 + timedelta(hours=1))
    assert p["seq"] and p["member"] == "door:qwen" and p["event_id"] == "e" and p["run_id"] == w.run_id
    assert p["wake_started_at"] == w.started_at and p["events_path"] == str(cfg.members["qwen"].events)
    assert reduce(led.read()).positions[-1]["position_id"] == p["position_id"]


def test_record_position_refusals(house):
    root, led, cfg, binding, q = house
    with pytest.raises(PositionRefused):
        record_position(led, binding=binding, wake=_wake(), cycle=1, record_id=uuid4(), question_id="nope",
                        stance="assent", reasons=None, now=T0)
    with pytest.raises(PositionRefused):          # wake began after closes_at
        record_position(led, binding=binding, wake=_wake(started=T0 + timedelta(days=8)), cycle=1,
                        record_id=uuid4(), question_id=q["question_id"], stance="assent", reasons=None, now=T0)
    with pytest.raises(ValueError):
        record_position(led, binding=binding, wake=_wake(), cycle=1, record_id=uuid4(),
                        question_id=q["question_id"], stance="maybe", reasons=None, now=T0)


def test_record_position_after_a_closing_is_a_late_position(house):
    from hamutay.assembly.records import closing_id_for
    root, led, cfg, binding, q = house
    led.append({"record_type": "closing", "closing_id": closing_id_for(q["question_id"]),
                "question_id": q["question_id"], "lineage_id": q["lineage_id"], "round": 1,
                "outcome": "unresolved", "governing": q["governing"], "provisional": True, "tally": {},
                "positions": [], "testimony": [], "absent": [], "next_question": None,
                "closed_by": "cli:t", "closed_at": iso(T0 + timedelta(days=7)), "proposal_sha256": "x",
                "delivery": {}})
    with pytest.raises(PositionRefused, match="closed"):
        record_position(led, binding=binding, wake=_wake(), cycle=1, record_id=uuid4(),
                        question_id=q["question_id"], stance="dissent", reasons=None, now=T0 + timedelta(days=8))
    assert reduce(led.read()).records[-1]["record_type"] == "late_position"


def test_executor_take_position_returns_error_when_the_ledger_is_unavailable(house, monkeypatch):
    root, led, cfg, binding, q = house
    ex = ToolExecutor(project_root=root, cycle=2, scheduled_by_record_id=uuid4(),
                      wake_context=_wake(), assembly=binding)
    ok = ex.execute("take_position", {"question_id": q["question_id"], "stance": "assent"})
    assert ok["recorded"] is True and ok["seq"]
    from hamutay.assembly import ledger as L
    def boom(self, timeout_s):
        raise L.LedgerUnavailable("busy")
    monkeypatch.setattr(L.Ledger, "try_locked", boom)
    bad = ex.execute("take_position", {"question_id": q["question_id"], "stance": "dissent"})
    assert "error" in bad and "busy" in bad["error"]
    assert [p["stance"] for p in reduce(led.read()).positions] == ["assent"]     # nothing accepted


def test_executor_without_wake_context_or_binding_refuses(house):
    root, led, cfg, binding, q = house
    ex = ToolExecutor(project_root=root, cycle=2, scheduled_by_record_id=uuid4())
    assert "error" in ex.execute("take_position", {"question_id": q["question_id"], "stance": "assent"})
    assert "error" in ex.execute("convene", {"text": "x", "closes_in": "2d"})


def test_executor_convene_writes_a_question_for_the_door(house):
    root, led, cfg, binding, q = house
    ex = ToolExecutor(project_root=root, cycle=2, scheduled_by_record_id=uuid4(),
                      wake_context=_wake(), assembly=binding)
    out = ex.execute("convene", {"text": "should we?", "closes_in": "3d"})
    assert out["convened"] is True
    assert reduce(led.read()).open_lineage_for("door:qwen")["question_id"] == out["question_id"]


def test_session_offers_the_tools_only_with_binding_and_wake_context(house):
    from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession, _build_messages
    root, led, cfg, binding, q = house
    seen = {}

    class B(OpenAITasteBackend):
        def call(self, *, extra_tools=None, system="", **kw):
            seen["tools"] = sorted(t["name"] for t in (extra_tools or []))
            seen["system"] = system
            from hamutay.taste_open import ExchangeResult
            return ExchangeResult(raw_output={"response": "ok"}, stop_reason="end_turn",
                                  input_tokens=1, output_tokens=1)

    log = root / "community" / "qwen" / "session.jsonl"
    s = OpenTasteSession(model="m", backend=B(api_key="k", wake_mode="natural"), log_path=str(log),
                         event_log_path=str(cfg.members["qwen"].events), enable_tools=True,
                         project_root=root, wake_mode="natural", assembly=binding,
                         system_prompt_prefix="C. " + ASSEMBLY_CONSTITUTION_CLAUSE)
    s.exchange("hi", event_managed=True, wake_context=_wake())
    assert {"take_position", "convene"} <= set(seen["tools"]) and "take_position records" in seen["system"]
    s.exchange("hi", event_managed=True)                      # no wake context: not offered, clause removed
    assert "take_position" not in seen["tools"] and "take_position records" not in seen["system"]
    _, sys_text = _build_messages({}, "u", 1, system_prefix=ASSEMBLY_CONSTITUTION_CLAUSE, wake_mode="natural",
                                  tools_enabled=True, declare_quiet=True, assembly=False)
    assert "take_position" not in sys_text
