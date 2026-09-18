"""Who is a member, and which heartbeat is which member.
Spec §1: identity and paths come from members.json, never from model input."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .ledger import Ledger

MEMBERS_FILE = Path("community/plaza/members.json")


class MembersMalformed(RuntimeError):
    pass


@dataclass(frozen=True)
class Member:
    name: str
    session: Path
    events: Path

    def snapshot(self) -> dict:
        return {"session": str(self.session), "events": str(self.events)}


@dataclass(frozen=True)
class MembersConfig:
    ledger: Path
    members: dict[str, Member]
    plaza: Path | None = None       # the plaza record; None means the plaza is not enabled
    digest: str = ""                # sha256 of members.json's bytes, for the plaza's records

    def snapshot(self) -> dict:      # member-only, on purpose: the assembly's freeze
        return {name: m.snapshot() for name, m in self.members.items()}


def _inside(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if not p.is_relative_to(root.resolve()):
        raise MembersMalformed(f"path escapes project root: {rel!r}")
    return p


def load_members(project_root: Path) -> MembersConfig | None:
    path = project_root / MEMBERS_FILE
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise MembersMalformed(f"{path}: {e}") from e
    if not isinstance(raw, dict) or not isinstance(raw.get("ledger"), str) \
            or not isinstance(raw.get("members"), dict) or not raw["members"]:
        raise MembersMalformed(f"{path}: expected {{ledger: str, members: {{...}}}}")
    plaza: Path | None = None
    if "plaza" in raw:
        if not isinstance(raw["plaza"], str) or not raw["plaza"]:
            raise MembersMalformed(f"{path}: plaza must be a non-empty string path")
        plaza = _inside(project_root, raw["plaza"])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    members: dict[str, Member] = {}
    for name, spec in raw["members"].items():
        if not isinstance(spec, dict) or not isinstance(spec.get("session"), str) \
                or not isinstance(spec.get("events"), str):
            raise MembersMalformed(f"{path}: member {name!r} needs session and events")
        members[str(name)] = Member(str(name), _inside(project_root, spec["session"]),
                                    _inside(project_root, spec["events"]))

    # Check for duplicate session or events paths across members
    session_paths: dict[Path, str] = {}
    events_paths: dict[Path, str] = {}
    for name, member in members.items():
        if member.session in session_paths:
            raise MembersMalformed(
                f"{path}: session path {member.session} is shared by members {session_paths[member.session]!r} and {name!r}"
            )
        session_paths[member.session] = name
        if member.events in events_paths:
            raise MembersMalformed(
                f"{path}: events path {member.events} is shared by members {events_paths[member.events]!r} and {name!r}"
            )
        events_paths[member.events] = name

    return MembersConfig(ledger=_inside(project_root, raw["ledger"]), members=members,
                        plaza=plaza, digest=digest)


@dataclass(frozen=True)
class AssemblyBinding:
    door: str
    ledger_path: Path
    members: MembersConfig
    project_root: Path

    @property
    def ledger(self) -> Ledger:
        return Ledger(self.ledger_path)

    @property
    def member(self) -> Member:
        return self.members.members[self.door]


def bind(project_root: Path, log_path: Path, event_store_path: Path, *,
         open_snapshots: list[dict] | None = None) -> tuple[AssemblyBinding | None, str]:
    """(binding or None, launch note). Fail closed: any doubt is no binding."""
    try:
        cfg = load_members(project_root)
    except MembersMalformed as e:
        return None, f"assembly: members.json malformed, no binding ({e})"
    if cfg is None:
        return None, "assembly: no members.json, no binding"
    log_abs = Path(log_path).resolve()
    door = next((n for n, m in cfg.members.items() if m.session == log_abs), None)
    if door is None:
        return None, f"assembly: {log_abs} is not a member session path, no binding"
    live = Path(event_store_path).resolve()
    if live != cfg.members[door].events:
        return None, (f"assembly: member {door} configured store path {cfg.members[door].events} "
                      f"differs from the live store path {live}; no binding")
    for snap in open_snapshots or []:
        # I3: an ADDED member would pass a check that only looks at its own door's paths.
        if set(cfg.members) != set(snap):
            added = sorted(set(cfg.members) - set(snap))
            removed = sorted(set(snap) - set(cfg.members))
            detail = ", ".join(filter(None, [f"added {','.join(added)}" if added else "",
                                             f"removed {','.join(removed)}" if removed else ""]))
            return None, (f"assembly: member set changed while a lineage is open ({detail}); "
                          f"no binding")
        mine = snap.get(door)
        if mine and mine != cfg.members[door].snapshot():
            return None, (f"assembly: member {door} paths are frozen while a lineage is open and "
                          f"differ from the open question's snapshot; no binding")
    note = f"assembly: member {door} bound; ledger {cfg.ledger}"
    if cfg.plaza is not None:
        note += f"; plaza: door {door} may send; log {cfg.plaza}"
    return AssemblyBinding(door, cfg.ledger, cfg, Path(project_root).resolve()), note
