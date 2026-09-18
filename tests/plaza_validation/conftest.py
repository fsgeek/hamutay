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
    body = {
        "ledger": "community/plaza/assembly.jsonl",
        "members": {
            door: {
                "session": f"community/{door}/session.jsonl",
                "events": f"community/{door}/session.jsonl.events.jsonl",
            }
            for door in DOORS
        },
    }
    if plaza:
        body["plaza"] = "community/plaza/plaza.jsonl"
    path = plaza_dir / "members.json"
    path.write_text(json.dumps(body, indent=1))
    for door in DOORS:
        (root / "community" / door).mkdir(parents=True, exist_ok=True)
    return path


def make_house(root: Path, *, plaza: bool, door: str = "qwen"):
    from hamutay.assembly.binding import bind, load_members

    write_members(root, plaza=plaza)
    cfg = load_members(root)
    assert cfg is not None
    binding, note = bind(root, cfg.members[door].session, cfg.members[door].events)
    assert binding is not None, note
    return root, cfg, binding


@pytest.fixture
def house(tmp_path):
    return make_house(tmp_path, plaza=True)


@pytest.fixture
def house_unplaza(tmp_path):
    return make_house(tmp_path, plaza=False)


def wake(event_id: str, *, started_at: datetime = T0, run: str | None = None) -> dict:
    from hamutay.assembly.ledger import iso

    return {
        "cycle": 7,
        "record_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "event_id": event_id,
        "run_id": run or "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "started_at": iso(started_at),
    }


def tool_send(cfg, *, actor="door:qwen", to="elder", text="hello", now=T0,
              event_id="11111111-1111-4111-8111-111111111111", **kwargs):
    from hamutay.plaza.send import send

    return send(
        cfg,
        actor=actor,
        via="tool",
        to=to,
        text=text,
        now=now,
        wake=wake(event_id),
        **kwargs,
    )
