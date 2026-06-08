from uuid import UUID

import pytest

from hamutay.memory.bridge import LocalMemorySubstrate
from hamutay.memory.driver import AutonomousDriver, DriverBlocked


RID_BASE = "10000000-0000-0000-0000-0000000000"


def _record_id(index: int) -> UUID:
    return UUID(f"{RID_BASE}{index:02d}")


def _store_open_item(
    substrate: LocalMemorySubstrate,
    *,
    index: int,
    text: str,
) -> str:
    record_id = _record_id(index)
    stored = substrate.store_episode(
        record_id=record_id,
        record_type="fixture_open_item",
        content={"open_items": [{"kind": "todo", "text": text}]},
        production={
            "who": {"instance": "fixture"},
            "what": {"artifact": "open_item"},
            "when": {"cycle": index},
            "where": {"project": "hamutay"},
        },
        execution_trace={"tool_path": "test_fixture"},
    )
    assert stored.ok
    return str(record_id)


def test_seed_wake_uses_seed_before_existing_open_items_and_logs_provenance():
    substrate = LocalMemorySubstrate()
    _store_open_item(substrate, index=1, text="preexisting work")
    calls: list[str] = []

    def cognition(stimulus: str) -> str:
        calls.append(stimulus)
        return "seed response"

    driver = AutonomousDriver(
        substrate,
        cognition,
        seed_intention="start from seed",
    )

    report = driver.run(max_cycles=1)

    assert calls == ["start from seed"]
    assert report.ran == 1
    assert report.cycles[0].woke_on == "seed"
    assert report.cycles[0].wake_omission == {}

    log = substrate.retrieval_log()
    assert log.ok
    seed_reads = [
        entry
        for entry in log.data["retrievals"]
        if entry["tool"] == "open_items"
        and entry["reason"].get("text")
        == "autonomous seed wake: cold start (reads nothing)"
    ]
    assert len(seed_reads) == 1
    assert seed_reads[0]["reason"]["layer"] == "consumption_time"


def test_wake_omissions_are_visible_in_report_stimulus_and_stored_episode():
    substrate = LocalMemorySubstrate()
    for index in range(1, 8):
        _store_open_item(substrate, index=index, text=f"work-{index}")

    driver = AutonomousDriver(
        substrate,
        lambda stimulus: f"ack: {stimulus[:20]}",
        seed_intention="seed",
    )

    report = driver.run(max_cycles=2)

    assert report.ran == 2
    open_wake = report.cycles[1]
    assert open_wake.woke_on == "open_items"
    assert "work-1" in open_wake.stimulus
    assert "work-5" in open_wake.stimulus
    assert "work-6" not in open_wake.stimulus
    assert "(+2 more open item(s) omitted" in open_wake.stimulus
    assert open_wake.wake_omission == {
        "total_open": 7,
        "rendered": 5,
        "omitted": 2,
        "omitted_handles": [
            {"record_id": str(_record_id(6)), "source": "open_items"},
            {"record_id": str(_record_id(7)), "source": "open_items"},
        ],
    }

    recalled = substrate.recall(record_id=open_wake.record_id)
    assert recalled.ok
    content = recalled.data["content"]["content"]
    assert content["wake_omission"] == open_wake.wake_omission


def test_open_work_from_one_cycle_becomes_later_stimulus_without_human_input():
    substrate = LocalMemorySubstrate()
    calls: list[str] = []
    surfaced = [
        [{"kind": "todo", "text": "second-cycle-work"}],
        [],
    ]

    def cognition(stimulus: str) -> str:
        calls.append(stimulus)
        return f"response to {stimulus[:24]}"

    def extractor(stimulus: str, response: str) -> list[dict]:
        return surfaced.pop(0)

    driver = AutonomousDriver(
        substrate,
        cognition,
        seed_intention="initial work",
        open_item_extractor=extractor,
    )

    report = driver.run(max_cycles=2)

    assert report.ran == 2
    assert calls[0] == "initial work"
    assert "Continue your own open work" in calls[1]
    assert "second-cycle-work" in calls[1]
    assert report.cycles[1].woke_on == "open_items"


def test_driver_records_walkable_chain_and_link_failures_block():
    substrate = LocalMemorySubstrate()

    driver = AutonomousDriver(
        substrate,
        lambda stimulus: "ack",
        seed_intention="start",
        open_item_extractor=lambda _s, _r: [{"kind": "todo", "text": "continue"}],
    )

    report = driver.run(max_cycles=3)

    assert report.ran == 3
    walked = substrate.walk(
        from_record_id=report.cycles[0].record_id,
        direction="forward",
        depth=3,
    )
    assert walked.ok
    assert [step["record_id"] for step in walked.data["path"]] == [
        report.cycles[1].record_id,
        report.cycles[2].record_id,
    ]
    assert {step["edge"]["relation_type"] for step in walked.data["path"]} == {
        "continues"
    }


def test_consumption_wake_reason_stays_out_of_production_and_content():
    substrate = LocalMemorySubstrate()
    driver = AutonomousDriver(
        substrate,
        lambda _stimulus: "ack",
        seed_intention="start",
        open_item_extractor=lambda _s, _r: [{"kind": "todo", "text": "again"}],
    )

    report = driver.run(max_cycles=2)
    recalled = substrate.recall(record_id=report.cycles[1].record_id)

    assert recalled.ok
    record = recalled.data["content"]
    assert record["production"]["layer"] == "production_time"
    assert "reason" not in record["production"]
    assert "wake_reason" not in record["production"]
    assert "wake_reason" not in record["content"]
    assert record["execution_trace"]["woke_on"] == "open_items"

    log = substrate.retrieval_log()
    assert log.ok
    open_item_reads = [
        entry for entry in log.data["retrievals"] if entry["tool"] == "open_items"
    ]
    assert len(open_item_reads) == 2
    assert all(
        entry["reason"]["layer"] == "consumption_time"
        for entry in open_item_reads
    )


def test_substrate_seed_wake_read_failure_blocks_before_cognition():
    substrate = LocalMemorySubstrate(available=False)
    calls: list[str] = []
    driver = AutonomousDriver(
        substrate,
        lambda stimulus: calls.append(stimulus) or "ack",
        seed_intention="start",
    )

    with pytest.raises(DriverBlocked, match="seed-wake open_items failed"):
        driver.run(max_cycles=1)

    assert calls == []


def test_zero_cycle_budget_does_not_wake_or_call_cognition():
    substrate = LocalMemorySubstrate()
    calls: list[str] = []
    driver = AutonomousDriver(
        substrate,
        lambda stimulus: calls.append(stimulus) or "ack",
        seed_intention="start",
    )

    report = driver.run(max_cycles=0)

    assert report.ran == 0
    assert report.cycles == []
    assert report.stopped_because == "budget: reached max_cycles=0"
    assert calls == []
    assert substrate.retrieval_log().data["retrievals"] == []
