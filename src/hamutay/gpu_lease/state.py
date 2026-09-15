from __future__ import annotations
import fcntl, json, os, re, uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

RESOURCE = "4090"
TTL_RE = re.compile(r"^([0-9]+)([mhd])$")
TTL_MIN, TTL_MAX = timedelta(minutes=1), timedelta(hours=72)


class MalformedState(Exception):
    """A state file exists but cannot be read as what it claims to be."""


@dataclass(frozen=True)
class Paths:
    dir: Path
    @property
    def lock(self): return self.dir / f"{RESOURCE}.lock"
    @property
    def door(self): return self.dir / f"{RESOURCE}.door"
    @property
    def lease(self): return self.dir / f"{RESOURCE}.lease"
    @property
    def quarantine(self): return self.dir / f"{RESOURCE}.quarantine"
    @property
    def tombstones(self): return self.dir / f"{RESOURCE}.tombstones"
    @property
    def ledger(self): return self.dir / f"{RESOURCE}.ledger.jsonl"


def paths(dir: Path | None = None) -> Paths:
    if dir is not None:
        return Paths(Path(dir))
    root = Path(os.environ.get("AYLLU_STATE_DIR") or (Path.home() / ".local" / "state" / "ayllu"))
    return Paths(root / "gpu")


@contextmanager
def locked(p: Paths):
    p.dir.mkdir(parents=True, exist_ok=True)
    with p.lock.open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def write_atomic(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    with tmp.open("w") as f:
        json.dump(obj, f, sort_keys=True)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def parse_instant(s: str) -> datetime:
    parsed = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"instant must carry a UTC offset: {s!r}")
    return parsed.astimezone(timezone.utc)


def parse_ttl(s: str) -> timedelta:
    m = TTL_RE.match(str(s))
    if not m:
        raise ValueError(f"ttl must match ^[0-9]+[mhd]$, got {s!r}")
    n, unit = int(m.group(1)), m.group(2)
    unit_name = {"m": "minutes", "h": "hours", "d": "days"}[unit]
    td = timedelta(**{unit_name: n})
    if not (TTL_MIN <= td <= TTL_MAX):
        raise ValueError(f"ttl must be between 1m and 72h, got {s!r}")
    return td


def scope_unit_for(lease_id: str) -> str:
    return f"ayllu-gpu-{lease_id}.scope"


def _is_uuid(s) -> bool:
    try:
        return str(uuid.UUID(str(s))) == str(s)
    except (ValueError, AttributeError, TypeError):
        return False


@dataclass(frozen=True)
class LeaseView:
    kind: str            # absent | live | expired | malformed
    data: dict | None
    raw: bytes | None


def validate_lease(obj) -> dict:
    """Return the object if it is a well-formed lease; raise ValueError otherwise."""
    if not isinstance(obj, dict) or obj.get("resource") != RESOURCE:
        raise ValueError("resource")
    for key in ("holder", "purpose"):
        if not isinstance(obj.get(key), str) or not obj[key]:
            raise ValueError(key)
    if not _is_uuid(obj.get("lease_id")) or not _is_uuid(obj.get("mutation_id")):
        raise ValueError("ids")
    if not isinstance(obj.get("generation"), int) or isinstance(obj.get("generation"), bool):
        raise ValueError("generation")
    if obj.get("scope_unit") != scope_unit_for(obj["lease_id"]):
        raise ValueError("scope_unit")
    for key in ("since", "expires_at"):
        if key not in obj:
            raise ValueError(key)
        parse_instant(obj[key])
    if "expected_until" in obj:
        parse_instant(obj["expected_until"])
    return obj


def read_lease(p: Paths, now: datetime) -> LeaseView:
    try:
        raw = p.lease.read_bytes()
    except FileNotFoundError:
        return LeaseView("absent", None, None)
    except OSError:
        return LeaseView("malformed", None, b"")
    try:
        data = validate_lease(json.loads(raw))
    except (ValueError, json.JSONDecodeError):
        return LeaseView("malformed", None, raw)
    kind = "live" if now < parse_instant(data["expires_at"]) else "expired"
    return LeaseView(kind, data, raw)


def read_quarantine(p: Paths) -> dict | None:
    try:
        raw = p.quarantine.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as e:
        raise MalformedState(str(e))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise MalformedState(str(e))
    if not isinstance(data, dict) or not data.get("quarantine_id"):
        raise MalformedState("quarantine without id")
    return data


def list_tombstones(p: Paths) -> list[str]:
    if not p.tombstones.is_dir():
        return []
    return sorted(child.name for child in p.tombstones.iterdir())
