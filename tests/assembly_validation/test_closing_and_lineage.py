from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier

from hamutay.assembly.close import try_close
from hamutay.assembly.pass_ import run_pass
from hamutay.assembly.records import reduce

from .conftest import House, T0, convene_question, land_outbox, take_and_complete


def _close(house: House, question_id: str, *, now: datetime) -> dict:
    with house.ledger.locked():
        view = reduce(house.ledger.read_unlocked())
        closing = try_close(
            house.ledger,
            view,
            view.questions[question_id],
            now=now,
            actor="heartbeat:validator",
        )
    assert closing is not None
    return closing


def _prepared_assent(house: House) -> dict:
    q = convene_question(house)
    land_outbox(house)
    take_and_complete(house, q, "north", "assent")
    take_and_complete(house, q, "east", "assent")
    return q


def _race_to_close(house: House, first: str, second: str) -> str:
    q = _prepared_assent(house)
    barrier = Barrier(2)

    def heartbeat(door: str) -> dict:
        barrier.wait()
        result, _memo = run_pass(
            house.bindings[door],
            now=T0 + timedelta(days=1, seconds=1),
            actor=f"heartbeat:{door}",
        )
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(heartbeat, (first, second)))

    records = house.ledger.read()
    closings = [
        record
        for record in records
        if record["record_type"] == "closing" and record["question_id"] == q["question_id"]
    ]
    assert len(closings) == 1
    assert sum(bool(result.get("closed")) for result in results) == 1
    return closings[0]["outcome"]


def test_two_heartbeats_close_once_without_changing_the_outcome(house_factory):
    north_first = _race_to_close(house_factory("north-first"), "north", "east")
    east_first = _race_to_close(house_factory("east-first"), "east", "north")
    assert north_first == east_first == "assented"


def test_dissent_survives_silence_is_cleared_only_by_replacement_and_wins_round_three(
    house_factory,
):
    persistent = house_factory("persistent")
    q = convene_question(persistent)
    land_outbox(persistent)
    take_and_complete(persistent, q, "north", "assent")
    take_and_complete(persistent, q, "east", "assent")
    dissent = take_and_complete(persistent, q, "west", "dissent", reasons="not yet")

    before = len(persistent.ledger.read())
    close1 = _close(persistent, q["question_id"], now=T0 + timedelta(days=1, seconds=1))
    after_records = persistent.ledger.read()
    assert close1["outcome"] == "extended"
    assert len(after_records) == before + 1
    assert after_records[-1]["record_type"] == "closing"
    assert after_records[-1]["next_question"] is not None

    child2 = close1["next_question"]
    view = reduce(after_records)
    assert view.questions[child2["question_id"]]["derived_from_closing"] == close1["closing_id"]
    assert not any(
        row["record_type"] == "question" and row["question_id"] == child2["question_id"]
        for row in after_records
    )

    land_outbox(persistent, now=datetime.fromisoformat(close1["closed_at"]))
    close2 = _close(
        persistent,
        child2["question_id"],
        now=datetime.fromisoformat(child2["closes_at"]) + timedelta(seconds=1),
    )
    assert close2["outcome"] == "extended"
    assert close2["tally"]["active"]["west"] == dissent["position_id"]

    child3 = close2["next_question"]
    land_outbox(persistent, now=datetime.fromisoformat(close2["closed_at"]))
    close3 = _close(
        persistent,
        child3["question_id"],
        now=datetime.fromisoformat(child3["closes_at"]) + timedelta(seconds=1),
    )
    assert close3["outcome"] == "unresolved"
    assert close3["tally"]["active"]["west"] == dissent["position_id"]

    replaced = house_factory("replaced")
    q = convene_question(replaced)
    land_outbox(replaced)
    take_and_complete(replaced, q, "north", "assent")
    take_and_complete(replaced, q, "east", "assent")
    take_and_complete(replaced, q, "west", "dissent")
    close1 = _close(replaced, q["question_id"], now=T0 + timedelta(days=1, seconds=1))
    child2 = close1["next_question"]
    land_outbox(replaced, now=datetime.fromisoformat(close1["closed_at"]))
    replacement = take_and_complete(
        replaced,
        child2,
        "west",
        "assent",
        now=datetime.fromisoformat(close1["closed_at"]) + timedelta(minutes=1),
        cycle=2,
    )
    close2 = _close(
        replaced,
        child2["question_id"],
        now=datetime.fromisoformat(child2["closes_at"]) + timedelta(seconds=1),
    )
    assert close2["outcome"] == "assented"
    assert close2["tally"]["active"]["west"] == replacement["position_id"]
