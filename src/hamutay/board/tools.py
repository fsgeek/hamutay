"""The door tools: board_read, board_post, set_board_filter, clear_board_filter, board_pass (contract §10).

Offered only on an event-managed wake bound to the assembly with the plaza set
AND the gate file present (checked at the start of each exchange). Identity --
which door is writing, which store holds its filter -- comes from the binding,
never from model input.
"""
from __future__ import annotations

from datetime import datetime, timezone

from hamutay.assembly.ledger import LedgerMalformed, LedgerUnavailable
from hamutay.events import EventStore, LeaseGateRequired, StoreUnavailable

from .filters import FilterRefused, clear_filter, pass_entry, set_filter
from .ids import board_enabled
from .write import BoardRefused, add_note, post_opening, read_entries, set_status

BOARD_TOOL_NAMES = ("board_read", "board_post", "set_board_filter", "clear_board_filter", "board_pass")
_ERRORS = (BoardRefused, FilterRefused, LedgerUnavailable, LedgerMalformed, StoreUnavailable,
           LeaseGateRequired, OSError, ValueError, TypeError)


def run_board_tool(name: str, tool_input: dict, *, binding, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    root = binding.project_root
    if not board_enabled(root):
        return {"error": f"{name}: the board is not enabled in this house"}
    door = binding.door
    me = f"door:{door}"
    try:
        if name == "board_read":
            return read_entries(root, opportunity_id=tool_input.get("opportunity_id"),
                                include_closed=bool(tool_input.get("include_closed", False)),
                                since_seq=tool_input.get("since_seq"))
        if name == "board_post":
            rt = tool_input.get("record_type") or "opening"
            if rt == "opening":
                return post_opening(root, by=me, title=tool_input.get("title"), what=tool_input.get("what"),
                                    kind=tool_input.get("kind"), why=tool_input.get("why", ""),
                                    help_wanted=tool_input.get("help_wanted", ""), tags=tool_input.get("tags"),
                                    owner=tool_input.get("owner"),
                                    record_of_help=tool_input.get("record_of_help", ""), now=now)
            if rt == "note":
                return add_note(root, by=me, opportunity_id=tool_input.get("opportunity_id"),
                                text=tool_input.get("text"), now=now)
            if rt == "status":
                return set_status(root, by=me, opportunity_id=tool_input.get("opportunity_id"),
                                  status=tool_input.get("status"), reason=tool_input.get("reason", ""), now=now)
            return {"error": f"board_post: record_type must be opening, note or status; got {rt!r}"}
        store = EventStore(binding.member.events)
        if name == "set_board_filter":
            raw = {k: tool_input.get(k) for k in ("kinds", "tags_any", "owners_any", "keywords_any")
                   if k in tool_input}
            extra = sorted(set(tool_input) - {"kinds", "tags_any", "owners_any", "keywords_any", "reason"})
            if extra:
                return {"error": f"set_board_filter: unknown field(s) {extra}"}
            out = set_filter(store, door, raw, now)
            # r2 §2: setting a filter scans the open entries at once (the heartbeat's
            # pass would within a poll; this makes the answer immediate and countable)
            from .pass_ import run_board_pass
            res, _ = run_board_pass(door=door, project_root=root, store=store, now=now)
            if res.get("error"):
                out["scan_error"] = res["error"]
            else:
                out["queued_now"] = res.get("queued", 0)
            return out
        if name == "clear_board_filter":
            return clear_filter(store, door, now)
        if name == "board_pass":
            oid = tool_input.get("opportunity_id")
            if not isinstance(oid, str) or not oid.strip():
                return {"error": "board_pass: opportunity_id is required"}
            return pass_entry(store, door, oid.strip(), now)
    except _ERRORS as e:
        return {"error": f"{name}: {e}"}
    return {"error": f"{name}: not a board tool"}
