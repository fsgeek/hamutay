"""Convening (spec §3). One locked write path for the CLI and the tool."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from .binding import MembersConfig
from .ledger import Ledger, iso
from .records import build_procedure, build_question, payload_sha256, reduce, sha256_text

MIN_CLOSES_IN = timedelta(hours=24)
MAX_CLOSES_IN = timedelta(days=30)

_CLOSES_IN_RE = re.compile(r"^([0-9]+)([mhd])$")


def parse_closes_in(s: str) -> timedelta:
    """A duration like 7d, 48h, 90m. Bounds are convene()'s (MIN_CLOSES_IN..MAX_CLOSES_IN), not this parser's."""
    m = _CLOSES_IN_RE.match(str(s).strip())
    if not m:
        raise ValueError(f"closes_in must match ^[0-9]+[mhd]$, got {s!r}")
    n, unit = int(m.group(1)), m.group(2)
    return timedelta(**{{"m": "minutes", "h": "hours", "d": "days"}[unit]: n})


class ConveneRefused(RuntimeError):
    pass


def convene(ledger: Ledger, members: MembersConfig, *, convener: str, text: str, closes_in: timedelta,
            now: datetime, proposal_procedure: dict | None = None, artifact: dict | None = None) -> dict:
    if not (MIN_CLOSES_IN <= closes_in <= MAX_CLOSES_IN):
        raise ConveneRefused(f"closes_in must be between {MIN_CLOSES_IN} and {MAX_CLOSES_IN}")
    if not str(text).strip():
        raise ConveneRefused("text is required")
    with ledger.locked():
        view = reduce(ledger.read_unlocked())
        if view.open_lineage_for(convener) is not None:
            raise ConveneRefused(f"{convener} already has an open lineage")
        snapshot = members.snapshot()
        for snap in view.snapshots_of_open_questions():
            # I3: the member SET is frozen too, not only the paths of the doors the
            # snapshot names — an added member would otherwise slip past this check.
            if set(snapshot) != set(snap):
                added = sorted(set(snapshot) - set(snap))
                removed = sorted(set(snap) - set(snapshot))
                detail = ", ".join(filter(None, [f"added {','.join(added)}" if added else "",
                                                 f"removed {','.join(removed)}" if removed else ""]))
                raise ConveneRefused(
                    f"the member set is frozen while a lineage is open ({detail})")
            for door, paths in snap.items():
                if snapshot.get(door) != paths:
                    raise ConveneRefused(f"member paths are frozen while a lineage is open ({door} differs)")
        if proposal_procedure is not None:
            proc = ledger.append_unlocked(build_procedure(
                proposal_procedure, artifact or {}, status="provisional", version=view.next_version()))
            proposal = {"kind": "procedure", "procedure_id": proc["procedure_id"],
                        "sha256": proc["payload_sha256"]}
        else:
            if not view.procedures:
                raise ConveneRefused("no procedure record exists; the first question must propose one")
            proposal = {"kind": "text", "sha256": sha256_text(str(text))}
        q = build_question(text=text, convener=convener, opened_at=iso(now), closes_at=iso(now + closes_in),
                           governing=view.governing_for_new_question(), members_snapshot=snapshot,
                           proposal=proposal)
        if proposal_procedure is not None:
            # the procedure record names the question that proposed it: one more line
            proc2 = dict(proc); proc2.pop("seq"); proc2.pop("created_at")
            proc2["proposed_by_question_id"] = q["question_id"]
            ledger.append_unlocked(proc2)
        return ledger.append_unlocked(q)
