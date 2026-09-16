from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pytest

from hamutay.assembly.binding import AssemblyBinding, MembersConfig, bind, load_members
from hamutay.assembly.convene import convene
from hamutay.assembly.ledger import Ledger
from hamutay.assembly.outbox import run_outbox
from hamutay.assembly.position import record_position
from hamutay.assembly.records import reduce
from hamutay.events import EventStore, WakeContext


T0 = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
DOORS = ("north", "east", "south", "west")


@dataclass(frozen=True)
class House:
    root: Path
    ledger: Ledger
    members: MembersConfig
    bindings: dict[str, AssemblyBinding]

    def store(self, door: str) -> EventStore:
        return EventStore(self.members.members[door].events)


def member_document(*, event_overrides: dict[str, str] | None = None) -> dict:
    event_overrides = event_overrides or {}
    return {
        "ledger": "community/plaza/assembly.jsonl",
        "members": {
            door: {
                "session": f"community/{door}/session.jsonl",
                "events": event_overrides.get(
                    door, f"community/{door}/session.jsonl.events.jsonl"
                ),
            }
            for door in DOORS
        },
    }


def write_members(root: Path, document: dict) -> None:
    plaza = root / "community" / "plaza"
    plaza.mkdir(parents=True, exist_ok=True)
    (plaza / "members.json").write_text(json.dumps(document) + "\n")


def make_house(root: Path) -> House:
    write_members(root, member_document())
    members = load_members(root)
    assert members is not None
    bindings: dict[str, AssemblyBinding] = {}
    for door, member in members.members.items():
        member.session.parent.mkdir(parents=True, exist_ok=True)
        binding, note = bind(root, member.session, member.events)
        assert binding is not None, note
        bindings[door] = binding
    return House(root=root, ledger=Ledger(members.ledger), members=members, bindings=bindings)


@pytest.fixture
def house_factory(tmp_path: Path) -> Callable[[str], House]:
    def factory(name: str) -> House:
        return make_house(tmp_path / name)

    return factory


@pytest.fixture
def house(house_factory: Callable[[str], House]) -> House:
    return house_factory("house")


def convene_question(
    house: House,
    *,
    now: datetime = T0,
    convener: str = "custodian",
    closes_in: timedelta = timedelta(days=1),
    text: str = "Shall the house adopt this proposal?",
) -> dict:
    payload = {
        "rule": "consent-v0",
        "max_rounds": 3,
        "quorum": "ceil(half)",
        "scope": ["house affairs"],
        "operations": ["maintenance"],
        "members_counted": "natural_doors",
        "humans": "testimony",
    }
    artifact = {
        "path": "docs/assembly-proposal.md",
        "commit": "a" * 40,
        "sha256": "b" * 64,
    }
    return convene(
        house.ledger,
        house.members,
        convener=convener,
        text=text,
        closes_in=closes_in,
        now=now,
        proposal_procedure=payload,
        artifact=artifact,
    )


def land_outbox(house: House, *, now: datetime = T0) -> list[dict]:
    with house.ledger.locked():
        view = reduce(house.ledger.read_unlocked())
        return run_outbox(house.ledger, view, now=now)


def claim(house: House, door: str, *, now: datetime = T0) -> tuple[dict, dict]:
    claimed = house.store(door).claim_next_pending(now=now)
    assert claimed is not None
    return claimed


def complete(
    house: House,
    door: str,
    event: dict,
    running: dict,
    *,
    record_id: str | None = None,
    cycle: int = 1,
) -> str:
    record_id = record_id or str(uuid4())
    house.store(door).append_completed(
        event=event,
        run_id=running["run_id"],
        wake_cycle=cycle,
        result_record_id=record_id,
        response_text="completed",
    )
    return record_id


def take_and_complete(
    house: House,
    q: dict,
    door: str,
    stance: str,
    *,
    now: datetime = T0,
    cycle: int = 1,
    reasons: str | None = None,
) -> dict:
    event, running = claim(house, door, now=now)
    record_id = str(uuid4())
    wake = WakeContext(
        event_id=event["event_id"],
        run_id=running["run_id"],
        started_at=running["started_at"],
        event=event,
    )
    position = record_position(
        house.ledger,
        binding=house.bindings[door],
        wake=wake,
        cycle=cycle,
        record_id=record_id,
        question_id=q["question_id"],
        stance=stance,
        reasons=reasons,
        now=now,
    )
    complete(house, door, event, running, record_id=record_id, cycle=cycle)
    return position


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, separators=(",", ":"), default=str) + "\n")
