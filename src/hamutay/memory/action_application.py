"""Apply validated autonomous action traces through audited operations."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from hamutay.events import EventStore, build_pending_event
from hamutay.memory.action_ledger import ActionLedger, canonical_hash
from hamutay.memory.bridge import MemoryPort


JsonDict = dict[str, Any]


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


@dataclass(frozen=True)
class ActionApplicationResult:
    """Result of applying one model-authored action trace."""

    status: str
    result_record_id: str | None = None
    applied_operations: list[JsonDict] = field(default_factory=list)
    refused_operations: list[JsonDict] = field(default_factory=list)
    created_records: list[JsonDict] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return {
            "status": self.status,
            "result_record_id": self.result_record_id,
            "applied_operations": deepcopy(self.applied_operations),
            "refused_operations": deepcopy(self.refused_operations),
            "created_records": deepcopy(self.created_records),
        }


class AutonomousActionApplier:
    """Apply accepted actions without inferring undeclared intent.

    The applier is the Phase-3 mutation boundary. It records the action trace,
    validation operations, and every substrate operation in the ledger. Existing
    ``schedule_event`` tool buffers are disabled for autonomy runs here unless a
    future caller routes them through this same operation path.
    """

    def __init__(
        self,
        *,
        memory: MemoryPort,
        ledger: ActionLedger,
        event_store: EventStore | None = None,
        instance_id: str = "hamutay-autonomous",
        project: str = "hamutay",
    ) -> None:
        self._memory = memory
        self._ledger = ledger
        self._event_store = event_store
        self._instance_id = instance_id
        self._project = project

    def apply_trace(
        self,
        trace: JsonDict,
        *,
        run_id: str,
        cycle_id: str | int,
        wake_id: str | None = None,
        result_record_id: str | UUID | None = None,
        event: JsonDict | None = None,
        tool_pending_events: list[JsonDict] | None = None,
    ) -> ActionApplicationResult:
        trace = _json_copy(trace)
        created_records: list[JsonDict] = []
        applied: list[JsonDict] = []
        refused: list[JsonDict] = []

        self._ledger.append_action_trace(
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=wake_id,
            trace=trace,
        )
        self._ledger.append_validation_operations(
            run_id=run_id,
            cycle_id=cycle_id,
            trace=trace,
        )

        for index, pending_event in enumerate(tool_pending_events or []):
            row = self._refuse_tool_scheduled_event(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=wake_id,
                index=index,
                pending_event=pending_event,
            )
            refused.append(row["payload"])

        if trace.get("validation_status") == "rejected":
            for index, action in enumerate(trace.get("accepted_actions", [])):
                if action.get("action_type") == "response":
                    continue
                row = self._append_refusal(
                    run_id=run_id,
                    cycle_id=cycle_id,
                    wake_id=wake_id,
                    operation_id=(
                        f"cycle-{cycle_id}:refuse-rejected-trace:"
                        f"{index}:{action.get('action_type', 'unknown')}"
                    ),
                    operation_type=f"apply_{action.get('action_type', 'unknown')}",
                    raw_parameters={"accepted_action": action},
                    reason="whole action trace was rejected",
                    code="action_trace_rejected",
                    message="accepted subaction was not applied because the action trace was rejected",
                )
                refused.append(row["payload"])
            return ActionApplicationResult(
                status="rejected",
                refused_operations=refused,
            )

        action_record = self._store_action_record(
            trace,
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=wake_id,
            result_record_id=result_record_id,
        )
        action_payload = action_record["payload"]
        if action_payload["result_status"] in {"applied", "no_op"}:
            applied.append(action_payload)
            created_records.extend(action_payload["created_records"])
            result_record_id = action_payload["result"]["record_id"]
        else:
            refused.append(action_payload)
            return ActionApplicationResult(
                status="blocked",
                refused_operations=refused,
            )

        for index, action in enumerate(trace.get("accepted_actions", [])):
            action_type = action.get("action_type")
            if action_type == "closure":
                row = self._apply_closure(
                    action,
                    run_id=run_id,
                    cycle_id=cycle_id,
                    wake_id=wake_id,
                    index=index,
                )
                self._collect_operation(row, applied, refused, created_records)
            elif action_type == "schedule_request":
                row = self._apply_schedule_request(
                    action,
                    run_id=run_id,
                    cycle_id=cycle_id,
                    wake_id=wake_id,
                    index=index,
                    result_record_id=str(result_record_id),
                )
                self._collect_operation(row, applied, refused, created_records)
            elif action_type == "policy_action":
                row = self._apply_policy_disposition(
                    action,
                    trace=trace,
                    run_id=run_id,
                    cycle_id=cycle_id,
                    wake_id=wake_id,
                    index=index,
                    result_record_id=str(result_record_id),
                    event=event,
                )
                self._collect_operation(row, applied, refused, created_records)

        status = "applied_with_refusals" if refused else "applied"
        return ActionApplicationResult(
            status=status,
            result_record_id=str(result_record_id),
            applied_operations=applied,
            refused_operations=refused,
            created_records=created_records,
        )

    def _store_action_record(
        self,
        trace: JsonDict,
        *,
        run_id: str,
        cycle_id: str | int,
        wake_id: str | None,
        result_record_id: str | UUID | None,
    ) -> JsonDict:
        parsed = trace.get("parsed_action") or {}
        content: JsonDict = {
            "response": parsed.get("response", ""),
        }
        for content_field in (
            "open_items",
            "declared_losses",
            "uncertainty",
            "abandonment_reason",
            "defer_reason",
            "policy_action",
        ):
            if content_field in parsed:
                content[content_field] = deepcopy(parsed[content_field])

        raw_parameters = {
            "record_id": None if result_record_id is None else str(result_record_id),
            "record_type": "autonomous_action_cycle",
            "content": content,
        }
        response = self._memory.store_episode(
            record_id=result_record_id,
            record_type="autonomous_action_cycle",
            content=content,
            production={
                "who": {"instance": self._instance_id},
                "what": {"artifact": "autonomous_action_cycle"},
                "when": {"cycle": cycle_id},
                "where": {"project": self._project},
            },
            execution_trace={
                "tool_path": "autonomous_action_applier",
                "run_id": run_id,
                "cycle_id": str(cycle_id),
                "wake_id": wake_id,
                "schema_version": trace.get("schema_version"),
            },
        )
        result = response.to_dict()
        if response.ok:
            created = [
                {
                    "record_type": "memory_record",
                    "record_id": response.data["record_id"],
                }
            ]
            return self._ledger.append_operation(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=wake_id,
                operation_id=f"cycle-{cycle_id}:store-action-record",
                operation_type="store_autonomous_action_record",
                actor="harness",
                raw_parameters=raw_parameters,
                validated_parameters=raw_parameters,
                reason="commit accepted model-authored action object",
                precondition_checks=[
                    {"name": "trace_validation_status", "ok": True}
                ],
                result_status="applied",
                result={
                    "ok": True,
                    "record_id": response.data["record_id"],
                    "record": response.data.get("record"),
                },
                created_records=created,
            )
        error = _memory_error(result)
        if (
            result_record_id is not None
            and isinstance(error, dict)
            and error.get("code") == "duplicate_record"
        ):
            return self._ledger.append_operation(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=wake_id,
                operation_id=f"cycle-{cycle_id}:store-action-record",
                operation_type="store_autonomous_action_record",
                actor="harness",
                raw_parameters=raw_parameters,
                validated_parameters=raw_parameters,
                reason="commit accepted model-authored action object",
                precondition_checks=[
                    {"name": "trace_validation_status", "ok": True},
                    {
                        "name": "explicit_result_record_already_exists",
                        "ok": False,
                    },
                ],
                result_status="no_op",
                result={
                    "ok": False,
                    "record_id": str(result_record_id),
                    "duplicate_record": result,
                },
                error=error,
            )
        return self._ledger.append_operation(
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=wake_id,
            operation_id=f"cycle-{cycle_id}:store-action-record",
            operation_type="store_autonomous_action_record",
            actor="harness",
            raw_parameters=raw_parameters,
            validated_parameters=raw_parameters,
            reason="commit accepted model-authored action object",
            precondition_checks=[
                {"name": "trace_validation_status", "ok": True}
            ],
            result_status="failed",
            result=result,
            error=error,
        )

    def _apply_closure(
        self,
        action: JsonDict,
        *,
        run_id: str,
        cycle_id: str | int,
        wake_id: str | None,
        index: int,
    ) -> JsonDict:
        params = deepcopy(action.get("parameters", {}))
        handle = params.get("target_handle", {})
        response = self._memory.write_attestation(
            subject_record_id=handle.get("record_id"),
            kind="closure",
            status=params.get("status", "resolved"),
            content={
                "target_handle": deepcopy(handle),
                "basis": params.get("basis"),
                "source_path": action.get("source_path"),
            },
            provenance={
                "actor": "model",
                "applied_by": "harness",
                "instance_id": self._instance_id,
                "run_id": run_id,
                "cycle_id": str(cycle_id),
                "wake_id": wake_id,
            },
            scope=str(handle.get("source", "open_items")),
        )
        result = response.to_dict()
        if response.ok:
            created = [
                {
                    "record_type": "memory_attestation",
                    "attestation_id": (
                        response.data["attestation"]["attestation_id"]
                    ),
                }
            ]
            return self._ledger.append_operation(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=wake_id,
                operation_id=f"cycle-{cycle_id}:apply-closure:{index}",
                operation_type="apply_closure",
                actor="harness",
                raw_parameters={"accepted_action": action},
                validated_parameters=params,
                reason=params.get("basis"),
                precondition_checks=[
                    {"name": "target_handle_validated", "ok": True}
                ],
                result_status="applied",
                result=result,
                created_records=created,
            )
        return self._ledger.append_operation(
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=wake_id,
            operation_id=f"cycle-{cycle_id}:apply-closure:{index}",
            operation_type="apply_closure",
            actor="harness",
            raw_parameters={"accepted_action": action},
            validated_parameters=params,
            reason=params.get("basis"),
            precondition_checks=[
                {"name": "target_handle_validated", "ok": True}
            ],
            result_status="failed",
            result=result,
            error=_memory_error(result),
        )

    def _apply_schedule_request(
        self,
        action: JsonDict,
        *,
        run_id: str,
        cycle_id: str | int,
        wake_id: str | None,
        index: int,
        result_record_id: str,
    ) -> JsonDict:
        params = deepcopy(action.get("parameters", {}))
        operation_id = f"cycle-{cycle_id}:apply-schedule-request:{index}"
        if self._event_store is None:
            return self._append_refusal(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=wake_id,
                operation_id=operation_id,
                operation_type="apply_schedule_request",
                raw_parameters={"accepted_action": action},
                validated_parameters=params,
                reason=params.get("purpose"),
                code="event_store_unavailable",
                message="schedule_request cannot be applied without an EventStore",
            )
        try:
            event = build_pending_event(
                purpose=params["purpose"],
                requested_context=params["requested_context"],
                scheduled_by_cycle=int(cycle_id),
                scheduled_by_record_id=UUID(str(result_record_id)),
                label=params.get("label"),
                not_before=params.get("not_before"),
                expires_at=params.get("expires_at"),
                durable_update_contract=params.get("durable_update_contract"),
                durable_update_example=params.get("durable_update_example"),
                terminal_surface=params.get("terminal_surface"),
            )
        except (TypeError, ValueError, KeyError) as exc:
            return self._append_refusal(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=wake_id,
                operation_id=operation_id,
                operation_type="apply_schedule_request",
                raw_parameters={"accepted_action": action},
                validated_parameters=params,
                reason=params.get("purpose"),
                code="schedule_build_failed",
                message=str(exc),
            )
        event["audit_operation_id"] = operation_id
        event["schedule_fingerprint"] = self._schedule_fingerprint(
            params=params,
            scheduled_by_record_id=result_record_id,
        )
        duplicate = self._find_duplicate_schedule(event["schedule_fingerprint"])
        if duplicate is not None:
            return self._ledger.append_operation(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=wake_id,
                operation_id=operation_id,
                operation_type="apply_schedule_request",
                actor="harness",
                raw_parameters={"accepted_action": action},
                validated_parameters=params,
                reason=params.get("purpose"),
                precondition_checks=[
                    {
                        "name": "duplicate_schedule_fingerprint_absent",
                        "ok": False,
                        "existing_event_id": duplicate.get("event_id"),
                    }
                ],
                result_status="no_op",
                result={"duplicate_event": duplicate},
            )

        prepared = self._ledger.append_operation(
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=wake_id,
            operation_id=operation_id,
            operation_type="apply_schedule_request",
            actor="harness",
            raw_parameters={"accepted_action": action},
            validated_parameters=params,
            reason=params.get("purpose"),
            precondition_checks=[
                {"name": "event_store_available", "ok": True},
                {"name": "duplicate_schedule_fingerprint_absent", "ok": True},
            ],
            result_status="accepted",
            result={"event_to_append": event, "commit_status": "pending"},
        )
        event["audit_ledger_sequence"] = prepared["sequence"]
        event["audit_ledger_record_hash"] = prepared["record_hash"]
        self._event_store.append(event)
        return self._ledger.append_operation(
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=wake_id,
            operation_id=operation_id,
            operation_type="apply_schedule_request",
            actor="harness",
            raw_parameters={"accepted_action": action},
            validated_parameters=params,
            reason=params.get("purpose"),
            precondition_checks=[
                {"name": "event_store_available", "ok": True},
                {"name": "duplicate_schedule_fingerprint_absent", "ok": True},
            ],
            result_status="applied",
            result={"event": event},
            created_records=[
                {
                    "record_type": "event_status",
                    "event_id": event["event_id"],
                }
            ],
        )

    def _apply_policy_disposition(
        self,
        action: JsonDict,
        *,
        trace: JsonDict,
        run_id: str,
        cycle_id: str | int,
        wake_id: str | None,
        index: int,
        result_record_id: str,
        event: JsonDict | None,
    ) -> JsonDict:
        params = deepcopy(action.get("parameters", {}))
        operation_id = f"cycle-{cycle_id}:apply-policy-disposition:{index}"
        if self._event_store is None or event is None:
            return self._append_refusal(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=wake_id,
                operation_id=operation_id,
                operation_type="apply_policy_disposition",
                raw_parameters={"accepted_action": action, "event": event},
                validated_parameters=params,
                reason=params.get("policy_action"),
                code="event_context_unavailable",
                message="policy disposition requires an EventStore and source event",
            )
        parsed = trace.get("parsed_action") or {}
        policy_decision, rationale_meta, rationale_error = (
            _build_policy_decision(parsed, params["policy_action"])
        )
        if rationale_error is not None:
            return self._append_refusal(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=wake_id,
                operation_id=operation_id,
                operation_type="apply_policy_disposition",
                raw_parameters={
                    "accepted_action": action,
                    "event": event,
                    "parsed_policy_fields": _authored_policy_rationale_fields(
                        parsed
                    ),
                },
                validated_parameters={
                    "policy_action": params["policy_action"],
                    "rationale_selection": rationale_meta,
                },
                reason=params.get("policy_action"),
                code=rationale_error["code"],
                message=rationale_error["message"],
            )
        try:
            disposition = self._event_store.append_policy_disposition(
                event=event,
                run_id=run_id,
                wake_cycle=int(cycle_id),
                result_record_id=result_record_id,
                policy_decision=policy_decision,
                policy_result={
                    "source": "autonomous_action",
                    "source_path": action.get("source_path"),
                    "rationale_selection": rationale_meta,
                },
            )
        except (TypeError, ValueError, KeyError) as exc:
            return self._append_refusal(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=wake_id,
                operation_id=operation_id,
                operation_type="apply_policy_disposition",
                raw_parameters={"accepted_action": action, "event": event},
                validated_parameters=params,
                reason=params.get("policy_action"),
                code="policy_disposition_failed",
                message=str(exc),
            )
        return self._ledger.append_operation(
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=wake_id,
            operation_id=operation_id,
            operation_type="apply_policy_disposition",
            actor="harness",
            raw_parameters={"accepted_action": action, "event": event},
            validated_parameters={
                "policy_decision": policy_decision,
                "rationale_selection": rationale_meta,
                "result_record_id": result_record_id,
            },
            reason=policy_decision["rationale"],
            precondition_checks=[
                {"name": "event_store_available", "ok": True},
                {"name": "source_event_available", "ok": True},
            ],
            result_status="applied",
            result={"policy_disposition": disposition},
            created_records=[
                {
                    "record_type": "policy_disposition",
                    "disposition_id": disposition["disposition_id"],
                }
            ],
        )

    def _refuse_tool_scheduled_event(
        self,
        *,
        run_id: str,
        cycle_id: str | int,
        wake_id: str | None,
        index: int,
        pending_event: JsonDict,
    ) -> JsonDict:
        return self._append_refusal(
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=wake_id,
            operation_id=f"cycle-{cycle_id}:refuse-tool-schedule-event:{index}",
            operation_type="refuse_tool_schedule_event",
            raw_parameters={"pending_event": pending_event},
            validated_parameters={},
            reason="schedule_event tool path disabled for autonomy action runs",
            code="schedule_event_tool_disabled_for_autonomy",
            message=(
                "tool-originated pending events must not be appended outside "
                "the audited action application path"
            ),
        )

    def _append_refusal(
        self,
        *,
        run_id: str,
        cycle_id: str | int,
        wake_id: str | None,
        operation_id: str,
        operation_type: str,
        raw_parameters: JsonDict,
        code: str,
        message: str,
        validated_parameters: JsonDict | None = None,
        reason: str | JsonDict | None = None,
    ) -> JsonDict:
        return self._ledger.append_operation(
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=wake_id,
            operation_id=operation_id,
            operation_type=operation_type,
            actor="harness",
            raw_parameters=raw_parameters,
            validated_parameters=validated_parameters or {},
            reason=reason,
            precondition_checks=[],
            result_status="refused",
            result={"applied": False},
            error={"layer": "harness", "code": code, "message": message},
        )

    def _schedule_fingerprint(
        self,
        *,
        params: JsonDict,
        scheduled_by_record_id: str,
    ) -> str:
        return canonical_hash(
            {
                "purpose": params.get("purpose"),
                "requested_context": params.get("requested_context"),
                "not_before": params.get("not_before"),
                "expires_at": params.get("expires_at"),
                "label": params.get("label"),
                "durable_update_contract": params.get(
                    "durable_update_contract"
                ),
                "durable_update_example": params.get(
                    "durable_update_example"
                ),
                "terminal_surface": params.get("terminal_surface"),
                "scheduled_by_record_id": scheduled_by_record_id,
            }
        )

    def _find_duplicate_schedule(self, fingerprint: str) -> JsonDict | None:
        if self._event_store is None:
            return None
        histories: dict[str, list[JsonDict]] = {}
        for record in self._event_store.read_records():
            event_id = record.get("event_id")
            if event_id:
                histories.setdefault(str(event_id), []).append(record)
        for history in histories.values():
            latest = history[-1]
            if latest.get("status") == "suppressed":
                continue
            for record in history:
                if record.get("schedule_fingerprint") == fingerprint:
                    return record
        return None

    @staticmethod
    def _collect_operation(
        row: JsonDict,
        applied: list[JsonDict],
        refused: list[JsonDict],
        created_records: list[JsonDict],
    ) -> None:
        payload = row["payload"]
        if payload["result_status"] in {"applied", "accepted"}:
            applied.append(payload)
            created_records.extend(payload["created_records"])
        else:
            refused.append(payload)


POLICY_RATIONALE_FIELD_BY_ACTION = {
    "abandon": "abandonment_reason",
    "defer": "defer_reason",
    "ask_external_evidence": "uncertainty",
}
POLICY_RATIONALE_FIELDS = tuple(POLICY_RATIONALE_FIELD_BY_ACTION.values())


def _authored_policy_rationale_fields(parsed: JsonDict) -> JsonDict:
    return {
        field: deepcopy(parsed[field])
        for field in POLICY_RATIONALE_FIELDS
        if field in parsed
    }


def _build_policy_decision(
    parsed: JsonDict,
    policy_action: str,
) -> tuple[JsonDict, JsonDict, JsonDict | None]:
    authored = _authored_policy_rationale_fields(parsed)
    authored_field_names = sorted(authored)
    selected_field = (
        authored_field_names[0] if len(authored_field_names) == 1 else None
    )
    expected_field = POLICY_RATIONALE_FIELD_BY_ACTION.get(policy_action)
    rationale_meta = {
        "authored_rationale_fields": authored_field_names,
        "selected_rationale_field": selected_field,
        "expected_rationale_field": expected_field,
        "selection_policy": "policy_action_compatible_single_field",
    }
    if len(authored_field_names) > 1:
        return (
            {"action": policy_action, "rationale": None},
            rationale_meta,
            {
                "code": "ambiguous_policy_rationale",
                "message": (
                    "policy disposition rationale is ambiguous because more "
                    "than one rationale-like field was authored"
                ),
            },
        )
    if selected_field is not None and selected_field != expected_field:
        return (
            {"action": policy_action, "rationale": None},
            rationale_meta,
            {
                "code": "policy_rationale_action_mismatch",
                "message": (
                    "authored rationale field is not compatible with the "
                    "selected policy_action"
                ),
            },
        )
    rationale = authored[selected_field] if selected_field is not None else None
    return {"action": policy_action, "rationale": rationale}, rationale_meta, None


def _memory_error(result: JsonDict) -> JsonDict | None:
    error = result.get("error")
    if not isinstance(error, dict):
        return None
    return {
        "layer": "memory",
        "code": error.get("code"),
        "message": error.get("message"),
        "details": error.get("details", {}),
    }
