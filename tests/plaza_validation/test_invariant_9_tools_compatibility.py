import json
import uuid

from hamutay.events import EventStore, WakeContext, build_inbound_event, run_next_event
from hamutay.heartbeat import build_constitution
from hamutay.plaza.note import plaza_note
from hamutay.plaza.pass_ import run_plaza_pass
from hamutay.taste_open import (
    CapabilityProfile,
    ExchangeResult,
    OpenTasteSession,
    TasteBackend,
    _natural_tool_guidance,
)
from hamutay.tools.schemas import PLAZA_CONSTITUTION_CLAUSE
from tests.plaza_validation.conftest import T0, make_house


class _CaptureBackend(TasteBackend):
    capability = CapabilityProfile()
    wake_mode = "natural"

    def __init__(self):
        self.offered = []

    def call(self, model, system, messages, experiment_label, extra_tools=None, tool_executor=None):
        self.offered.append([tool["name"] for tool in (extra_tools or [])])
        return ExchangeResult(raw_output={"state": {}, "response": "ok"})


def _offered(root, binding, *, event_managed, wake_context):
    backend = _CaptureBackend()
    session = OpenTasteSession(
        backend=backend,
        enable_tools=True,
        project_root=root,
        wake_mode="natural",
        assembly=binding,
    )
    assert session.exchange("wake", event_managed=event_managed, wake_context=wake_context) == "ok"
    return backend.offered[-1]


def test_invariant_9_send_message_offered_only_for_assembly_wake_and_plaza_key(tmp_path):
    enabled_root, enabled_cfg, enabled_binding = make_house(tmp_path / "enabled", plaza=True)
    disabled_root, disabled_cfg, disabled_binding = make_house(tmp_path / "disabled", plaza=False)
    context = WakeContext(
        event_id="11111111-1111-4111-8111-111111111111",
        run_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        started_at=T0.isoformat(),
        event={},
    )

    assert "send_message" in _offered(
        enabled_root, enabled_binding, event_managed=True, wake_context=context
    )
    assert "send_message" not in _offered(
        disabled_root, disabled_binding, event_managed=True, wake_context=context
    )
    assert "send_message" not in _offered(
        enabled_root, enabled_binding, event_managed=False, wake_context=context
    )
    assert "send_message" not in _offered(
        enabled_root, enabled_binding, event_managed=True, wake_context=None
    )
    assert "send_message" not in _offered(
        enabled_root, None, event_managed=True, wake_context=context
    )


def test_invariant_9_absent_key_has_no_clause_guidance_note_or_pass(tmp_path):
    root, cfg, binding = make_house(tmp_path, plaza=False)
    assert "send_message" not in _natural_tool_guidance(
        declare_quiet=True, assembly=True, plaza=False
    )
    assert PLAZA_CONSTITUTION_CLAUSE not in build_constitution(
        None, assembly=True, plaza=False
    )
    assert plaza_note(cfg, "qwen", []) == []
    result, memo = run_plaza_pass(binding, now=T0)
    assert result["skipped"] is True
    assert result["units"] == 0
    assert cfg.plaza is None
    assert not (root / "community/plaza/plaza.jsonl").exists()


def test_invariant_9_build_inbound_external_and_run_next_none_match_unplaza_baseline(
    tmp_path, monkeypatch
):
    import hamutay.events as events_module

    unplaza_root, unplaza_cfg, unplaza_binding = make_house(tmp_path / "before", plaza=False)
    plaza_root, plaza_cfg, plaza_binding = make_house(tmp_path / "after", plaza=True)
    fixed_uuid = uuid.UUID("99999999-9999-4999-8999-999999999999")
    monkeypatch.setattr(events_module, "uuid4", lambda: fixed_uuid)
    monkeypatch.setattr(events_module, "utc_now_iso", lambda: "2026-09-20T12:00:00+00:00")

    baseline_event = build_inbound_event(purpose="unchanged", sender="outside", origin="external")
    plaza_enabled_event = build_inbound_event(
        purpose="unchanged", sender="outside", origin="external"
    )
    assert json.dumps(plaza_enabled_event) == json.dumps(baseline_event)
    assert baseline_event["origin"] == "external"

    event = build_inbound_event(
        purpose="run the same wake",
        sender="outside",
        event_id="11111111-1111-4111-8111-111111111111",
    )
    before_store = EventStore(unplaza_cfg.members["qwen"].events)
    after_store = EventStore(plaza_cfg.members["qwen"].events)
    before_store.append(dict(event))
    after_store.append(dict(event))

    class Session:
        _prior_states = []
        _bridge = None
        _state = {}

        def __init__(self):
            self.envelopes = []

        def exchange(self, envelope, **kwargs):
            self.envelopes.append(envelope)
            return "same response"

    before_session = Session()
    baseline = run_next_event(before_session, before_store, now=T0)
    after_session = Session()
    with_none = run_next_event(after_session, after_store, now=T0, extra_notes=None)
    assert json.dumps(with_none, sort_keys=True) == json.dumps(baseline, sort_keys=True)
    assert after_session.envelopes == before_session.envelopes


def test_invariant_9_enabled_wake_differs_only_by_supplied_plaza_note(tmp_path, monkeypatch):
    import hamutay.events as events_module

    root, cfg, binding = make_house(tmp_path, plaza=True)
    fixed_uuid = uuid.UUID("99999999-9999-4999-8999-999999999999")
    monkeypatch.setattr(events_module, "uuid4", lambda: fixed_uuid)
    monkeypatch.setattr(events_module, "utc_now_iso", lambda: "2026-09-20T12:00:00+00:00")
    event = build_inbound_event(
        purpose="ordinary wake",
        sender="outside",
        event_id="11111111-1111-4111-8111-111111111111",
    )
    plain_store = EventStore(root / "plain.events.jsonl")
    noted_store = EventStore(root / "noted.events.jsonl")
    plain_store.append(dict(event))
    noted_store.append(dict(event))

    class Session:
        _prior_states = []
        _bridge = None
        _state = {}

        def __init__(self):
            self.envelope = None

        def exchange(self, envelope, **kwargs):
            self.envelope = json.loads(envelope)
            return "same response"

    plain_session = Session()
    run_next_event(plain_session, plain_store, now=T0, extra_notes=None)
    noted_session = Session()
    run_next_event(
        noted_session,
        noted_store,
        now=T0,
        extra_notes=lambda event: ["plaza: the only added operational note"],
    )
    note = noted_session.envelope.pop("operational_notes")
    assert note == ["plaza: the only added operational note"]
    assert noted_session.envelope == plain_session.envelope


def test_invariant_6_member_event_shape_is_public_and_quiet_aware(house):
    from hamutay.assembly.ledger import Ledger
    from tests.plaza_validation.conftest import tool_send

    root, cfg, binding = house
    tool_send(cfg, text="quiet-aware")
    message = Ledger(cfg.plaza).read()[0]
    event = EventStore(cfg.members["elder"].events).read_records()[0]
    assert event["origin"] == "member"
    assert event["sender"] == "door:qwen"
    assert event["event_id"] == message["delivery"]["event_id"]
    assert event["defer_to_declared_quiet"] is True
    assert "expires_at" not in event
    assert "plaza seq 1" in event["purpose"]
