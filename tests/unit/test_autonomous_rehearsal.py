from hamutay.memory.rehearsal import run_fake_autonomy_rehearsal


def test_fake_autonomy_rehearsal_runs_scheduler_driver_closure_and_idle():
    result = run_fake_autonomy_rehearsal()

    assert result.dispatch.status == "completed"
    assert result.handler.last_report is not None
    assert result.handler.last_report.ran == 2
    assert result.handler.last_report.stopped_because == "idle: no open work remained"
    assert [cycle.woke_on for cycle in result.handler.last_report.cycles] == [
        "seed",
        "open_items",
    ]
    assert result.memory.closed_handles == [
        {
            "record_id": result.handler.last_report.cycles[0].record_id,
            "source": "open_items",
            "index": 0,
        }
    ]

    open_items = result.memory.open_items(reason="test final open check")
    assert open_items.ok
    assert open_items.data["items"] == []


def test_fake_autonomy_rehearsal_persists_scheduler_result_and_auditable_closure():
    result = run_fake_autonomy_rehearsal()
    assert result.dispatch.lifecycle_record is not None

    scheduled_result = result.memory.recall(
        record_id=result.dispatch.lifecycle_record["result_record_id"]
    )
    changed = result.memory.what_changed(
        since_record_id=result.handler.last_report.cycles[0].record_id
    )
    retrieval_log = result.memory.retrieval_log()

    assert scheduled_result.ok
    content = scheduled_result.data["content"]["content"]
    assert content["event_id"] == result.dispatch.event_id
    assert content["handler_result"]["driver_report"]["ran"] == 2
    assert content["handler_result"]["driver_report"]["stopped_because"] == (
        "idle: no open work remained"
    )

    assert changed.ok
    assert any(
        attestation["kind"] == "closure"
        and attestation["status"] == "resolved"
        and attestation["content"]["target_handle"] == result.memory.closed_handles[0]
        for attestation in changed.data["attestations"]
    )

    assert retrieval_log.ok
    recall_entries = [
        entry for entry in retrieval_log.data["retrievals"] if entry["tool"] == "recall"
    ]
    assert any(
        entry["reason"].get("text") == "scheduler context resolution"
        and entry["reason"].get("event_id") == result.dispatch.event_id
        for entry in recall_entries
    )
