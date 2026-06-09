from uuid import UUID

from hamutay.memory.bridge import LocalMemorySubstrate


RID_1 = UUID("00000000-0000-0000-0000-000000000101")
RID_2 = UUID("00000000-0000-0000-0000-000000000102")
RID_3 = UUID("00000000-0000-0000-0000-000000000103")


def _substrate_with_records() -> LocalMemorySubstrate:
    substrate = LocalMemorySubstrate()
    first = substrate.store_episode(
        record_id=RID_1,
        record_type="cycle",
        content={
            "claim": "first claim",
            "nested": {"field": "nested value"},
            "open_items": [{"kind": "question", "text": "what changed?"}],
            "declared_losses": [{"what": "detail", "why": "budget"}],
            "body": "alpha " * 40,
        },
        production={
            "who": {"instance": "test-instance"},
            "what": {"artifact": "cycle-state"},
            "when": {"cycle": 1},
            "where": {"project": "hamutay"},
        },
        objective_attestations=[
            {"kind": "goal", "text": "test bridge contract"}
        ],
        execution_trace={"tool_path": "local-test"},
    )
    assert first.ok
    second = substrate.store_episode(
        record_id=RID_2,
        record_type="cycle",
        content={"claim": "second claim", "evidence_requests": [{"id": "req-1"}]},
        production={"who": {"instance": "test-instance"}, "when": {"cycle": 2}},
        execution_trace={"tool_path": "local-test"},
    )
    assert second.ok
    linked = substrate.link_records(
        from_record_id=RID_1,
        to_record_id=RID_2,
        relation_type="refines",
        provenance={"source": "test"},
    )
    assert linked.ok
    return substrate


def test_exact_record_recall_by_uuid_and_field_level_recall():
    substrate = _substrate_with_records()

    full = substrate.recall(record_id=RID_1, reason="load full record")
    field = substrate.recall(
        record_id=str(RID_1),
        field="nested.field",
        reason={"purpose": "surgical recall"},
    )

    assert full.ok
    assert full.data["content"]["record_id"] == str(RID_1)
    assert field.ok
    assert field.data["content"] == "nested value"
    assert field.data["field"] == "nested.field"


def test_invalid_uuid_and_missing_record_fail_explicitly_and_are_logged():
    substrate = _substrate_with_records()

    invalid = substrate.recall(record_id="not-a-uuid", reason="bad id")
    missing = substrate.recall(record_id=RID_3, reason="missing id")
    log = substrate.retrieval_log()

    assert not invalid.ok
    assert invalid.error is not None
    assert invalid.error.code == "invalid_record_id"
    assert not missing.ok
    assert missing.error is not None
    assert missing.error.code == "record_not_found"
    assert log.ok
    failures = [entry for entry in log.data["retrievals"] if not entry["success"]]
    assert [entry["error"]["code"] for entry in failures] == [
        "invalid_record_id",
        "record_not_found",
    ]
    assert all(entry["reason"]["layer"] == "consumption_time" for entry in failures)


def test_schema_map_returns_structure_without_full_content():
    substrate = _substrate_with_records()

    schema = substrate.schema(record_id=RID_1, reason="inspect before recall")

    assert schema.ok
    assert set(schema.data["field_names"]) >= {"claim", "nested", "body"}
    assert "content" not in schema.data
    assert schema.data["field_types"]["nested"] == "dict"


def test_graph_walk_from_known_anchor():
    substrate = _substrate_with_records()

    walked = substrate.walk(from_record_id=RID_1, direction="forward", depth=1)

    assert walked.ok
    assert len(walked.data["path"]) == 1
    assert walked.data["path"][0]["record_id"] == str(RID_2)
    assert walked.data["path"][0]["edge"]["relation_type"] == "refines"


def test_open_items_include_declared_losses_and_open_evidence_requests():
    substrate = _substrate_with_records()
    attested = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="status",
        status="open",
        content={"claim": "still unresolved"},
        provenance={"actor": "test"},
        scope="claim",
    )
    assert attested.ok

    open_items = substrate.open_items(reason="resume open work")

    assert open_items.ok
    sources = {item["source"] for item in open_items.data["items"]}
    assert {"open_items", "declared_losses", "evidence_requests", "attestation"} <= sources


def test_open_content_items_can_be_closed_by_exact_append_only_attestation():
    substrate = _substrate_with_records()
    before = substrate.open_items(reason="find closure target")
    assert before.ok
    target = next(item for item in before.data["items"] if item["source"] == "open_items")

    closed = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="closure",
        status="resolved",
        content={
            "target_handle": target["handle"],
            "basis": "test resolved the outstanding question",
        },
        provenance={"actor": "test"},
        scope="open_items",
    )
    after = substrate.open_items(reason="resume after closure")
    recalled = substrate.recall(record_id=RID_1)
    changed = substrate.what_changed(since_record_id=RID_1)

    assert closed.ok
    assert after.ok
    assert not any(
        item["source"] == "open_items" and item["record_id"] == str(RID_1)
        for item in after.data["items"]
    )
    assert recalled.data["content"]["content"]["open_items"] == [
        {"kind": "question", "text": "what changed?"}
    ]
    assert any(
        attestation["status"] == "resolved"
        and attestation["content"]["target_handle"] == target["handle"]
        for attestation in changed.data["attestations"]
    )


def test_ambiguous_or_contested_targeted_attestation_does_not_close_open_content():
    substrate = _substrate_with_records()
    before = substrate.open_items()
    assert before.ok
    target = next(item for item in before.data["items"] if item["source"] == "open_items")

    malformed = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="closure",
        status="resolved",
        content={"target_handle": {"record_id": str(RID_1), "source": "open_items"}},
        provenance={"actor": "test"},
        scope="open_items",
    )
    contested = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="closure",
        status="contested",
        content={"target_handle": target["handle"]},
        provenance={"actor": "test"},
        scope="open_items",
    )
    after = substrate.open_items(reason="ambiguous closure should not hide work")

    assert malformed.ok
    assert contested.ok
    assert after.ok
    assert any(
        item["source"] == "open_items" and item["record_id"] == str(RID_1)
        for item in after.data["items"]
    )


def test_attestation_open_items_collapse_to_latest_status_per_chain():
    substrate = _substrate_with_records()
    opened = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="status",
        status="open",
        content={"claim": "needs follow-up"},
        provenance={"actor": "test"},
        scope="claim",
    )
    resolved = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="status",
        status="resolved",
        content={"claim": "follow-up complete"},
        provenance={"actor": "test"},
        scope="claim",
    )
    open_items = substrate.open_items(reason="latest status should govern")
    changed = substrate.what_changed(since_record_id=RID_1)

    assert opened.ok
    assert resolved.ok
    assert not any(
        item["source"] == "attestation"
        and item["item"]["kind"] == "status"
        and item["item"]["scope"] == "claim"
        for item in open_items.data["items"]
    )
    statuses = [
        attestation["status"]
        for attestation in changed.data["attestations"]
        if attestation["kind"] == "status" and attestation["scope"] == "claim"
    ]
    assert statuses == ["open", "resolved"]


def test_contested_latest_attestation_remains_live_open_work():
    substrate = _substrate_with_records()
    resolved = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="status",
        status="resolved",
        content={"claim": "initially resolved"},
        provenance={"actor": "test"},
        scope="claim",
    )
    contested = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="status",
        status="contested",
        content={"claim": "resolution was challenged"},
        provenance={"actor": "test"},
        scope="claim",
    )
    open_items = substrate.open_items(reason="contested claims remain live")

    assert resolved.ok
    assert contested.ok
    assert any(
        item["source"] == "attestation"
        and item["item"]["kind"] == "status"
        and item["item"]["scope"] == "claim"
        and item["item"]["status"] == "contested"
        for item in open_items.data["items"]
    )


def test_attestation_chain_is_append_only_and_preserves_declared_loss():
    substrate = _substrate_with_records()

    supported = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="status",
        status="supported",
        content={"claim": "first claim"},
        provenance={"actor": "scorer"},
        scope="claim",
    )
    invalidated = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="status",
        status="invalidated",
        content={"claim": "first claim", "reason": "new evidence"},
        provenance={"actor": "scorer"},
        scope="claim",
    )
    items = substrate.open_items()

    assert supported.ok
    assert invalidated.ok
    changed = substrate.what_changed(since_record_id=RID_1)
    assert changed.ok
    statuses = [a["status"] for a in changed.data["attestations"]]
    assert statuses == ["supported", "invalidated"]
    assert any(item["source"] == "declared_losses" for item in items.data["items"])


def test_successful_recall_logs_consumption_time_reason():
    substrate = _substrate_with_records()

    result = substrate.recall(record_id=RID_1, field="claim", reason="answer user")
    log = substrate.retrieval_log()

    assert result.ok
    assert log.ok
    last = log.data["retrievals"][-1]
    assert last["success"] is True
    assert last["records_returned"] == [str(RID_1)]
    assert last["fields_returned"] == ["claim"]
    assert last["reason"] == {"layer": "consumption_time", "text": "answer user"}


def test_bounded_payload_reports_truncation_and_omission_metadata():
    substrate = _substrate_with_records()

    result = substrate.recall(record_id=RID_1, field="body", max_chars=20)
    log = substrate.retrieval_log()

    assert result.ok
    assert result.data["truncated"] is True
    assert result.data["omitted"] == ["payload_truncated"]
    assert len(result.data["content"]) == 20
    assert log.data["retrievals"][-1]["truncated"] is True


def test_production_and_consumption_layers_remain_separate():
    substrate = _substrate_with_records()

    recalled = substrate.recall(record_id=RID_1, reason="consumer query")
    log = substrate.retrieval_log()

    assert recalled.ok
    record = recalled.data["content"]
    assert record["production"]["layer"] == "production_time"
    assert record["objective_attestations"][0]["layer"] == "contestable_attestation"
    assert record["execution_trace"]["layer"] == "execution_trace"
    assert "reason" not in record["production"]
    assert log.data["retrievals"][-1]["reason"]["layer"] == "consumption_time"


def test_relabel_requires_disambiguating_cause_and_does_not_overwrite():
    substrate = _substrate_with_records()

    ambiguous = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="relabel",
        status="contested",
        content={"from": "X", "to": "Y"},
        provenance={"actor": "archivist"},
        scope="label",
    )
    relabel = substrate.write_attestation(
        subject_record_id=RID_1,
        kind="relabel",
        status="contested",
        content={"from": "X", "to": "Y"},
        provenance={"actor": "archivist"},
        scope="label",
        cause="wrong_label",
    )
    recalled = substrate.recall(record_id=RID_1)

    assert not ambiguous.ok
    assert ambiguous.error is not None
    assert ambiguous.error.code == "ambiguous_relabel"
    assert relabel.ok
    assert relabel.data["attestation"]["cause"] == "wrong_label"
    assert recalled.data["content"]["content"]["claim"] == "first claim"


def test_semantic_conflict_write_down_is_attestation_edge_not_truth():
    substrate = _substrate_with_records()

    conflict = substrate.write_attestation(
        subject_record_id=RID_1,
        target_record_id=RID_2,
        kind="semantic_conflict",
        status="contested",
        content={"basis": "consumer semantic judgment"},
        provenance={"actor": "consumer-layer"},
        scope="claim",
    )
    walked = substrate.walk(from_record_id=RID_1, direction="forward", depth=1)
    recalled = substrate.recall(record_id=RID_1)

    assert conflict.ok
    assert conflict.data["attestation"]["layer"] == "contestable_attestation"
    edge_types = {step["edge"]["relation_type"] for step in walked.data["path"]}
    assert "semantic_conflict" in edge_types
    assert "semantic_conflict" not in recalled.data["content"]["content"]


def test_unsupported_semantic_find_and_substrate_unavailable_fail_explicitly():
    substrate = _substrate_with_records()
    unavailable = LocalMemorySubstrate(available=False)

    find = substrate.find(query="meaning")
    failed_store = unavailable.store_episode(
        record_id=RID_1,
        record_type="cycle",
        content={},
        production={},
    )

    assert not find.ok
    assert find.error is not None
    assert find.error.code == "unsupported_operation"
    assert not failed_store.ok
    assert failed_store.error is not None
    assert failed_store.error.code == "substrate_unavailable"


import pytest


@pytest.mark.xfail(
    reason=(
        "Found-by: Claude (adversarial pass against Codex's fused build, 2026-06-08). "
        "Module docstring (bridge.py:4-6): 'missing data return explicit failures.' Seven "
        "read/write methods guard on self._unavailable() (lines 305, 361, 409, 498, 561, "
        "646, 767). what_changed (bridge.py:697) does NOT — when the substrate is down it "
        "returns ok=True with an empty diff, i.e. 'nothing changed' instead of 'I cannot "
        "answer.' what_changed is the wake-resumption surface (substrate-position MVP #11); "
        "a false 'nothing changed' is exactly the masked fault the contract forbids. The "
        "unavailable-path test (test:396-413) only exercises store_episode, so the sibling "
        "read methods on the same contract are structurally untested under available=False. "
        "INTENT IS CODEX'S CALL: add the _unavailable() guard (retrieval_log may stay exempt "
        "as the audit surface). Flip once decided."
    ),
    strict=True,
)
def test_what_changed_fails_explicitly_when_substrate_unavailable():
    substrate = _substrate_with_records()
    substrate.available = False
    response = substrate.what_changed(since_record_id=RID_1)
    assert not response.ok, (
        "what_changed returned ok=True with a downed substrate — masked the fault "
        "as 'nothing changed' instead of failing explicitly"
    )


@pytest.mark.xfail(
    reason=(
        "Found-by: Claude (adversarial pass against Codex's fused build, 2026-06-08). "
        "open_items() decides closure by the SHAPE of an attestation's content, not its "
        "declared intent. _target_handle (bridge.py:951) reads content keys "
        "target_handle/target/closes and never reads attestation.kind; 'supported' is in "
        "CLOSING_STATUSES (bridge.py:32). So a kind='evidence' attestation that merely CITES "
        "an open item's handle with status='supported' silently removes it from open_items. "
        "The autonomous driver terminates on 'no open work', so this lets an offhand citation "
        "mark real work finished and strand the loop in a false idle. The closure tests "
        "(test:133, 170) only ever use kind='closure' or a malformed/non-closing handle, so "
        "'closes by shape, not intent' is never separated from 'closes by being a closure.' "
        "INTENT IS CODEX'S CALL: gate closure on kind=='closure' (or drop 'supported' from "
        "the closing set). Flip once decided."
    ),
    strict=True,
)
def test_non_closure_citation_does_not_silently_close_open_item():
    substrate = LocalMemorySubstrate()
    rid = UUID("00000000-0000-0000-0000-0000000009c1")
    substrate.store_episode(
        record_id=rid, record_type="work",
        content={"open_items": [{"text": "todo NEVER RESOLVED", "status": "open"}]},
        production={"who": {"instance": "x"}, "what": {"artifact": "x"},
                    "when": {"cycle": 1}, "where": {"project": "hamutay"}},
        execution_trace={"tool_path": "t"},
    )
    before = substrate.open_items()
    handle = before.data["items"][0]["handle"]

    # A citation, not a closure: kind='evidence', status='supported'.
    substrate.write_attestation(
        subject_record_id=str(rid), kind="evidence", status="supported",
        content={"note": "citing prior item as support", "target": handle},
        provenance={"who": {"instance": "x"}}, scope="claim",
    )

    after = substrate.open_items()
    assert len(after.data["items"]) == 1, (
        "a kind='evidence' citation with status='supported' silently closed an open "
        f"item: open_items went {len(before.data['items'])} -> {len(after.data['items'])}"
    )
