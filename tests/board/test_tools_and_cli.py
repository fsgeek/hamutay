import json
import uuid

from hamutay.board.cli import main as board_main
from hamutay.board.filters import current_filter
from hamutay.board.ids import board_path
from hamutay.board.tools import run_board_tool
from hamutay.events import EventStore, WakeContext
from hamutay.heartbeat import HeartbeatLoop
from hamutay.taste_open import _build_messages
from hamutay.tools import ToolExecutor
from hamutay.tools.executor import _CAPABILITY
from hamutay.tools.schemas import (BOARD_CONSTITUTION_CLAUSE, BOARD_TOOL_SCHEMAS, GUESTS_CONSTITUTION_SENTENCE,
                                   PLAZA_CONSTITUTION_CLAUSE)

from .conftest import T0, enable, post

BOARD_TOOLS = {"board_read", "board_post", "set_board_filter", "clear_board_filter", "board_pass"}


def _wake():
    return WakeContext(event_id=str(uuid.uuid4()), run_id=str(uuid.uuid4()), started_at=T0.isoformat(), event={})


def test_schemas_and_capabilities():
    assert {s["name"] for s in BOARD_TOOL_SCHEMAS} == BOARD_TOOLS
    assert _CAPABILITY["board_read"] == "read_only"
    assert all(_CAPABILITY[n] == "bounded_write" for n in BOARD_TOOLS - {"board_read"})


def test_tools_refuse_while_dormant(house):
    root, cfg, binding = house
    assert "not enabled" in run_board_tool("board_read", {}, binding=binding)["error"]
    ex = ToolExecutor(project_root=root, cycle=2, scheduled_by_record_id=uuid.uuid4(), wake_context=_wake(),
                      assembly=binding, board=False)
    assert "not offered" in ex.execute("board_read", {})["error"]


def test_tools_write_with_the_bindings_identity(on):
    root, cfg, binding = on
    ex = ToolExecutor(project_root=root, cycle=2, scheduled_by_record_id=uuid.uuid4(), wake_context=_wake(),
                      assembly=binding, board=True)
    r = ex.execute("board_post", {"title": "Help me", "what": "a thing", "kind": "build", "posted_by": "tony"})
    assert r["seq"] == 1
    rec = json.loads(board_path(root).read_text())
    assert rec["posted_by"] == "door:qwen" and rec["owner"] == "door:qwen"
    n = ex.execute("board_post", {"record_type": "note", "opportunity_id": r["opportunity_id"], "text": "more"})
    assert n["seq"] == 2
    s = ex.execute("board_post", {"record_type": "status", "opportunity_id": r["opportunity_id"],
                                  "status": "taken", "reason": "elder took it"})
    assert s["seq"] == 3
    got = ex.execute("board_read", {"opportunity_id": r["opportunity_id"]})["entries"][0]
    assert got["status"] == "taken" and got["notes"][0]["text"] == "more"
    post(root, 1, title="Read the draft")             # tony's: matches at once
    f = ex.execute("set_board_filter", {"kinds": ["REVIEW"], "keywords_any": ["Draft"]})
    assert f == {"generation": 1, "filter": {"kinds": ["review"], "tags_any": [], "owners_any": [],
                                             "keywords_any": ["draft"]}, "queued_now": 1}
    assert "error" in ex.execute("set_board_filter", {"keywords_any": [""]})
    assert "error" in ex.execute("set_board_filter", {"colour": ["red"]})
    assert current_filter(EventStore(cfg.members["qwen"].events).read_records())[0] == 1
    assert ex.execute("board_pass", {"opportunity_id": r["opportunity_id"]})["passed"] is True
    assert ex.execute("clear_board_filter", {})["generation"] == 2


def test_clause_and_guidance_only_with_the_board_and_prefix_unchanged_without():
    prefix = "X " + PLAZA_CONSTITUTION_CLAUSE + GUESTS_CONSTITUTION_SENTENCE + "ZZEND"
    kw = dict(tools_enabled=True, wake_mode="natural", declare_quiet=True, assembly=True, plaza=True)
    _, without = _build_messages({}, "u", 2, system_prefix=prefix, **kw)
    _, with_ = _build_messages({}, "u", 2, system_prefix=prefix, board=True, **kw)
    assert BOARD_CONSTITUTION_CLAUSE not in without and "board_post" not in without
    assert with_.count(BOARD_CONSTITUTION_CLAUSE) == 1 and "board_read, board_post" in with_
    assert with_.index(GUESTS_CONSTITUTION_SENTENCE) < with_.index(BOARD_CONSTITUTION_CLAUSE)
    assert prefix in without and prefix.replace("ZZEND", BOARD_CONSTITUTION_CLAUSE + "ZZEND") in with_


def test_session_offers_board_tools_only_with_the_gate(house):
    from hamutay.taste_open import ExchangeResult, OpenAITasteBackend, OpenTasteSession
    root, cfg, binding = house
    seen = {}

    class B(OpenAITasteBackend):
        def call(self, *, extra_tools=None, system="", **kw):
            seen["tools"] = {t["name"] for t in (extra_tools or [])}
            seen["system"] = system
            return ExchangeResult(raw_output={"response": "ok"}, stop_reason="end_turn",
                                  input_tokens=1, output_tokens=1)

    s = OpenTasteSession(model="m", backend=B(api_key="k", wake_mode="natural"),
                         log_path=str(root / "community" / "qwen" / "session.jsonl"),
                         event_log_path=str(cfg.members["qwen"].events), enable_tools=True, project_root=root,
                         wake_mode="natural", assembly=binding, system_prompt_prefix="C. " + PLAZA_CONSTITUTION_CLAUSE)
    s.exchange("hi", event_managed=True, wake_context=_wake())
    assert not (seen["tools"] & BOARD_TOOLS) and BOARD_CONSTITUTION_CLAUSE not in seen["system"]
    enable(root)
    s.exchange("hi", event_managed=True, wake_context=_wake())
    assert BOARD_TOOLS <= seen["tools"] and BOARD_CONSTITUTION_CLAUSE in seen["system"]


def test_heartbeat_step_runs_the_board_pass_and_survives_its_errors(on, capsys):
    root, cfg, binding = on
    st = EventStore(cfg.members["qwen"].events)
    calls = []

    def fake(**kw):
        calls.append(kw["door"])
        raise RuntimeError("boom")

    class Stub:
        def exchange(self, *a, **k):
            return "ok"

    noop = lambda *a, **k: ({"skipped": True}, None)  # noqa: E731
    loop = HeartbeatLoop(Stub(), st, poll_interval=1.0, sleep=lambda s: None, now=lambda: T0, assembly=binding,
                         assembly_pass=noop, plaza_pass=noop, board_pass=fake)
    loop.step()
    assert calls == ["qwen"] and '"heartbeat": "board", "error": "RuntimeError: boom"' in capsys.readouterr().out


def test_cli_post_note_status_read(house, capsys):
    root = house[0]
    rc = board_main(["--project-root", str(root), "post", "--by", "tony", "--title", "T", "--what", "W",
                     "--kind", "design", "--tags", "A,b"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["tags"] == ["a", "b"] and "dormant" in out["note"]
    oid = out["opportunity_id"]
    assert board_main(["--project-root", str(root), "note", "--by", "custodian", "--id", oid, "--text", "x"]) == 2
    assert "owner" in capsys.readouterr().err
    assert board_main(["--project-root", str(root), "status", "--by", "tony", "--id", oid,
                       "--status", "closed", "--reason", "done"]) == 0
    capsys.readouterr()
    assert board_main(["--project-root", str(root), "read", "--all"]) == 0
    got = json.loads(capsys.readouterr().out)
    assert got["entries"][0]["status"] == "closed" and got["enabled"] is False
    assert board_main(["--project-root", str(root), "post", "--by", "door:qwen", "--title", "T", "--what", "W",
                       "--kind", "design"]) == 2  # doors write through their tool, as on the plaza
    assert "door" in capsys.readouterr().err
