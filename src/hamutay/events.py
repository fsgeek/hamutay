"""Append-only event log for taste_open scheduled wakeups."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

EVENT_TYPE_REFLECTION = "self_scheduled_reflection"
VALID_CONTEXT_TOOLS = {"recall", "compare"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_event_log_path(session_log_path: str | Path) -> Path:
    """Return the sidecar event log path for a session JSONL."""
    path = Path(session_log_path)
    return path.with_suffix(path.suffix + ".events.jsonl")


def validate_requested_context(requests: object) -> list[dict]:
    """Validate v1 requested_context entries and return JSON-safe copies."""
    if not isinstance(requests, list) or not requests:
        raise ValueError("requested_context must be a non-empty list")

    validated: list[dict] = []
    for i, request in enumerate(requests):
        if not isinstance(request, dict):
            raise ValueError(f"requested_context[{i}] must be an object")
        tool = request.get("tool")
        if tool not in VALID_CONTEXT_TOOLS:
            raise ValueError(
                f"requested_context[{i}].tool must be one of: "
                f"{', '.join(sorted(VALID_CONTEXT_TOOLS))}"
            )
        if tool == "recall":
            has_cycle = "cycle" in request
            has_record = "record_id" in request
            if has_cycle == has_record:
                raise ValueError(
                    "recall context requires exactly one of cycle or record_id"
                )
            allowed = {"tool", "cycle", "record_id", "field"}
        else:
            if "cycle_a" not in request or "cycle_b" not in request:
                raise ValueError("compare context requires cycle_a and cycle_b")
            allowed = {"tool", "cycle_a", "cycle_b", "field", "content"}
        extra = set(request) - allowed
        if extra:
            raise ValueError(
                f"requested_context[{i}] has unsupported keys: {sorted(extra)}"
            )
        validated.append({k: v for k, v in request.items() if k in allowed})

    return json.loads(json.dumps(validated, default=str))


def build_pending_event(
    *,
    purpose: str,
    requested_context: list[dict],
    scheduled_by_cycle: int,
    scheduled_by_record_id: UUID,
    label: str | None = None,
    expires_at: str | None = None,
) -> dict:
    """Create a pending event record. Does not write it."""
    purpose = str(purpose).strip()
    if not purpose:
        raise ValueError("purpose is required")
    context = validate_requested_context(requested_context)
    event_id = uuid4()
    record = {
        "record_type": "event_status",
        "event_id": str(event_id),
        "event_type": EVENT_TYPE_REFLECTION,
        "status": "pending",
        "created_at": utc_now_iso(),
        "scheduled_by_cycle": scheduled_by_cycle,
        "scheduled_by_record_id": str(scheduled_by_record_id),
        "purpose": purpose,
        "requested_context": context,
    }
    if label:
        record["label"] = str(label)
    if expires_at:
        # Validate parseability but preserve original ISO spelling.
        datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        record["expires_at"] = str(expires_at)
    return record


@dataclass
class EventStore:
    """Append-only JSONL event store."""

    path: Path

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> None:
        with self.path.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def append_many(self, records: list[dict]) -> None:
        if not records:
            return
        with self.path.open("a") as f:
            for record in records:
                f.write(json.dumps(record, default=str) + "\n")

    def read_records(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open() as f:
            return [json.loads(line) for line in f if line.strip()]

    def latest_by_event_id(self) -> dict[str, dict]:
        latest: dict[str, dict] = {}
        for record in self.read_records():
            event_id = record.get("event_id")
            if event_id:
                latest[str(event_id)] = record
        return latest

    def next_pending(self, *, now: datetime | None = None) -> dict | None:
        """Return the oldest pending event by created_at, if any."""
        pending = [
            r for r in self.latest_by_event_id().values()
            if r.get("status") == "pending"
        ]
        if not pending:
            return None
        pending.sort(key=lambda r: r.get("created_at", ""))
        return pending[0]

    def append_running(self, event: dict, run_id: UUID | None = None) -> dict:
        record = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "running",
            "run_id": str(run_id or uuid4()),
            "started_at": utc_now_iso(),
        }
        self.append(record)
        return record

    def append_completed(
        self,
        *,
        event: dict,
        run_id: str,
        wake_cycle: int,
        result_record_id: UUID,
        response_text: str,
    ) -> dict:
        record = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "completed",
            "run_id": run_id,
            "completed_at": utc_now_iso(),
            "wake_cycle": wake_cycle,
            "result_record_id": str(result_record_id),
            "response_text": response_text,
        }
        self.append(record)
        return record

    def append_failed(self, *, event: dict, run_id: str, exc: Exception) -> dict:
        record = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "failed",
            "run_id": run_id,
            "failed_at": utc_now_iso(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        self.append(record)
        return record

    def append_expired(self, event: dict) -> dict:
        record = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "expired",
            "expired_at": utc_now_iso(),
        }
        self.append(record)
        return record


def is_expired(event: dict, *, now: datetime | None = None) -> bool:
    expires_at = event.get("expires_at")
    if not expires_at:
        return False
    deadline = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) >= deadline


def resolve_requested_context(
    requests: list[dict],
    *,
    prior_states: list[tuple[int, UUID, dict, str]],
    bridge=None,
) -> list[dict]:
    """Resolve a v1 requested_context list using existing memory tools."""
    from hamutay.tools.memory import tool_compare, tool_recall

    context = validate_requested_context(requests)
    results: list[dict] = []
    for request in context:
        params = {k: v for k, v in request.items() if k != "tool"}
        if request["tool"] == "recall":
            result = tool_recall(params, prior_states=prior_states, bridge=bridge)
        elif request["tool"] == "compare":
            result = tool_compare(params, prior_states=prior_states)
        else:
            result = {"error": f"Unsupported context tool: {request['tool']}"}
        results.append({"request": request, "result": result})
    return results


def build_event_envelope(event: dict, context_results: list[dict], run_id: str) -> str:
    """Build the explicit user-message envelope for a wake cycle."""
    envelope = {
        "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
        "event_id": event["event_id"],
        "run_id": run_id,
        "scheduled_by_cycle": event.get("scheduled_by_cycle"),
        "scheduled_by_record_id": event.get("scheduled_by_record_id"),
        "purpose": event.get("purpose", ""),
        "requested_context": event.get("requested_context", []),
        "context_results": context_results,
        "instruction": (
            "This is a self-scheduled reflection event. Use the provided "
            "context to decide whether to revise, preserve, defer, or "
            "declare losses. End the cycle with think_and_respond."
        ),
    }
    return json.dumps(envelope, indent=2, default=str)


def run_next_event(session, store: EventStore) -> dict:
    """Run the oldest pending event once using an OpenTasteSession."""
    event = store.next_pending()
    if event is None:
        return {"status": "none", "message": "no pending events"}
    if is_expired(event):
        return store.append_expired(event)

    running = store.append_running(event)
    run_id = running["run_id"]
    try:
        context_results = resolve_requested_context(
            event.get("requested_context", []),
            prior_states=session._prior_states,
            bridge=session._bridge,
        )
        envelope = build_event_envelope(event, context_results, run_id)
        response = session.exchange(envelope, force_memory=None)
        return store.append_completed(
            event=event,
            run_id=run_id,
            wake_cycle=session.cycle,
            result_record_id=session._prior_states[-1][1],
            response_text=response,
        )
    except Exception as e:
        store.append_failed(event=event, run_id=run_id, exc=e)
        raise


def main() -> None:
    import argparse
    import os

    from hamutay.taste_open import (
        AnthropicTasteBackend,
        OpenAITasteBackend,
        OpenTasteSession,
    )

    parser = argparse.ArgumentParser(
        description="Run one pending taste_open scheduled event."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-next")
    run.add_argument("--log-path", required=True)
    run.add_argument("--event-log-path", default=None)
    run.add_argument("--model", default="claude-haiku-4-5")
    run.add_argument(
        "--provider",
        choices=["anthropic", "openrouter", "openai"],
        default="anthropic",
    )
    run.add_argument("--base-url", default=None)
    run.add_argument("--api-key", default=None)
    run.add_argument("--project-root", default=".")
    args = parser.parse_args()

    backend = None
    if args.provider == "anthropic":
        backend = AnthropicTasteBackend()
    else:
        if args.provider == "openrouter":
            base_url = args.base_url or "https://openrouter.ai/api/v1"
            api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
            extra_headers = {
                "X-Title": "hamutay/event-runner",
                "HTTP-Referer": "https://github.com/fsgeek/hamutay",
            }
        else:
            base_url = args.base_url or "https://api.openai.com/v1"
            api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
            extra_headers = {}
        if not api_key:
            raise SystemExit(
                f"No API key for {args.provider}: pass --api-key or set env"
            )
        backend = OpenAITasteBackend(
            base_url=base_url,
            api_key=api_key,
            extra_headers=extra_headers,
            provider_name=args.provider,
        )

    event_log_path = args.event_log_path or str(default_event_log_path(args.log_path))
    session = OpenTasteSession(
        model=args.model,
        backend=backend,
        log_path=args.log_path,
        event_log_path=event_log_path,
        resume=True,
        enable_tools=True,
        project_root=Path(args.project_root),
    )
    result = run_next_event(session, EventStore(event_log_path))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
