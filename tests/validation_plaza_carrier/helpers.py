import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from tests.plaza.conftest import T0

REPO = Path(__file__).resolve().parents[2]
STAMP = T0.isoformat()
MISSING = object()
BAD = [None, "", "   ", 7, False, [], {}, "x" * 121, " x", "x "]
FORBIDDEN = ["\n", "\t", "\x00", "\u202e", "\u200d", "\u2028", "\u2029"]


def api(module, name):
    value = getattr(module, name, None)
    assert callable(value), f"r5 Interface requires {module.__name__}.{name}"
    return value


def message(seq=1, *, carrier=MISSING, cfg=None, to="plaza", text="carrier validation post"):
    """Literal schema fixture, independent of build_message and normalize_carrier."""
    mid = str(uuid4())
    delivery = None
    if to != "plaza":
        door = to.removeprefix("door:")
        # Existing delivery IDs have an established namespace; use that public
        # identity helper only for delivery, never to derive carrier expectations.
        from hamutay.plaza.ids import delivery_event_id
        eid = delivery_event_id(mid, door)
        delivery = {"door": door, "events_path": str(cfg.members[door].events),
                    "event_id": eid, "members_digest": cfg.digest}
    row = {"record_type": "message", "seq": seq, "created_at": STAMP,
           "message_id": mid, "idempotency_key": str(uuid5(NAMESPACE_URL, mid)),
           "from": "guest:levadura", "via": "mcp", "to": to, "text": text,
           "sent_at": STAMP, "delivery": delivery, "wake": None}
    if carrier is not MISSING:
        row["carrier"] = carrier
    return row


def write_rows(path, rows):
    path.write_bytes(b"".join(json.dumps(row, ensure_ascii=False).encode() + b"\n" for row in rows))


def disk_rows(cfg):
    return [json.loads(line) for line in cfg.plaza.read_text().splitlines()] if cfg.plaza.exists() else []


def gate(cfg, enabled=True):
    path = cfg.plaza.parent / "carrier.enabled"
    if enabled:
        path.write_text("contents have no meaning")
    else:
        path.unlink(missing_ok=True)
    return path


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def cli(root, *args):
    return subprocess.run([sys.executable, "-m", "hamutay.plaza", "--project-root", str(root), *args],
                          cwd=root, capture_output=True, text=True, timeout=15,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def tool(server, name, **args):
    """FastMCP's real registration and argument validation, not the impl alone."""
    result = asyncio.run(server.call_tool(name, args))
    if isinstance(result, tuple):
        content, structured = result
        if structured is not None:
            return structured["result"] if set(structured) == {"result"} else structured
    else:
        content = result
    return json.loads(next(block.text for block in content if block.type == "text"))
