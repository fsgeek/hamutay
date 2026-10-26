"""Synthetic houses for the board tests: never a resident's real home."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

UTC = timezone.utc
T0 = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
DOORS = ("qwen", "elder", "fable")


def write_members(root: Path, guests=None) -> Path:
    plaza_dir = root / "community" / "plaza"
    plaza_dir.mkdir(parents=True, exist_ok=True)
    body = {"ledger": "community/plaza/assembly.jsonl",
            "members": {d: {"session": f"community/{d}/session.jsonl",
                            "events": f"community/{d}/session.jsonl.events.jsonl"} for d in DOORS},
            "plaza": "community/plaza/plaza.jsonl"}
    if guests is not None:
        body["guests"] = list(guests)
    p = plaza_dir / "members.json"
    p.write_text(json.dumps(body, indent=1))
    for d in DOORS:
        (root / "community" / d).mkdir(parents=True, exist_ok=True)
    return p


def enable(root: Path) -> Path:
    g = root / "community" / "board" / "board.enabled"
    g.parent.mkdir(parents=True, exist_ok=True)
    g.write_text("")
    return g


@pytest.fixture
def house(tmp_path):
    """(root, cfg, binding for qwen); the gate is NOT created."""
    from hamutay.assembly.binding import bind, load_members
    write_members(tmp_path, guests=["levadura"])
    cfg = load_members(tmp_path)
    binding, note = bind(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)
    assert binding is not None, note
    return tmp_path, cfg, binding


@pytest.fixture
def on(house):
    enable(house[0])
    return house


class Session:
    """A stand-in session: records each envelope; optionally raises."""

    def __init__(self, fail: Exception | None = None):
        self._prior_states = [(1, uuid.uuid4(), {}, T0.isoformat())]
        self._bridge = None
        self._state = {}
        self.cycle = 1
        self.fail = fail
        self.envelopes: list[dict] = []

    def exchange(self, envelope, **kw):
        self.envelopes.append(json.loads(envelope))
        if self.fail is not None:
            raise self.fail
        self.cycle += 1
        self._prior_states.append((self.cycle, uuid.uuid4(), {}, T0.isoformat()))
        return "ok"


def post(root, n=0, *, by="tony", kind="review", tags=None, title=None, what=None, now=T0, **kw):
    from hamutay.board.write import post_opening
    return post_opening(root, by=by, title=title or f"Opening {n}", what=what or f"Please look at thing {n}.",
                        kind=kind, tags=tags or [], now=now, **kw)
