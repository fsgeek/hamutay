"""Independent wire fixtures. Only documented board entry points are invoked."""
from datetime import datetime, timedelta, timezone
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from hamutay.assembly.binding import bind
from hamutay.events import EventStore, run_next_event, summarize_event_log

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
NS_BOARD = UUID("e095e4d0-cfce-5dc7-86c8-4e7a231df71b")
KINDS = ["review", "design", "build", "analysis", "writing", "testimony", "other"]
FILTER = {"kinds": ["review"], "tags_any": [], "owners_any": [], "keywords_any": []}
TOOLS = {"board_read", "board_post", "set_board_filter", "clear_board_filter", "board_pass"}


def event_id(door, seq, generation=1, attempt=1):
    return str(uuid5(NS_BOARD, f"{door}:{seq}:g{generation}:a{attempt}"))


def opening(seq=1, **changes):
    r = dict(record_type="opening", seq=seq, created_at=NOW.isoformat(),
             opportunity_id=str(uuid4()), posted_by="tony", posted_at=NOW.isoformat(),
             title=f"Draft {seq}", what="Review a draft of the memory paper.", why="Useful evidence",
             help_wanted="Read and respond", kind="review", tags=["memory"],
             owner="tony", record_of_help="A public note")
    return {**r, **changes}


def update(entry, seq, record_type="note", **changes):
    r = dict(record_type=record_type, seq=seq, created_at=NOW.isoformat(),
             opportunity_id=entry["opportunity_id"], by=entry["owner"])
    r.update({"text": f"New evidence {seq}"} if record_type == "note"
             else {"status": "taken", "reason": "Work started"})
    return {**r, **changes}


def board_event(root, row, *, door="alpha", generation=1, attempt=1):
    return dict(record_type="event_status", event_id=event_id(door, row["seq"], generation, attempt),
                event_type="board_match", status="pending", created_at=NOW.isoformat(),
                origin="board", sender="board", purpose="A matching board entry",
                defer_to_declared_quiet=True,
                board=dict(door=door, board_seq=row["seq"], record_type=row["record_type"],
                           opportunity_id=row["opportunity_id"], generation=generation,
                           attempt=attempt, clause={"kinds": ["review"]} if row["record_type"] == "opening" else None,
                           gate=str(root / "community/board/board.enabled"),
                           board_file=str(root / "community/board/board.jsonl")))


def bytes_at(path):
    return path.read_bytes() if path.exists() else b""


class Session:
    """Minimal existing run_next_event session protocol, with no inference."""
    def __init__(self, failure=False, during=None):
        self._prior_states = []
        self._bridge = None
        self._state = {}
        self.cycle = 0
        self.messages = []
        self.contexts = []
        self.failure = failure
        self.during = during

    def exchange(self, message, **kwargs):
        self.messages.append(json.loads(message))
        self.contexts.append(kwargs["wake_context"])
        if self.during:
            self.during()
        if self.failure:
            raise RuntimeError("synthetic board wake failure")
        self.cycle += 1
        self._prior_states.append((self.cycle, uuid4(), {}, "validation"))
        return "Synthetic board response"


class House:
    def __init__(self, root):
        self.root = root.resolve()
        self.root.mkdir(parents=True)
        self.board = self.root / "community/board/board.jsonl"
        self.gate = self.board.with_name("board.enabled")
        self.gate.parent.mkdir(parents=True)
        self.gate.write_text("enabled; contents intentionally meaningless\n")
        self.config = {
            "ledger": "community/assembly/ledger.jsonl",
            "plaza": "community/plaza/plaza.jsonl", "guests": ["visitor"],
            "members": {door: {"session": f"scratch/{door}/session.jsonl",
                                "events": f"scratch/{door}/events.jsonl"}
                        for door in ("alpha", "beta")}}
        self.members = self.root / "community/plaza/members.json"
        self.members.parent.mkdir(parents=True)
        self.members.write_text(json.dumps(self.config))
        self.bindings = {}
        self.stores = {}
        for door in self.config["members"]:
            session = self.root / self.config["members"][door]["session"]
            events = self.root / self.config["members"][door]["events"]
            binding, note = bind(self.root, session, events)
            assert binding is not None, note
            self.bindings[door] = binding
            self.stores[door] = EventStore(events)
        self.store = self.stores["alpha"]

    def seed(self, rows):
        self.board.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        return rows

    def many(self, count, **changes):
        return self.seed([opening(i + 1, posted_by=f"door:poster{i // 5}", **changes)
                          for i in range(count)])

    def rows(self):
        return [json.loads(s) for s in self.board.read_text().splitlines()] if self.board.exists() else []

    def filter(self, value=FILTER, *, door="alpha", generation=1):
        self.stores[door].append(dict(record_type="board_filter", door=door,
            generation=generation, filter=value, recorded_at=NOW.isoformat()))

    def notice_done(self, door="alpha"):
        """A completed documented onboarding notice, to isolate board delivery."""
        eid = str(uuid5(NS_BOARD, f"{door}:onboarding"))
        self.stores[door].append_many([
            dict(record_type="event_status", event_id=eid, event_type="inbound_message",
                 status="pending", created_at=(NOW - timedelta(days=1)).isoformat(),
                 origin="board", sender="board", label="board:onboarding", purpose="Board notice",
                 defer_to_declared_quiet=True),
            dict(record_type="event_status", event_id=eid, event_type="inbound_message",
                 status="completed", run_id=str(uuid4()), wake_cycle=1,
                 result_record_id=str(uuid4()), response_text="Notice read",
                 completed_at=(NOW - timedelta(days=1)).isoformat())])

    def queue(self, rows=None, *, door="alpha", generation=1, attempt=1):
        for r in rows if rows is not None else self.rows():
            self.stores[door].append(board_event(self.root, r, door=door,
                                               generation=generation, attempt=attempt))

    def pass_(self, *, door="alpha", now=NOW, memo=None):
        module = importlib.import_module("hamutay.board.pass_")
        return module.run_board_pass(door=door, project_root=self.root,
                                    store=self.stores[door], now=now, memo=memo)

    def tool(self, name, data=None, *, door="alpha", now=NOW):
        module = importlib.import_module("hamutay.board.tools")
        return module.run_board_tool(name, data or {}, binding=self.bindings[door], now=now)

    def post(self, **data):
        return self.tool("board_post", {"title": "A draft", "what": "Review a draft", "kind": "review", **data})

    def cli(self, *args):
        env = dict(os.environ)
        source = Path(__file__).resolve().parents[2] / "src"
        env["PYTHONPATH"] = str(source) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run([sys.executable, "-m", "hamutay.board", "--project-root",
                               str(self.root), *map(str, args)], cwd=self.root, env=env,
                              capture_output=True, text=True, timeout=20)

    def cli_json(self, *args):
        result = self.cli(*args)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def matches(self, door="alpha", status=None):
        rows = self.stores[door].read_records()
        originals = {r["event_id"]: r for r in rows if r.get("event_type") == "board_match"
                     and r.get("status") == "pending"}
        latest = self.stores[door].latest_by_event_id()
        return [r for eid, r in originals.items()
                if status is None or latest[eid].get("status") == status]

    def run(self, session=None, *, door="alpha", now=NOW):
        session = session or Session()
        result = run_next_event(session, self.stores[door], now=now)
        return result, session

    def summary(self, now=NOW):
        return summarize_event_log(self.store.read_records(), now=now, door="alpha")

    def snapshot(self):
        # Only these public fixture-owned files; never real homes.
        return (bytes_at(self.board), *(bytes_at(s.path) for s in self.stores.values()))


def ok(result):
    assert "error" not in result, result
    return result


def refused(house, name, data):
    before = house.snapshot()
    result = house.tool(name, data)
    assert isinstance(result.get("error"), str) and result["error"].startswith(name + ":"), result
    assert house.snapshot() == before
    return result
