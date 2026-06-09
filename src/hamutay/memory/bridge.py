"""Hamut'ay memory bridge contract.

This module defines the narrow Hamut'ay-facing memory port and a deterministic
local substrate used for contract tests. The local substrate is intentionally
strict: unsupported behavior and missing data return explicit failures and are
logged as retrieval attempts. It is not evidence that production storage works.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID, uuid4


JsonDict = dict[str, Any]

RETRIEVAL_REASON_LAYER = "consumption_time"
ATTESTATION_LAYER = "contestable_attestation"
EXECUTION_TRACE_LAYER = "execution_trace"
PRODUCTION_LAYER = "production_time"

OPEN_STATUSES = {"open", "partial", "uncertain", "declared_lost", "contested"}
CLOSING_STATUSES = {
    "closed",
    "complete",
    "completed",
    "invalidated",
    "resolved",
    "supported",
    "superseded",
}
OPEN_CONTENT_FIELDS = ("open_items", "evidence_requests", "declared_losses")
OPEN_CONTENT_TARGET_KEYS = ("target_handle", "target", "closes")
ALLOWED_RELABEL_CAUSES = {
    "wrong_label",
    "malformed_query",
    "missing_index_axis",
    "substrate_failure",
}


@dataclass(frozen=True)
class MemoryFailure:
    """Explicit memory-port failure result."""

    code: str
    message: str
    details: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "code": self.code,
            "message": self.message,
            "details": deepcopy(self.details),
        }


@dataclass(frozen=True)
class MemoryResponse:
    """Envelope returned by memory-port operations."""

    ok: bool
    data: JsonDict = field(default_factory=dict)
    error: MemoryFailure | None = None

    @classmethod
    def success(cls, **data: Any) -> "MemoryResponse":
        return cls(ok=True, data=data)

    @classmethod
    def failure(
        cls,
        code: str,
        message: str,
        **details: Any,
    ) -> "MemoryResponse":
        return cls(
            ok=False,
            error=MemoryFailure(code=code, message=message, details=details),
        )

    def to_dict(self) -> JsonDict:
        if self.ok:
            return {"ok": True, **deepcopy(self.data)}
        assert self.error is not None
        return {"ok": False, "error": self.error.to_dict()}


@dataclass
class MemoryRecord:
    """Stored episode with layer-separated metadata."""

    record_id: UUID
    record_type: str
    content: JsonDict
    production: JsonDict
    objective_attestations: list[JsonDict]
    execution_trace: JsonDict
    sequence: int

    def public_view(self) -> JsonDict:
        return {
            "record_id": str(self.record_id),
            "record_type": self.record_type,
            "content": deepcopy(self.content),
            "production": deepcopy(self.production),
            "objective_attestations": deepcopy(self.objective_attestations),
            "execution_trace": deepcopy(self.execution_trace),
            "sequence": self.sequence,
        }


@dataclass
class MemoryEdge:
    edge_id: UUID
    from_record_id: UUID
    to_record_id: UUID
    relation_type: str
    provenance: JsonDict
    sequence: int

    def public_view(self) -> JsonDict:
        return {
            "edge_id": str(self.edge_id),
            "from_record_id": str(self.from_record_id),
            "to_record_id": str(self.to_record_id),
            "relation_type": self.relation_type,
            "provenance": deepcopy(self.provenance),
            "sequence": self.sequence,
        }


@dataclass
class MemoryAttestation:
    attestation_id: UUID
    subject_record_id: UUID
    kind: str
    status: str
    content: JsonDict
    provenance: JsonDict
    scope: str
    layer: str
    sequence: int
    target_record_id: UUID | None = None
    cause: str | None = None

    def public_view(self) -> JsonDict:
        view = {
            "attestation_id": str(self.attestation_id),
            "subject_record_id": str(self.subject_record_id),
            "kind": self.kind,
            "status": self.status,
            "content": deepcopy(self.content),
            "provenance": deepcopy(self.provenance),
            "scope": self.scope,
            "layer": self.layer,
            "sequence": self.sequence,
        }
        if self.target_record_id is not None:
            view["target_record_id"] = str(self.target_record_id)
        if self.cause is not None:
            view["cause"] = self.cause
        return view


@dataclass
class RetrievalLogEntry:
    retrieval_id: UUID
    tool: str
    coordinate: JsonDict
    reason: JsonDict
    success: bool
    records_returned: list[str]
    fields_returned: list[str]
    detail_level: str
    omitted: list[str]
    truncated: bool
    error: JsonDict | None
    sequence: int

    def public_view(self) -> JsonDict:
        return {
            "retrieval_id": str(self.retrieval_id),
            "tool": self.tool,
            "coordinate": deepcopy(self.coordinate),
            "reason": deepcopy(self.reason),
            "success": self.success,
            "records_returned": list(self.records_returned),
            "fields_returned": list(self.fields_returned),
            "detail_level": self.detail_level,
            "omitted": list(self.omitted),
            "truncated": self.truncated,
            "error": deepcopy(self.error),
            "sequence": self.sequence,
        }


class MemoryPort(Protocol):
    """Narrow Hamut'ay-facing memory port."""

    def store_episode(
        self,
        *,
        record_id: UUID | str | None = None,
        record_type: str,
        content: JsonDict,
        production: JsonDict,
        objective_attestations: list[JsonDict] | None = None,
        execution_trace: JsonDict | None = None,
    ) -> MemoryResponse:
        ...

    def recall(
        self,
        *,
        record_id: UUID | str,
        field: str | None = None,
        detail_level: str = "full",
        max_chars: int | None = None,
        reason: str | JsonDict | None = None,
    ) -> MemoryResponse:
        ...

    def schema(
        self,
        *,
        record_id: UUID | str,
        reason: str | JsonDict | None = None,
    ) -> MemoryResponse:
        ...

    def walk(
        self,
        *,
        from_record_id: UUID | str,
        direction: str = "both",
        depth: int = 1,
        reason: str | JsonDict | None = None,
    ) -> MemoryResponse:
        ...

    def link_records(
        self,
        *,
        from_record_id: UUID | str,
        to_record_id: UUID | str,
        relation_type: str,
        provenance: JsonDict | None = None,
    ) -> MemoryResponse:
        ...

    def open_items(self, *, reason: str | JsonDict | None = None) -> MemoryResponse:
        ...

    def what_changed(
        self,
        *,
        since_record_id: UUID | str,
        reason: str | JsonDict | None = None,
    ) -> MemoryResponse:
        ...

    def retrieval_log(self) -> MemoryResponse:
        ...

    def write_attestation(
        self,
        *,
        subject_record_id: UUID | str,
        kind: str,
        status: str,
        content: JsonDict,
        provenance: JsonDict,
        scope: str,
        target_record_id: UUID | str | None = None,
        cause: str | None = None,
    ) -> MemoryResponse:
        ...


class LocalMemorySubstrate(MemoryPort):
    """Failure-capable deterministic substrate for memory-port contract tests."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self._records: dict[UUID, MemoryRecord] = {}
        self._edges: list[MemoryEdge] = []
        self._attestations: list[MemoryAttestation] = []
        self._retrievals: list[RetrievalLogEntry] = []
        self._sequence = 0

    def store_episode(
        self,
        *,
        record_id: UUID | str | None = None,
        record_type: str,
        content: JsonDict,
        production: JsonDict,
        objective_attestations: list[JsonDict] | None = None,
        execution_trace: JsonDict | None = None,
    ) -> MemoryResponse:
        unavailable = self._unavailable()
        if unavailable is not None:
            return unavailable
        parsed = self._parse_record_id(record_id or uuid4(), field_name="record_id")
        if isinstance(parsed, MemoryResponse):
            return parsed
        if parsed in self._records:
            return MemoryResponse.failure(
                "duplicate_record",
                f"Record {parsed} already exists",
                record_id=str(parsed),
            )
        if not isinstance(content, dict):
            return MemoryResponse.failure("invalid_content", "content must be an object")
        if not isinstance(production, dict):
            return MemoryResponse.failure(
                "invalid_production", "production must be an object"
            )
        if execution_trace is not None and not isinstance(execution_trace, dict):
            return MemoryResponse.failure(
                "invalid_execution_trace", "execution_trace must be an object"
            )

        self._sequence += 1
        record = MemoryRecord(
            record_id=parsed,
            record_type=str(record_type),
            content=deepcopy(content),
            production={
                "layer": PRODUCTION_LAYER,
                **deepcopy(production),
            },
            objective_attestations=[
                {
                    "layer": ATTESTATION_LAYER,
                    **deepcopy(attestation),
                }
                for attestation in (objective_attestations or [])
            ],
            execution_trace={
                "layer": EXECUTION_TRACE_LAYER,
                **deepcopy(execution_trace or {}),
            },
            sequence=self._sequence,
        )
        self._records[parsed] = record
        return MemoryResponse.success(record_id=str(parsed), record=record.public_view())

    def link_records(
        self,
        *,
        from_record_id: UUID | str,
        to_record_id: UUID | str,
        relation_type: str,
        provenance: JsonDict | None = None,
    ) -> MemoryResponse:
        unavailable = self._unavailable()
        if unavailable is not None:
            return unavailable
        from_id = self._parse_record_id(from_record_id, field_name="from_record_id")
        if isinstance(from_id, MemoryResponse):
            return from_id
        to_id = self._parse_record_id(to_record_id, field_name="to_record_id")
        if isinstance(to_id, MemoryResponse):
            return to_id
        missing = [str(rid) for rid in (from_id, to_id) if rid not in self._records]
        if missing:
            return MemoryResponse.failure(
                "record_not_found",
                "Cannot link missing record(s)",
                record_ids=missing,
            )
        self._sequence += 1
        edge = MemoryEdge(
            edge_id=uuid4(),
            from_record_id=from_id,
            to_record_id=to_id,
            relation_type=str(relation_type),
            provenance=deepcopy(provenance or {}),
            sequence=self._sequence,
        )
        self._edges.append(edge)
        return MemoryResponse.success(edge=edge.public_view())

    def recall(
        self,
        *,
        record_id: UUID | str,
        field: str | None = None,
        detail_level: str = "full",
        max_chars: int | None = None,
        reason: str | JsonDict | None = None,
    ) -> MemoryResponse:
        parsed = self._parse_record_id(record_id, field_name="record_id")
        if isinstance(parsed, MemoryResponse):
            self._log_retrieval(
                tool="recall",
                coordinate={"record_id": str(record_id), "field": field},
                reason=reason,
                success=False,
                detail_level=detail_level,
                error=parsed.error,
            )
            return parsed
        unavailable = self._unavailable()
        if unavailable is not None:
            self._log_retrieval(
                tool="recall",
                coordinate={"record_id": str(parsed), "field": field},
                reason=reason,
                success=False,
                detail_level=detail_level,
                error=unavailable.error,
            )
            return unavailable
        record = self._records.get(parsed)
        if record is None:
            failure = MemoryResponse.failure(
                "record_not_found",
                f"Record {parsed} not found",
                record_id=str(parsed),
            )
            self._log_retrieval(
                tool="recall",
                coordinate={"record_id": str(parsed), "field": field},
                reason=reason,
                success=False,
                detail_level=detail_level,
                error=failure.error,
            )
            return failure
        if field is None:
            value: Any = record.public_view()
            fields_returned = sorted(record.content.keys())
        else:
            found = self._resolve_field(record.content, field)
            if found is _MISSING:
                failure = MemoryResponse.failure(
                    "field_not_found",
                    f"Field {field!r} not found in record {parsed}",
                    record_id=str(parsed),
                    field=field,
                )
                self._log_retrieval(
                    tool="recall",
                    coordinate={"record_id": str(parsed), "field": field},
                    reason=reason,
                    success=False,
                    detail_level=detail_level,
                    error=failure.error,
                )
                return failure
            value = deepcopy(found)
            fields_returned = [field]

        payload, truncated, omitted = self._bounded_payload(value, max_chars)
        self._log_retrieval(
            tool="recall",
            coordinate={"record_id": str(parsed), "field": field},
            reason=reason,
            success=True,
            records_returned=[str(parsed)],
            fields_returned=fields_returned,
            detail_level=detail_level,
            omitted=omitted,
            truncated=truncated,
        )
        return MemoryResponse.success(
            record_id=str(parsed),
            content=payload,
            field=field,
            detail_level=detail_level,
            truncated=truncated,
            omitted=omitted,
        )

    def schema(
        self,
        *,
        record_id: UUID | str,
        reason: str | JsonDict | None = None,
    ) -> MemoryResponse:
        parsed = self._parse_record_id(record_id, field_name="record_id")
        if isinstance(parsed, MemoryResponse):
            self._log_retrieval(
                tool="schema",
                coordinate={"record_id": str(record_id)},
                reason=reason,
                success=False,
                detail_level="schema",
                error=parsed.error,
            )
            return parsed
        unavailable = self._unavailable()
        if unavailable is not None:
            self._log_retrieval(
                tool="schema",
                coordinate={"record_id": str(parsed)},
                reason=reason,
                success=False,
                detail_level="schema",
                error=unavailable.error,
            )
            return unavailable
        record = self._records.get(parsed)
        if record is None:
            failure = MemoryResponse.failure(
                "record_not_found",
                f"Record {parsed} not found",
                record_id=str(parsed),
            )
            self._log_retrieval(
                tool="schema",
                coordinate={"record_id": str(parsed)},
                reason=reason,
                success=False,
                detail_level="schema",
                error=failure.error,
            )
            return failure
        self._log_retrieval(
            tool="schema",
            coordinate={"record_id": str(parsed)},
            reason=reason,
            success=True,
            records_returned=[str(parsed)],
            fields_returned=sorted(record.content.keys()),
            detail_level="schema",
        )
        return MemoryResponse.success(
            record_id=str(parsed),
            field_names=sorted(record.content.keys()),
            field_types={k: type(v).__name__ for k, v in record.content.items()},
            field_sizes={k: self._field_size(v) for k, v in record.content.items()},
            total_chars=len(json.dumps(record.content, default=str)),
        )

    def walk(
        self,
        *,
        from_record_id: UUID | str,
        direction: str = "both",
        depth: int = 1,
        reason: str | JsonDict | None = None,
    ) -> MemoryResponse:
        parsed = self._parse_record_id(from_record_id, field_name="from_record_id")
        if isinstance(parsed, MemoryResponse):
            self._log_retrieval(
                tool="walk",
                coordinate={"from_record_id": str(from_record_id)},
                reason=reason,
                success=False,
                detail_level="graph",
                error=parsed.error,
            )
            return parsed
        unavailable = self._unavailable()
        if unavailable is not None:
            self._log_retrieval(
                tool="walk",
                coordinate={"from_record_id": str(parsed)},
                reason=reason,
                success=False,
                detail_level="graph",
                error=unavailable.error,
            )
            return unavailable
        if parsed not in self._records:
            failure = MemoryResponse.failure(
                "record_not_found",
                f"Record {parsed} not found",
                record_id=str(parsed),
            )
            self._log_retrieval(
                tool="walk",
                coordinate={"from_record_id": str(parsed)},
                reason=reason,
                success=False,
                detail_level="graph",
                error=failure.error,
            )
            return failure
        if direction not in {"forward", "backward", "both"}:
            failure = MemoryResponse.failure(
                "unsupported_direction",
                "direction must be one of: forward, backward, both",
                direction=direction,
            )
            self._log_retrieval(
                tool="walk",
                coordinate={"from_record_id": str(parsed), "direction": direction},
                reason=reason,
                success=False,
                detail_level="graph",
                error=failure.error,
            )
            return failure

        visited = {parsed}
        frontier = [(parsed, 0)]
        path: list[JsonDict] = []
        while frontier:
            current, current_depth = frontier.pop(0)
            if current_depth >= depth:
                continue
            for edge in self._matching_edges(current, direction):
                candidate = (
                    edge.to_record_id
                    if edge.from_record_id == current
                    else edge.from_record_id
                )
                next_depth = current_depth + 1
                record = self._records[candidate]
                path.append(
                    {
                        "record_id": str(candidate),
                        "edge": edge.public_view(),
                        "depth": next_depth,
                        "field_names": sorted(record.content.keys()),
                        "summary": self._summary(record.content),
                    }
                )
                if candidate in visited:
                    continue
                visited.add(candidate)
                frontier.append((candidate, next_depth))
        self._log_retrieval(
            tool="walk",
            coordinate={
                "from_record_id": str(parsed),
                "direction": direction,
                "depth": depth,
            },
            reason=reason,
            success=True,
            records_returned=[step["record_id"] for step in path],
            detail_level="graph",
        )
        return MemoryResponse.success(path=path)

    def open_items(self, *, reason: str | JsonDict | None = None) -> MemoryResponse:
        unavailable = self._unavailable()
        if unavailable is not None:
            self._log_retrieval(
                tool="open_items",
                coordinate={},
                reason=reason,
                success=False,
                detail_level="summary",
                error=unavailable.error,
            )
            return unavailable
        items: list[JsonDict] = []
        content_closures = self._latest_targeted_closures()
        for record in self._records.values():
            for key in OPEN_CONTENT_FIELDS:
                value = record.content.get(key)
                if not value:
                    continue
                entries = value if isinstance(value, list) else [value]
                for index, entry in enumerate(entries):
                    handle = self._open_content_handle(record.record_id, key, index)
                    closure = content_closures.get(self._handle_key(handle))
                    if closure is not None and closure.status in CLOSING_STATUSES:
                        continue
                    items.append(
                        {
                            "record_id": str(record.record_id),
                            "source": key,
                            "handle": handle,
                            "item": deepcopy(entry),
                        }
                    )
        for attestation in self._latest_attestations_by_chain().values():
            if attestation.status in OPEN_STATUSES:
                items.append(
                    {
                        "record_id": str(attestation.subject_record_id),
                        "source": "attestation",
                        "item": attestation.public_view(),
                    }
                )
        self._log_retrieval(
            tool="open_items",
            coordinate={},
            reason=reason,
            success=True,
            records_returned=sorted({item["record_id"] for item in items}),
            detail_level="summary",
        )
        return MemoryResponse.success(items=items)

    def what_changed(
        self,
        *,
        since_record_id: UUID | str,
        reason: str | JsonDict | None = None,
    ) -> MemoryResponse:
        parsed = self._parse_record_id(since_record_id, field_name="since_record_id")
        if isinstance(parsed, MemoryResponse):
            self._log_retrieval(
                tool="what_changed",
                coordinate={"since_record_id": str(since_record_id)},
                reason=reason,
                success=False,
                detail_level="summary",
                error=parsed.error,
            )
            return parsed
        unavailable = self._unavailable()
        if unavailable is not None:
            self._log_retrieval(
                tool="what_changed",
                coordinate={"since_record_id": str(parsed)},
                reason=reason,
                success=False,
                detail_level="summary",
                error=unavailable.error,
            )
            return unavailable
        if parsed not in self._records:
            failure = MemoryResponse.failure(
                "record_not_found",
                f"Record {parsed} not found",
                record_id=str(parsed),
            )
            self._log_retrieval(
                tool="what_changed",
                coordinate={"since_record_id": str(parsed)},
                reason=reason,
                success=False,
                detail_level="summary",
                error=failure.error,
            )
            return failure
        base_sequence = self._records[parsed].sequence
        records = [
            record.public_view()
            for record in self._records.values()
            if record.sequence > base_sequence
        ]
        attestations = [
            attestation.public_view()
            for attestation in self._attestations
            if attestation.sequence > base_sequence
        ]
        self._log_retrieval(
            tool="what_changed",
            coordinate={"since_record_id": str(parsed)},
            reason=reason,
            success=True,
            records_returned=[record["record_id"] for record in records],
            detail_level="summary",
        )
        return MemoryResponse.success(records=records, attestations=attestations)

    def retrieval_log(self) -> MemoryResponse:
        return MemoryResponse.success(
            retrievals=[entry.public_view() for entry in self._retrievals]
        )

    def write_attestation(
        self,
        *,
        subject_record_id: UUID | str,
        kind: str,
        status: str,
        content: JsonDict,
        provenance: JsonDict,
        scope: str,
        target_record_id: UUID | str | None = None,
        cause: str | None = None,
    ) -> MemoryResponse:
        unavailable = self._unavailable()
        if unavailable is not None:
            return unavailable
        subject = self._parse_record_id(subject_record_id, field_name="subject_record_id")
        if isinstance(subject, MemoryResponse):
            return subject
        if subject not in self._records:
            return MemoryResponse.failure(
                "record_not_found",
                f"Record {subject} not found",
                record_id=str(subject),
            )
        target: UUID | None = None
        if target_record_id is not None:
            parsed_target = self._parse_record_id(
                target_record_id, field_name="target_record_id"
            )
            if isinstance(parsed_target, MemoryResponse):
                return parsed_target
            if parsed_target not in self._records:
                return MemoryResponse.failure(
                    "record_not_found",
                    f"Record {parsed_target} not found",
                    record_id=str(parsed_target),
                )
            target = parsed_target
        if kind == "relabel" and cause not in ALLOWED_RELABEL_CAUSES:
            return MemoryResponse.failure(
                "ambiguous_relabel",
                "relabel attestations require a disambiguating cause",
                allowed_causes=sorted(ALLOWED_RELABEL_CAUSES),
                cause=cause,
            )

        self._sequence += 1
        attestation = MemoryAttestation(
            attestation_id=uuid4(),
            subject_record_id=subject,
            target_record_id=target,
            kind=str(kind),
            status=str(status),
            content=deepcopy(content),
            provenance=deepcopy(provenance),
            scope=str(scope),
            layer=ATTESTATION_LAYER,
            cause=cause,
            sequence=self._sequence,
        )
        self._attestations.append(attestation)
        if kind == "semantic_conflict" and target is not None:
            edge_response = self.link_records(
                from_record_id=subject,
                to_record_id=target,
                relation_type="semantic_conflict",
                provenance={
                    "layer": ATTESTATION_LAYER,
                    "attestation_id": str(attestation.attestation_id),
                    **deepcopy(provenance),
                },
            )
            if not edge_response.ok:
                return edge_response
        return MemoryResponse.success(attestation=attestation.public_view())

    def find(self, **_: Any) -> MemoryResponse:
        """Broad semantic find is explicitly out of scope for the substrate."""
        return MemoryResponse.failure(
            "unsupported_operation",
            "semantic find is deferred until its scope is explicitly decided",
        )

    def _unavailable(self) -> MemoryResponse | None:
        if self.available:
            return None
        return MemoryResponse.failure(
            "substrate_unavailable",
            "Local memory substrate is configured unavailable",
        )

    def _parse_record_id(
        self, value: UUID | str, *, field_name: str
    ) -> UUID | MemoryResponse:
        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return MemoryResponse.failure(
                "invalid_record_id",
                f"{field_name} is not a valid UUID",
                field_name=field_name,
                value=str(value),
            )

    def _log_retrieval(
        self,
        *,
        tool: str,
        coordinate: JsonDict,
        reason: str | JsonDict | None,
        success: bool,
        records_returned: list[str] | None = None,
        fields_returned: list[str] | None = None,
        detail_level: str,
        omitted: list[str] | None = None,
        truncated: bool = False,
        error: MemoryFailure | None = None,
    ) -> None:
        self._sequence += 1
        self._retrievals.append(
            RetrievalLogEntry(
                retrieval_id=uuid4(),
                tool=tool,
                coordinate=deepcopy(coordinate),
                reason=self._reason(reason),
                success=success,
                records_returned=list(records_returned or []),
                fields_returned=list(fields_returned or []),
                detail_level=detail_level,
                omitted=list(omitted or []),
                truncated=truncated,
                error=error.to_dict() if error else None,
                sequence=self._sequence,
            )
        )

    def _reason(self, reason: str | JsonDict | None) -> JsonDict:
        if reason is None:
            value: JsonDict = {}
        elif isinstance(reason, dict):
            value = deepcopy(reason)
        else:
            value = {"text": str(reason)}
        return {
            "layer": RETRIEVAL_REASON_LAYER,
            **value,
        }

    def _bounded_payload(
        self, value: Any, max_chars: int | None
    ) -> tuple[Any, bool, list[str]]:
        if max_chars is None:
            return deepcopy(value), False, []
        text = json.dumps(value, default=str, sort_keys=True)
        if len(text) <= max_chars:
            return deepcopy(value), False, []
        return text[:max_chars], True, ["payload_truncated"]

    def _matching_edges(self, record_id: UUID, direction: str) -> list[MemoryEdge]:
        edges: list[MemoryEdge] = []
        for edge in self._edges:
            if direction in {"forward", "both"} and edge.from_record_id == record_id:
                edges.append(edge)
            if direction in {"backward", "both"} and edge.to_record_id == record_id:
                edges.append(edge)
        return sorted(edges, key=lambda edge: edge.sequence)

    def _summary(self, content: JsonDict) -> str:
        keys = sorted(content.keys())
        if not keys:
            return "(empty record)"
        shown = ", ".join(keys[:5])
        suffix = "..." if len(keys) > 5 else ""
        return f"{len(keys)} field(s): {shown}{suffix}"

    def _field_size(self, value: Any) -> int:
        if isinstance(value, (dict, list, tuple, set, str)):
            return len(value)
        return 1

    def _open_content_handle(
        self, record_id: UUID, source: str, index: int
    ) -> JsonDict:
        return {"record_id": str(record_id), "source": source, "index": index}

    def _handle_key(self, handle: JsonDict) -> tuple[str, str, int] | None:
        try:
            record_id = str(handle["record_id"])
            source = str(handle["source"])
            index = int(handle["index"])
        except (KeyError, TypeError, ValueError):
            return None
        if source not in OPEN_CONTENT_FIELDS:
            return None
        return (record_id, source, index)

    def _target_handle(self, attestation: MemoryAttestation) -> JsonDict | None:
        if attestation.kind != "closure":
            return None
        for key in OPEN_CONTENT_TARGET_KEYS:
            value = attestation.content.get(key)
            if isinstance(value, dict):
                return value
        return None

    def _latest_targeted_closures(self) -> dict[tuple[str, str, int], MemoryAttestation]:
        latest: dict[tuple[str, str, int], MemoryAttestation] = {}
        for attestation in sorted(self._attestations, key=lambda item: item.sequence):
            target = self._target_handle(attestation)
            if target is None:
                continue
            key = self._handle_key(target)
            if key is None:
                continue
            latest[key] = attestation
        return latest

    def _latest_attestations_by_chain(
        self,
    ) -> dict[tuple[UUID, str, str], MemoryAttestation]:
        latest: dict[tuple[UUID, str, str], MemoryAttestation] = {}
        for attestation in sorted(self._attestations, key=lambda item: item.sequence):
            if self._target_handle(attestation) is not None:
                continue
            key = (
                attestation.subject_record_id,
                attestation.kind,
                attestation.scope,
            )
            latest[key] = attestation
        return latest

    def _resolve_field(self, content: JsonDict, field: str) -> Any:
        if field in content:
            return content[field]
        current: Any = content
        for part in field.split("."):
            if not isinstance(current, dict) or part not in current:
                return _MISSING
            current = current[part]
        return current


_MISSING = object()
