"""The plaza's ids, spelled once (spec §2)."""
from __future__ import annotations

import hashlib
import re
import uuid

PLAZA_NS = uuid.uuid5(uuid.NAMESPACE_URL, "hamutay:plaza")

# The plan's Global Constraints name these once: every plaza-lock acquisition and
# every event-store acquisition on the plaza path is bounded by them. Defined here,
# imported everywhere -- four definitions of two numbers is three too many.
PLAZA_LOCK_WINDOW_S = 2.0
STORE_LOCK_WINDOW_S = 2.0
DOOR_RE = re.compile(r"^door:[a-z0-9_-]+$")
HUMANS = ("tony", "custodian")


def is_door(actor: str) -> bool:
    return bool(DOOR_RE.match(str(actor)))


def door_name(actor: str) -> str:
    if not is_door(actor):
        raise ValueError(f"not a door: {actor!r}")
    return actor[len("door:"):]


def canonical_to(s: str) -> str:
    s = str(s).strip()
    if s == "plaza":
        return s
    if is_door(s):
        return s
    if re.match(r"^[a-z0-9_-]+$", s):
        return f"door:{s}"
    raise ValueError(f"to must be a door name, door:<name>, or plaza; got {s!r}")


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def resident_key(source_event_id: str, to: str, text: str) -> str:
    return str(uuid.uuid5(PLAZA_NS, f"{source_event_id}\0{canonical_to(to)}\0{sha256_text(text)}"))


def cli_key(key: str) -> str:
    if not str(key):
        raise ValueError("key must be non-empty")
    return str(uuid.uuid5(PLAZA_NS, f"cli\0{key}"))


GUEST_LABEL_RE = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
GUEST_RE = re.compile(r"^guest:([a-z][a-z0-9-]{1,31})$")


def is_guest(actor: str) -> bool:
    return bool(GUEST_RE.match(str(actor)))


def guest_label(actor: str) -> str:
    m = GUEST_RE.match(str(actor))
    if not m:
        raise ValueError(f"not a guest: {actor!r}")
    return m.group(1)


def guest_key(label: str, token: str) -> str:
    """Invariant 3 (r7): a guest's key is namespaced by its label, never shared with the humans'."""
    if not GUEST_LABEL_RE.match(str(label)):
        raise ValueError(f"bad guest label {label!r}")
    if not str(token):
        raise ValueError("token must be non-empty")
    return str(uuid.uuid5(PLAZA_NS, f"guest:{label}\0{token}"))


def delivery_event_id(message_id: str, door: str) -> str:
    return str(uuid.uuid5(PLAZA_NS, f"{message_id}\0door:{door}"))
