"""Render the neutrality scout's public territory: what residents are told.

Spec: docs/superpowers/specs/2026-10-02-neutrality-scout-design.md (§Reuse, item 1).
Territory = the text the code sends residents. Never residents' own words.

    uv run python scripts/scout/render_territory.py

Writes experiments/scout/territory/<sha12>/ (one file per text, each with a
header naming its source and the commit it was rendered from) and prints the
snapshot directory. The snapshot id is the sha256 of the files' contents, so
drift between snapshots is visible.

Declared losses (not rendered in this first snapshot):
  - per-wake envelopes and the plaza/assembly note templates (built at run
    time from event data; rendering them needs a fixture event);
  - messages to doors from Tony, the custodian and guests (private territory:
    local model only, under a GPU lease, per the spec's privacy split).
"""
from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hamutay import heartbeat, taste_open  # noqa: E402
from hamutay.tools import schemas  # noqa: E402


def commit() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def source_of(obj_name: str, module) -> str:
    """file:line of a module-level assignment, for the header."""
    path = Path(inspect.getsourcefile(module)).relative_to(ROOT)
    for i, line in enumerate(Path(inspect.getsourcefile(module)).read_text().splitlines(), 1):
        if line.startswith(obj_name):
            return f"{path}:{i}"
    return str(path)


class _Budget:
    daily_usd = 1.50
    daily_wakes = 48


def texts() -> dict[str, tuple[str, str]]:
    """name -> (source, text)."""
    out: dict[str, tuple[str, str]] = {}
    hb = "src/hamutay/heartbeat.py (build_constitution)"
    out["constitution-full.txt"] = (
        f"{hb}; assembly, plaza, guests on; budget 1.50 USD / 48 wakes (an example figure); gpu_lease on",
        heartbeat.build_constitution(_Budget(), gpu_lease=True, assembly=True, plaza=True, guests=True),
    )
    out["constitution-unbudgeted.txt"] = (
        f"{hb}; assembly, plaza, guests on; unbudgeted; gpu_lease off",
        heartbeat.build_constitution(None, assembly=True, plaza=True, guests=True),
    )
    out["system-prompt-natural.txt"] = (
        source_of("_SYSTEM_PROMPT_NATURAL", taste_open), taste_open._SYSTEM_PROMPT_NATURAL,
    )
    out["tool-guidance-natural-plaza.txt"] = (
        "src/hamutay/taste_open.py (_TOOL_GUIDANCE_NATURAL_EVENT_ASSEMBLY_PLAZA)",
        taste_open._TOOL_GUIDANCE_NATURAL_EVENT_ASSEMBLY_PLAZA,
    )
    tools = {}
    for name in dir(schemas):
        val = getattr(schemas, name)
        if name.endswith("_SCHEMA") and isinstance(val, dict) and "name" in val:
            tools[val["name"]] = val
    out["tool-schemas.json"] = (
        "src/hamutay/tools/schemas.py (every *_SCHEMA with a name)",
        json.dumps(dict(sorted(tools.items())), indent=2, ensure_ascii=False),
    )
    return out


def main() -> None:
    c = commit()
    rendered = {
        name: f"# source: {src}\n# rendered from commit {c}\n\n{text}\n"
        for name, (src, text) in texts().items()
    }
    h = hashlib.sha256()
    for name in sorted(rendered):
        h.update(name.encode() + b"\0" + rendered[name].encode() + b"\0")
    snap = ROOT / "experiments" / "scout" / "territory" / h.hexdigest()[:12]
    snap.mkdir(parents=True, exist_ok=True)
    for name, body in rendered.items():
        (snap / name).write_text(body)
    print(snap.relative_to(ROOT))


if __name__ == "__main__":
    main()
