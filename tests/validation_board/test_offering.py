"""§2: observe the real session's offered tools and system prompt pre-inference."""
import json
from uuid import uuid4

import pytest

from hamutay import heartbeat
from hamutay.events import WakeContext
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import BOARD_CONSTITUTION_CLAUSE
from hamutay.taste_open import OpenAITasteBackend

from .support import NOW, TOOLS


class ProbeStop(BaseException):
    """Stop before inference; intentionally bypass ordinary retry handlers."""


class CaptureBackend(OpenAITasteBackend):
    def call(self, *args, **kwargs):
        self.captured = kwargs
        raise ProbeStop()

    def call_terminal_surface(self, *args, **kwargs):
        self.captured = kwargs
        raise ProbeStop()


def session_for(house, monkeypatch, *, mode="natural"):
    from hamutay import taste_open
    from hamutay.context_policy import ContextPolicy
    monkeypatch.setattr(taste_open, "OpenAITasteBackend", CaptureBackend)
    # Unrelated model capability/persistence/window discovery is replaced;
    # actual session setup, binding, tool selection and prompts remain real.
    monkeypatch.setattr(heartbeat, "load_capability_profile", lambda *a: (None, "synthetic"))
    monkeypatch.setattr(heartbeat, "resolve_context_limit", lambda *a, **k: (None, "provider default"))
    monkeypatch.setattr(heartbeat, "resolve_persistence", lambda *a, **k: (None, "no persistence"))
    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(lambda cls, *a, **k: cls.none()))
    member = house.config["members"]["alpha"]
    args = heartbeat.build_parser().parse_args([
        "--project-root", str(house.root), "--log-path", str(house.root / member["session"]),
        "--event-log-path", str(house.root / member["events"]), "--model", "synthetic",
        "--provider", "openai", "--api-key", "synthetic-not-a-secret", "--base-url", "http://board.invalid/v1",
        "--wake-mode", mode, "--no-daily-budget"])
    session, backend, _ = heartbeat.build_session(args)
    return session, backend


def capture(session, backend, *, managed=True, context=True):
    event = {"event_id": str(uuid4()), "event_type": "inbound_message", "origin": "external"}
    ctx = WakeContext(event["event_id"], str(uuid4()), NOW.isoformat(), event) if context else None
    with pytest.raises(ProbeStop):
        session.exchange("A synthetic tool offering probe", event_managed=managed, wake_context=ctx)
    payload = backend.captured
    tools = payload.get("extra_tools") or []
    names = {t.get("name") or t.get("function", {}).get("name") for t in tools}
    return names, payload["system"]


@pytest.mark.parametrize("missing", [None, "gate", "natural", "managed", "context", "binding", "plaza"])
def test_tools_follow_send_message_prerequisites(house, monkeypatch, missing):
    if missing == "gate":
        house.gate.unlink()
    if missing == "binding":
        house.config["members"].pop("alpha")
        # Preserve path arguments for the unbound session.
        paths = {"session": "scratch/alpha/session.jsonl", "events": "scratch/alpha/events.jsonl"}
        house.members.write_text(json.dumps(house.config))
        house.config["members"]["alpha"] = paths
    elif missing == "plaza":
        house.config.pop("plaza")
        house.members.write_text(json.dumps(house.config))
    session, backend = session_for(house, monkeypatch, mode="terminal" if missing == "natural" else "natural")
    names, prompt = capture(session, backend, managed=missing != "managed", context=missing != "context")
    eligible = missing is None
    assert ("send_message" in names) == (missing not in ("natural", "managed", "context", "binding", "plaza"))
    assert names & TOOLS == (TOOLS if eligible else set())
    if eligible:
        assert "board" in prompt.lower()
    else:
        assert not any(name in prompt for name in TOOLS)


def test_dormant_constitution_has_no_board_text(house):
    house.gate.unlink()
    prefix = heartbeat.build_constitution(None, assembly=True, plaza=True, guests=True)
    assert heartbeat.ASSEMBLY_CONSTITUTION_CLAUSE in prefix
    assert heartbeat.PLAZA_CONSTITUTION_CLAUSE in prefix
    assert heartbeat.GUESTS_CONSTITUTION_SENTENCE in prefix
    assert BOARD_CONSTITUTION_CLAUSE not in prefix
    assert "opportunities board" not in prefix.lower()
    assert "community/board/" not in prefix
    assert not any(name in prefix for name in TOOLS)


@pytest.mark.parametrize("guests", [True, False])
def test_exchange_gate_toggle_restores_prompt(house, monkeypatch, guests):
    if not guests:
        house.config.pop("guests")
        house.members.write_text(json.dumps(house.config))
    house.gate.unlink()
    session, backend = session_for(house, monkeypatch)
    absent_names, absent_prompt = capture(session, backend)
    assert not (TOOLS & absent_names)
    house.gate.touch()
    enabled_names, enabled_prompt = capture(session, backend)
    assert TOOLS <= enabled_names
    assert enabled_prompt != absent_prompt
    # The board clause is immediately after the existing plaza + guests clause.
    anchor = heartbeat.PLAZA_CONSTITUTION_CLAUSE + (heartbeat.GUESTS_CONSTITUTION_SENTENCE if guests else "")
    assert anchor in absent_prompt and anchor in enabled_prompt
    before_anchor, after_anchor = absent_prompt.split(anchor, 1)
    assert enabled_prompt.startswith(before_anchor + anchor)
    insertion = enabled_prompt[len(before_anchor + anchor):]
    assert insertion != after_anchor
    # The unchanged following constitution sentence must follow the board clause.
    next_sentence = after_anchor.lstrip().split(".", 1)[0]
    assert insertion.find("board") < insertion.find(next_sentence)
    house.gate.unlink()
    final_names, final_prompt = capture(session, backend)
    assert final_names & TOOLS == set()
    assert final_prompt == absent_prompt


@pytest.mark.parametrize("name", sorted(TOOLS))
@pytest.mark.parametrize("board", [False, True])
def test_executor_requires_explicit_board_enablement(house, name, board):
    if board:
        # Direct executor must also check the live house gate.
        house.gate.unlink()
    event = {"event_id": str(uuid4()), "event_type": "inbound_message"}
    ctx = WakeContext(event["event_id"], str(uuid4()), NOW.isoformat(), event)
    executor = ToolExecutor(project_root=house.root, cycle=1,
        assembly=house.bindings["alpha"], wake_context=ctx, board=board)
    before = house.snapshot()
    result = executor.execute(name, {})
    if isinstance(result, str):
        result = json.loads(result)
    assert "error" in result
    assert house.snapshot() == before


def test_full_dormant_system_prompt_is_preboard_baseline(house, monkeypatch):
    house.gate.unlink()
    session, backend = session_for(house, monkeypatch)
    names, prompt = capture(session, backend)
    assert "send_message" in names
    assert not (names & TOOLS)

    # Use the same house/session to hold every non-board input fixed. Derive
    # today's pre-board baseline by removing only the two board additions
    # observed at the public backend boundary, rather than freezing all prose.
    house.gate.touch()
    enabled_names, enabled_prompt = capture(session, backend)
    assert TOOLS <= enabled_names
    assert enabled_prompt.count(BOARD_CONSTITUTION_CLAUSE) == 1
    guidance_lines = [line for line in enabled_prompt.splitlines(keepends=True)
                      if line.startswith("- ") and all(name in line for name in TOOLS)]
    assert len(guidance_lines) == 1
    guidance = guidance_lines[0]
    assert enabled_prompt.count(guidance) == 1
    baseline = enabled_prompt.replace(BOARD_CONSTITUTION_CLAUSE, "", 1).replace(guidance, "", 1)

    # Independent negatives keep the comparison honest even if board text
    # leaks into shared prompt construction used by both captures.
    assert BOARD_CONSTITUTION_CLAUSE not in prompt
    assert guidance not in prompt
    assert "opportunities board" not in prompt.lower()
    assert "community/board/" not in prompt
    assert not any(name in prompt for name in TOOLS)
    assert prompt.encode("utf-8") == baseline.encode("utf-8")


def test_enabled_executor_dispatches_bound_writer(house):
    event = {"event_id": str(uuid4()), "event_type": "inbound_message"}
    ctx = WakeContext(event["event_id"], str(uuid4()), NOW.isoformat(), event)
    # §0 r1: binding and wake context suffice; no scheduled_by_record_id is needed.
    executor = ToolExecutor(project_root=house.root, cycle=1,
        assembly=house.bindings["alpha"], wake_context=ctx, board=True)
    result = executor.execute("board_post", {"title": "Executor post", "what": "Read it", "kind": "review"})
    if isinstance(result, str):
        result = json.loads(result)
    assert "error" not in result and result["posted"] is True
    assert house.rows()[0]["posted_by"] == house.rows()[0]["owner"] == "door:alpha"
