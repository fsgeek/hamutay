"""Tamper-evident append-only ledger for autonomous action traces."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]
GENESIS_HASH = "0" * 64
LEDGER_SCHEMA_VERSION = "autonomous_action_ledger.v1"
Redactor = Callable[[Any], Any]

OPERATION_RECORD_SCHEMA: JsonDict = {
    "schema_version": LEDGER_SCHEMA_VERSION,
    "record_type": "operation",
    "required_payload_fields": [
        "run_id",
        "cycle_id",
        "wake_id",
        "operation_id",
        "operation_type",
        "actor",
        "raw_parameters",
        "validated_parameters",
        "reason",
        "precondition_checks",
        "result_status",
        "result",
        "result_hash",
        "truncation",
        "omission",
        "error",
        "created_records",
    ],
}


def default_redactor(value: Any) -> Any:
    """Default redaction policy: preserve all values."""

    return deepcopy(value)


@dataclass(frozen=True)
class LedgerVerification:
    ok: bool
    record_count: int
    errors: list[JsonDict]

    def to_dict(self) -> JsonDict:
        return {
            "ok": self.ok,
            "record_count": self.record_count,
            "errors": deepcopy(self.errors),
        }


class ActionLedger:
    """Append-only JSONL ledger with canonical hash chaining.

    The ledger has no model-facing tool surface. It is an in-process detective
    control: tampering is detectable by ``verify()``, not prevented by this
    class alone.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        redactor: Redactor | None = None,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._redactor = redactor or default_redactor

    def append_run_manifest(
        self,
        *,
        run_id: str,
        manifest: JsonDict,
        sandbox: JsonDict | None = None,
    ) -> JsonDict:
        payload = {
            "run_id": str(run_id),
            "manifest": self._redacted(manifest),
            "manifest_hash": canonical_hash(manifest),
            "sandbox": self._redacted(sandbox or {}),
        }
        return self._append("run_manifest", payload)

    def append_action_trace(
        self,
        *,
        run_id: str,
        cycle_id: str | int | None = None,
        wake_id: str | None = None,
        trace: JsonDict,
    ) -> JsonDict:
        payload = {
            "run_id": str(run_id),
            "cycle_id": None if cycle_id is None else str(cycle_id),
            "wake_id": wake_id,
            "trace": self._redacted(trace),
        }
        return self._append("action_trace", payload)

    def append_operation(
        self,
        *,
        run_id: str,
        operation_id: str,
        operation_type: str,
        actor: str,
        cycle_id: str | int | None = None,
        wake_id: str | None = None,
        raw_parameters: JsonDict | None = None,
        validated_parameters: JsonDict | None = None,
        reason: str | JsonDict | None = None,
        precondition_checks: list[JsonDict] | None = None,
        result_status: str,
        result: Any = None,
        truncation: JsonDict | None = None,
        omission: JsonDict | None = None,
        error: JsonDict | None = None,
        created_records: list[JsonDict] | None = None,
    ) -> JsonDict:
        payload = {
            "run_id": str(run_id),
            "cycle_id": None if cycle_id is None else str(cycle_id),
            "wake_id": wake_id,
            "operation_id": str(operation_id),
            "operation_type": str(operation_type),
            "actor": str(actor),
            "raw_parameters": self._redacted(raw_parameters or {}),
            "validated_parameters": self._redacted(validated_parameters or {}),
            "reason": self._redacted(reason),
            "precondition_checks": self._redacted(precondition_checks or []),
            "result_status": str(result_status),
            "result": self._redacted(result),
            "result_hash": canonical_hash(result),
            "truncation": self._redacted(truncation or {}),
            "omission": self._redacted(omission or {}),
            "error": self._redacted(error),
            "created_records": self._redacted(created_records or []),
        }
        return self._append("operation", payload)

    def append_validation_rejections(
        self,
        *,
        run_id: str,
        cycle_id: str | int | None,
        trace: JsonDict,
    ) -> list[JsonDict]:
        return [
            row for row in self.append_validation_operations(
                run_id=run_id,
                cycle_id=cycle_id,
                trace=trace,
            )
            if row["payload"]["result_status"] == "rejected"
        ]

    def append_validation_operations(
        self,
        *,
        run_id: str,
        cycle_id: str | int | None,
        trace: JsonDict,
    ) -> list[JsonDict]:
        rows: list[JsonDict] = []
        for index, action in enumerate(trace.get("accepted_actions", [])):
            rows.append(
                self.append_operation(
                    run_id=run_id,
                    cycle_id=cycle_id,
                    operation_id=f"accepted-action-{index}",
                    operation_type=str(action.get("action_type", "unknown")),
                    actor="harness",
                    raw_parameters={"accepted_action": action},
                    validated_parameters=action.get("parameters", {}),
                    reason="action validation acceptance",
                    precondition_checks=[
                        {"name": "schema_validation", "ok": True}
                    ],
                    result_status="accepted",
                    result={"accepted_action": action},
                )
            )
        for index, rejection in enumerate(trace.get("rejected_actions", [])):
            rows.append(
                self.append_operation(
                    run_id=run_id,
                    cycle_id=cycle_id,
                    operation_id=f"rejected-action-{index}",
                    operation_type=str(rejection.get("action_type", "unknown")),
                    actor="harness",
                    raw_parameters={"rejection": rejection},
                    validated_parameters={},
                    reason="action validation rejection",
                    precondition_checks=[],
                    result_status="rejected",
                    result={"rejection": rejection},
                    error={
                        "layer": "validation",
                        "code": rejection.get("code"),
                        "message": rejection.get("message"),
                    },
                )
            )
        return rows

    def read_records(self) -> list[JsonDict]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text().splitlines()
            if line.strip()
        ]

    def verify(self) -> LedgerVerification:
        records = self.read_records()
        errors: list[JsonDict] = []
        previous_hash = GENESIS_HASH
        for expected_sequence, record in enumerate(records, start=1):
            if record.get("sequence") != expected_sequence:
                errors.append(
                    {
                        "sequence": expected_sequence,
                        "code": "sequence_mismatch",
                        "message": "ledger sequence is not monotonic",
                        "value": record.get("sequence"),
                    }
                )
            if record.get("previous_hash") != previous_hash:
                errors.append(
                    {
                        "sequence": expected_sequence,
                        "code": "previous_hash_mismatch",
                        "message": "previous_hash does not match prior record",
                        "value": record.get("previous_hash"),
                        "expected": previous_hash,
                    }
                )
            expected_hash = record_hash(record)
            if record.get("record_hash") != expected_hash:
                errors.append(
                    {
                        "sequence": expected_sequence,
                        "code": "record_hash_mismatch",
                        "message": "record_hash does not match canonical record",
                        "value": record.get("record_hash"),
                        "expected": expected_hash,
                    }
                )
            previous_hash = expected_hash
        return LedgerVerification(
            ok=not errors,
            record_count=len(records),
            errors=errors,
        )

    def _append(self, record_type: str, payload: JsonDict) -> JsonDict:
        records = self.read_records()
        sequence = len(records) + 1
        previous_hash = (
            records[-1]["record_hash"] if records else GENESIS_HASH
        )
        record = {
            "ledger_schema_version": LEDGER_SCHEMA_VERSION,
            "record_type": record_type,
            "sequence": sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_hash": previous_hash,
            "payload": deepcopy(payload),
        }
        record["record_hash"] = record_hash(record)
        with self.path.open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        return deepcopy(record)

    def _redacted(self, value: Any) -> Any:
        return deepcopy(self._redactor(value))


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def record_hash(record: JsonDict) -> str:
    hashed = {k: v for k, v in record.items() if k != "record_hash"}
    return canonical_hash(hashed)
