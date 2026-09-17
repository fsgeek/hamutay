import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
DOORS = ("qwen", "elder", "fable")


def write_members(root: Path, *, plaza: bool) -> Path:
    plaza_dir = root / "community" / "plaza"
    plaza_dir.mkdir(parents=True, exist_ok=True)
    body = {"ledger": "community/plaza/assembly.jsonl",
            "members": {d: {"session": f"community/{d}/session.jsonl",
                            "events": f"community/{d}/session.jsonl.events.jsonl"} for d in DOORS}}
    if plaza:
        body["plaza"] = "community/plaza/plaza.jsonl"
    p = plaza_dir / "members.json"
    p.write_text(json.dumps(body, indent=1))
    for d in DOORS:
        (root / "community" / d).mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
def house(tmp_path):
    """A root with three doors and the plaza key set; returns (root, cfg, binding for qwen)."""
    from hamutay.assembly.binding import bind, load_members
    write_members(tmp_path, plaza=True)
    cfg = load_members(tmp_path)
    binding, note = bind(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)
    assert binding is not None, note
    return tmp_path, cfg, binding


@pytest.fixture
def house_unplaza(tmp_path):
    from hamutay.assembly.binding import bind, load_members
    write_members(tmp_path, plaza=False)
    cfg = load_members(tmp_path)
    binding, note = bind(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)
    assert binding is not None, note
    return tmp_path, cfg, binding
