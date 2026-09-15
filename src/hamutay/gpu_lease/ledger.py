from __future__ import annotations
import json
from .state import Paths

def append(p: Paths, row: dict) -> dict:
    p.dir.mkdir(parents=True, exist_ok=True)
    row = {"record_type": "gpu_lease", **row}
    with p.ledger.open("a") as f:
        f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        f.flush()
    return row

def rows(p: Paths) -> list[dict]:
    if not p.ledger.exists():
        return []
    out = []
    with p.ledger.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    out.append({"record_type": "gpu_lease", "phase": "corrupt", "raw": line})
    return out

def dangling_intents(all_rows: list[dict]) -> list[dict]:
    outcomes = {r.get("action_id") for r in all_rows if r.get("phase") == "outcome"}
    return [r for r in all_rows if r.get("phase") == "intent" and r.get("action_id") not in outcomes]
