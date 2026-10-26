"""The board's names, paths, labels and ids, spelled once (board v0 contract §1, §4)."""
from __future__ import annotations

import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hamutay.plaza.ids import HUMANS, is_door, is_guest

# A fixed namespace of the board's own, distinct from the plaza's
# (uuid5(NAMESPACE_URL, "hamutay:plaza")) and every other uuid5 namespace in
# src/hamutay. Its value is part of the contract: e095e4d0-cfce-5dc7-86c8-4e7a231df71b.
NS_BOARD = uuid.uuid5(uuid.NAMESPACE_URL, "hamutay:board")

BOARD_DIR = Path("community") / "board"
BOARD_FILE = "board.jsonl"
GATE_FILE = "board.enabled"
BOARD_LOCK_WINDOW_S = 2.0
STORE_LOCK_WINDOW_S = 2.0

EVENT_TYPE_BOARD_MATCH = "board_match"
ONBOARDING_LABEL = "board:onboarding"


def board_dir(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / BOARD_DIR


def board_path(project_root: str | Path) -> Path:
    return board_dir(project_root) / BOARD_FILE


def gate_path(project_root: str | Path) -> Path:
    """While this file is absent the board is dormant (contract §2). Content ignored; checked at use."""
    return board_dir(project_root) / GATE_FILE


def board_enabled(project_root: str | Path) -> bool:
    return gate_path(project_root).exists()


def norm(s: str) -> str:
    """The one normalization, identical on write and on filter: NFKC, case-fold, trim."""
    return unicodedata.normalize("NFKC", s).casefold().strip()


def is_label(s: object) -> bool:
    """Canonical labels: tony, custodian, door:<name>, guest:<label>."""
    return isinstance(s, str) and (s in HUMANS or is_door(s) or is_guest(s))


def canonical_label(raw: object) -> str:
    if not isinstance(raw, str):
        raise ValueError("a label must be a string")
    s = norm(raw)
    if not is_label(s):
        raise ValueError(f"not a canonical label (tony, custodian, door:<name>, guest:<label>): {raw!r}")
    return s


def match_event_id(door: str, board_seq: int, generation: int, attempt: int) -> str:
    return str(uuid.uuid5(NS_BOARD, f"{door}:{board_seq}:g{generation}:a{attempt}"))


def onboarding_event_id(door: str) -> str:
    return str(uuid.uuid5(NS_BOARD, f"{door}:onboarding"))


def utc_day(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).date().isoformat()


def next_utc_midnight(now: datetime) -> datetime:
    u = now.astimezone(timezone.utc)
    return (u + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
