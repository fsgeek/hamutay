"""Restart frontier persistence for autonomous action runs."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hamutay.events import EventStore, EVENT_TYPE_REFLECTION, utc_now_iso
from hamutay.memory.action_ledger import (
    GENESIS_HASH,
    ActionLedger,
    LedgerVerification,
    canonical_hash,
)
from hamutay.memory.bridge import LocalMemorySubstrate


JsonDict = dict[str, Any]
FRONTIER_SCHEMA_VERSION = "autonomous_restart_frontier.v1"


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


@dataclass(frozen=True)
class RestartFrontier:
    """One committed restart boundary."""

    run_id: str
    cycle_id: int
    next_cycle_id: int
    result_record_id: str | None
    ledger_sequence: int
    ledger_record_hash: str | None
    event_record_count: int
    memory_snapshot_hash: str
    committed_at: str
    status: str = "committed"
    notes: JsonDict = field(default_factory=dict)

    def to_payload(self) -> JsonDict:
        return {
            "schema_version": FRONTIER_SCHEMA_VERSION,
            "run_id": self.run_id,
            "cycle_id": self.cycle_id,
            "next_cycle_id": self.next_cycle_id,
            "result_record_id": self.result_record_id,
            "ledger_sequence": self.ledger_sequence,
            "ledger_record_hash": self.ledger_record_hash,
            "event_record_count": self.event_record_count,
            "memory_snapshot_hash": self.memory_snapshot_hash,
            "committed_at": self.committed_at,
            "status": self.status,
            "notes": deepcopy(self.notes),
        }

    @classmethod
    def from_payload(cls, payload: JsonDict) -> "RestartFrontier":
        if payload.get("schema_version") != FRONTIER_SCHEMA_VERSION:
            raise ValueError("unsupported restart frontier schema")
        return cls(
            run_id=str(payload["run_id"]),
            cycle_id=int(payload["cycle_id"]),
            next_cycle_id=int(payload["next_cycle_id"]),
            result_record_id=(
                str(payload["result_record_id"])
                if payload.get("result_record_id") is not None else None
            ),
            ledger_sequence=int(payload["ledger_sequence"]),
            ledger_record_hash=(
                str(payload["ledger_record_hash"])
                if payload.get("ledger_record_hash") is not None else None
            ),
            event_record_count=int(payload["event_record_count"]),
            memory_snapshot_hash=str(payload["memory_snapshot_hash"]),
            committed_at=str(payload["committed_at"]),
            status=str(payload.get("status", "committed")),
            notes=deepcopy(payload.get("notes", {})),
        )


@dataclass(frozen=True)
class FrontierLoadResult:
    """What resume reconstructed from persisted artifacts."""

    frontier: RestartFrontier | None
    ledger_verification: LedgerVerification
    recovered_event_records: list[JsonDict]
    suppressed_event_records: list[JsonDict]
    ignored_ledger_records: list[JsonDict]

    def to_dict(self) -> JsonDict:
        return {
            "frontier": (
                self.frontier.to_payload() if self.frontier is not None else None
            ),
            "ledger_verification": self.ledger_verification.to_dict(),
            "recovered_event_records": deepcopy(self.recovered_event_records),
            "suppressed_event_records": deepcopy(self.suppressed_event_records),
            "ignored_ledger_records": deepcopy(self.ignored_ledger_records),
        }


class RestartFrontierStore:
    """Append-only restart frontier and memory snapshot store."""

    def __init__(
        self,
        *,
        frontier_path: str | Path,
        memory_snapshot_path: str | Path,
    ) -> None:
        self.frontier_path = Path(frontier_path)
        self.memory_snapshot_path = Path(memory_snapshot_path)
        self.frontier_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_run_manifest(
        self,
        *,
        ledger: ActionLedger,
        run_id: str,
        manifest: JsonDict,
        sandbox: JsonDict | None = None,
    ) -> JsonDict | None:
        """Persist a run manifest if this ledger has not already stored one."""
        for record in ledger.read_records():
            if (
                record.get("record_type") == "run_manifest"
                and record.get("payload", {}).get("run_id") == str(run_id)
            ):
                return None
        return ledger.append_run_manifest(
            run_id=run_id,
            manifest=manifest,
            sandbox=sandbox,
        )

    def commit_frontier(
        self,
        *,
        run_id: str,
        cycle_id: int,
        result_record_id: str | None,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
        notes: JsonDict | None = None,
    ) -> RestartFrontier:
        """Persist the latest clean restart boundary."""
        snapshot = memory.snapshot()
        snapshot_hash = canonical_hash(snapshot)
        self._write_json_atomic(self.memory_snapshot_path, snapshot)

        ledger_records = ledger.read_records()
        latest_ledger = ledger_records[-1] if ledger_records else None
        frontier = RestartFrontier(
            run_id=str(run_id),
            cycle_id=int(cycle_id),
            next_cycle_id=int(cycle_id) + 1,
            result_record_id=(
                str(result_record_id) if result_record_id is not None else None
            ),
            ledger_sequence=(
                int(latest_ledger["sequence"]) if latest_ledger is not None else 0
            ),
            ledger_record_hash=(
                str(latest_ledger["record_hash"])
                if latest_ledger is not None else None
            ),
            event_record_count=len(event_store.read_records()),
            memory_snapshot_hash=snapshot_hash,
            committed_at=datetime.now(timezone.utc).isoformat(),
            notes=deepcopy(notes or {}),
        )
        self._append_frontier(frontier)
        return frontier

    def load_latest(
        self,
        *,
        run_id: str,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
        recover_events: bool = True,
    ) -> FrontierLoadResult:
        """Load the latest committed frontier and repair uncommitted events."""
        verification = ledger.verify()
        if not verification.ok:
            raise ValueError(
                "action ledger verification failed during restart frontier load: "
                f"{verification.errors}"
            )
        frontier = self.latest(run_id=run_id)
        if frontier is not None:
            snapshot = self._read_snapshot()
            if canonical_hash(snapshot) != frontier.memory_snapshot_hash:
                raise ValueError("memory snapshot hash does not match frontier")
            memory.load_snapshot(snapshot)
        else:
            memory.load_snapshot(
                {
                    "schema_version": "local_memory_substrate.v1",
                    "available": True,
                    "sequence": 0,
                    "records": [],
                    "edges": [],
                    "attestations": [],
                    "retrievals": [],
                }
            )

        ignored = [
            record for record in ledger.read_records()
            if int(record.get("sequence", 0)) > (
                frontier.ledger_sequence if frontier is not None else 0
            )
        ]
        recovered: list[JsonDict] = []
        suppressed: list[JsonDict] = []
        if recover_events:
            recovered, suppressed = self._recover_events(
                run_id=run_id,
                frontier=frontier,
                event_store=event_store,
            )
        return FrontierLoadResult(
            frontier=frontier,
            ledger_verification=verification,
            recovered_event_records=recovered,
            suppressed_event_records=suppressed,
            ignored_ledger_records=ignored,
        )

    def latest(self, *, run_id: str) -> RestartFrontier | None:
        frontiers = [
            frontier for frontier in self.read_frontiers()
            if frontier.run_id == str(run_id) and frontier.status == "committed"
        ]
        if not frontiers:
            return None
        return frontiers[-1]

    def read_frontiers(self) -> list[RestartFrontier]:
        return [
            RestartFrontier.from_payload(record["payload"])
            for record in self._read_frontier_records()
        ]

    def _append_frontier(self, frontier: RestartFrontier) -> JsonDict:
        records = self._read_frontier_records()
        sequence = len(records) + 1
        previous_hash = (
            records[-1]["frontier_hash"] if records else GENESIS_HASH
        )
        record = {
            "frontier_schema_version": FRONTIER_SCHEMA_VERSION,
            "record_type": "restart_frontier",
            "sequence": sequence,
            "timestamp": utc_now_iso(),
            "previous_hash": previous_hash,
            "payload": frontier.to_payload(),
        }
        record["frontier_hash"] = canonical_hash(record)
        with self.frontier_path.open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        return deepcopy(record)

    def _recover_events(
        self,
        *,
        run_id: str,
        frontier: RestartFrontier | None,
        event_store: EventStore,
    ) -> tuple[list[JsonDict], list[JsonDict]]:
        committed_sequence = frontier.ledger_sequence if frontier is not None else 0
        recovered: list[JsonDict] = []
        suppressed: list[JsonDict] = []
        histories: dict[str, list[JsonDict]] = {}
        for record in event_store.read_records():
            event_id = record.get("event_id")
            if event_id:
                histories.setdefault(str(event_id), []).append(record)
        for event_id, history in histories.items():
            latest = history[-1]
            pending_source = next(
                (
                    record for record in history
                    if record.get("status") == "pending"
                ),
                latest,
            )
            audit_sequence = pending_source.get("audit_ledger_sequence")
            if (
                audit_sequence is not None
                and int(audit_sequence) > committed_sequence
            ):
                suppressed_record = {
                    "record_type": "event_status",
                    "event_id": event_id,
                    "event_type": latest.get("event_type", EVENT_TYPE_REFLECTION),
                    "status": "suppressed",
                    "suppressed_at": utc_now_iso(),
                    "suppressed_by_policy": "restart_frontier",
                    "suppression_reason": (
                        "event was created after latest committed frontier"
                    ),
                    "suppressed_after_ledger_sequence": committed_sequence,
                }
                event_store.append(suppressed_record)
                suppressed.append(suppressed_record)
                continue
            if latest.get("status") != "running":
                continue
            if latest.get("run_id") != str(run_id):
                continue
            recovered_record = {
                **deepcopy(pending_source),
                "status": "pending",
                "recovered_at": utc_now_iso(),
                "recovered_by": "restart_frontier",
                "recovered_from_run_id": str(run_id),
                "recovered_after_ledger_sequence": committed_sequence,
            }
            event_store.append(recovered_record)
            recovered.append(recovered_record)
        return recovered, suppressed

    def _read_snapshot(self) -> JsonDict:
        if not self.memory_snapshot_path.exists():
            raise FileNotFoundError(self.memory_snapshot_path)
        return json.loads(self.memory_snapshot_path.read_text())

    def _read_frontier_records(self) -> list[JsonDict]:
        if not self.frontier_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.frontier_path.read_text().splitlines()
            if line.strip()
        ]

    @staticmethod
    def _write_json_atomic(path: Path, payload: JsonDict) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(_json_copy(payload), sort_keys=True) + "\n")
        tmp_path.replace(path)
