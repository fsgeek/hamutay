import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

from hamutay.assembly.binding import load_members
from hamutay.plaza.ids import delivery_event_id

NOW = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
STAMP = NOW.isoformat()
DOORS = ("qwen", "elder", "fable")
SECRETS = (
    "PRIVATE-SESSION-SENTINEL",
    "PRIVATE-AUTHORED-STATE-SENTINEL",
    "PRIVATE-RAW-OUTPUT-SENTINEL",
    "PRIVATE-EVENT-RESPONSE-SENTINEL",
    "PRIVATE-BILLING-RAW-SENTINEL",
)


def write_jsonl(path, records):
    path.write_bytes(b"".join(json.dumps(row).encode() + b"\n" for row in records))


def event(event_id, status, **fields):
    row = {"record_type": "event_status", "event_id": event_id,
           "event_type": "inbound", "status": status, "run_id": f"run-{event_id}",
           "created_at": STAMP, "sender": "guest:levadura", "purpose": "Public knock"}
    if status in ("completed", "failed"):
        row[f"{status}_at"] = STAMP
    row.update(fields)
    return row


def message(seq, *, to="plaza", text="Public plaza post", cfg=None):
    mid = str(uuid4())
    delivery = None
    if to != "plaza":
        door = to.removeprefix("door:")
        delivery = {"door": door, "events_path": str(cfg.members[door].events),
                    "event_id": delivery_event_id(mid, door), "members_digest": cfg.digest}
    return {"record_type": "message", "seq": seq, "created_at": STAMP,
            "message_id": mid, "idempotency_key": str(uuid5(NAMESPACE_URL, mid)),
            "from": "guest:levadura", "via": "cli", "to": to, "text": text,
            "sent_at": STAMP, "delivery": delivery, "wake": None}


def question(qid="question-1", seq=1):
    return {"record_type": "question", "question_id": qid, "lineage_id": qid,
            "seq": seq, "created_at": STAMP, "round": 1, "convener": "tony",
            "text": "Public assembly question\nSecond public line",
            "opened_at": STAMP, "closes_at": (NOW + timedelta(days=1)).isoformat(),
            "proposal": {"kind": "action", "sha256": "a" * 64},
            "governing": {"max_rounds": 3}, "members": {d: {} for d in DOORS}}


def closing(qid="question-1", **fields):
    row = {"record_type": "closing", "question_id": qid, "lineage_id": "question-1",
           "closing_id": f"closing-{qid}", "seq": 5, "created_at": STAMP,
           "outcome": "assented", "closed_at": STAMP, "closed_by": "custodian",
           "absent": [], "next_question": None}
    row.update(fields)
    return row


@dataclass
class Community:
    root: Path
    cfg: object
    plaza_records: list
    assembly_records: list
    private_files: set

    def events(self, name="qwen"):
        return self.cfg.members[name].events

    def billing(self, name="qwen"):
        return Path(str(self.cfg.members[name].session) + ".billing.jsonl")


@pytest.fixture
def community(tmp_path):
    plaza_dir = tmp_path / "community" / "plaza"
    plaza_dir.mkdir(parents=True)
    config = {"ledger": "community/plaza/assembly.jsonl", "plaza": "community/plaza/plaza.jsonl",
              "guests": ["levadura", "visitor-two"],
              "members": {d: {"session": f"community/{d}/session.jsonl",
                              "events": f"community/{d}/session.jsonl.events.jsonl"} for d in DOORS}}
    (plaza_dir / "members.json").write_text(json.dumps(config))
    for d in DOORS:
        (tmp_path / "community" / d).mkdir()
    cfg = load_members(tmp_path)
    private = set()
    for member in cfg.members.values():
        for path, secret in ((member.session, SECRETS[0]),
                             (member.session.parent / "state.json", SECRETS[1]),
                             (member.session.parent / "raw-output.txt", SECRETS[2])):
            path.write_text(secret)
            private.add(path)
        write_jsonl(member.events, [])
    post = message(1)
    knock = message(2, to="door:elder", text="Public directed message", cfg=cfg)
    delivered = {"record_type": "delivery", "seq": 3, "created_at": STAMP,
                 "message_id": knock["message_id"], "door": "elder",
                 "event_id": knock["delivery"]["event_id"], "state": "landed",
                 "landed_at": STAMP, "detail": None}
    rows = [post, knock, delivered]
    write_jsonl(cfg.plaza, rows)
    assembly = [question(),
                {"record_type": "position", "question_id": "question-1", "seq": 2,
                 "member": "door:qwen", "stance": "assent", "reasons": "Public position reasons",
                 "cycle": 1, "created_at": STAMP},
                {"record_type": "testimony", "question_id": "question-1", "seq": 3,
                 "by": "tony", "text": "Public testimony body", "created_at": STAMP},
                closing(),
                {"record_type": "execution", "question_id": "question-1", "seq": 6,
                 "by": "custodian", "outcome": "done", "what": "Public execution details",
                 "created_at": STAMP}]
    write_jsonl(cfg.ledger, assembly)
    write_jsonl(cfg.members["qwen"].events, [
        event("failed", "failed", error_type="RuntimeError", error="Public failure details",
              response_text=SECRETS[3]),
        event("finished", "completed", wake_cycle=1, result_record_id="completed-cycle-record",
              response_text=SECRETS[3],
              authored_state=SECRETS[1], raw_output=SECRETS[2],
              context_results={"response_text": SECRETS[3]}),
        event("waiting", "pending"),
        event("awake", "pending"), event("awake", "running", started_at=STAMP),
        {"record_type": "heartbeat_status", "status": "resting", "reason": "quiet_hours",
         "created_at": STAMP, "response_text": SECRETS[3], "detail": {"raw": SECRETS[2]}},
        {"record_type": "quiet_declaration", "reason": "Public quiet reason",
         "until": (NOW + timedelta(days=1)).isoformat(), "created_at": STAMP,
         "declared_by_cycle": 1, "declared_by_record_id": "completed-cycle-record",
         "response_text": SECRETS[3]},
    ])
    write_jsonl(Path(str(cfg.members["qwen"].session) + ".billing.jsonl"), [
        {"generation_id": "generation-1", "usage_usd": 1.25, "created_at": STAMP,
         "raw": {"response_text": SECRETS[4]}},
        {"generation_id": "generation-2", "usage_usd": .5, "created_at": STAMP},
        {"generation_id": "old-generation", "usage_usd": 100,
         "created_at": (NOW - timedelta(days=8)).isoformat()},
    ])
    return Community(tmp_path, cfg, rows, assembly, private)
