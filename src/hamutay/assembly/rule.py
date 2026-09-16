"""consent-v0 (spec §8) and the fail-closed caps (spec §7 step 5)."""
from __future__ import annotations

from .records import OBJECTIONS


def consent_v0(active: dict[str, str | None], *, members: list[str], round_n: int,
               max_rounds: int, quorum: int) -> tuple[str, str]:
    objectors = sorted(m for m, s in active.items() if s in OBJECTIONS)
    if objectors:
        if round_n < max_rounds:
            return "extended", f"objection by {','.join(objectors)}; round {round_n} < {max_rounds}"
        return "unresolved", f"objection by {','.join(objectors)} at final round {round_n}"
    spoke = sorted(m for m, s in active.items() if s is not None)
    if len(spoke) < quorum:
        return "unresolved", f"spoke {len(spoke)} < quorum {quorum}"
    if any(s == "assent" for s in active.values()):
        return "assented", f"no objection; spoke {len(spoke)} >= quorum {quorum}; assents present"
    return "unresolved", "all who spoke abstained"


def apply_caps(outcome: str, *, round_n: int, max_rounds: int, not_offered: list[str],
               running_at_cutoff: list[str], unknown_at_cutoff: list[str]) -> tuple[str, str]:
    if outcome != "assented":
        return outcome, ""
    for name, members in (("not_offered", not_offered), ("running_at_cutoff", running_at_cutoff),
                          ("unknown_at_cutoff", unknown_at_cutoff)):
        if members:
            capped = "extended" if round_n < max_rounds else "unresolved"
            return capped, f"cap:{name}:{','.join(sorted(members))}"
    return outcome, ""
