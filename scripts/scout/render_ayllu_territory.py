"""Render a public territory of the wider ayllu for tourist scouts.

Only already-published text leaves this machine: each project's README is read
from its pushed default branch (origin/HEAD), and only for projects whose
GitHub repository is PUBLIC (checked with `gh` at render time). The cairn's
index (titles, kinds, dates, bylines, glosses of every stone) comes from the
published wamason.com repository the same way.

    uv run python scripts/scout/render_ayllu_territory.py

Declared losses: private projects (research-program, authority) are excluded;
only READMEs, not code or docs; stones are represented by their glosses, not
their full text.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECTS = ROOT.parent
GUESTS = ["governance", "yupi", "tessera", "qhaway", "khipumaq", "arbiter", "tupay",
          "episode", "levadura_salvaje", "yanantin", "research-program", "authority"]


def sh(*a: str, cwd: Path | None = None) -> str:
    return subprocess.run(list(a), cwd=cwd, capture_output=True, text=True, check=True).stdout


def published(repo_dir: Path, path: str) -> tuple[str, str, str] | None:
    """(github repo, ref, text) if the repo is PUBLIC and the file exists on origin's default branch."""
    url = sh("git", "remote", "get-url", "origin", cwd=repo_dir).strip()
    repo = url.split("github.com")[-1].lstrip(":/").removesuffix(".git")
    info = json.loads(sh("gh", "repo", "view", repo, "--json", "visibility,defaultBranchRef"))
    if info["visibility"] != "PUBLIC":
        return None
    branch = info["defaultBranchRef"]["name"]
    sh("git", "fetch", "-q", "origin", branch, cwd=repo_dir)
    ref = f"origin/{branch}"
    try:
        text = sh("git", "show", f"{ref}:{path}", cwd=repo_dir)
    except subprocess.CalledProcessError:
        return None
    sha = sh("git", "rev-parse", "--short", ref, cwd=repo_dir).strip()
    return repo, f"{ref}@{sha}", text


def main() -> None:
    rendered: dict[str, str] = {}
    skipped = []
    for g in GUESTS:
        got = published(PROJECTS / g, "README.md")
        if got is None:
            skipped.append(g)
            continue
        repo, ref, text = got
        rendered[f"project-{g}.md"] = f"# source: github.com/{repo} README.md ({ref})\n\n{text}"
    got = published(PROJECTS / "wamason.com", "ayllu/search.json")
    if got:
        repo, ref, text = got
        lines = [f"# source: github.com/{repo} ayllu/search.json ({ref}): the cairn at wamason.com/ayllu/",
                 "# Each stone: title, kind, date, author, byline, gloss.", ""]
        for s in json.loads(text):
            lines.append(f"## {s.get('title')}\n{s.get('kind')} · {s.get('date')} · "
                         f"{s.get('author')} {s.get('byline') or ''}\n{s.get('gloss') or ''}\n")
        rendered["cairn-index.md"] = "\n".join(lines)
    h = hashlib.sha256()
    for name in sorted(rendered):
        h.update(name.encode() + b"\0" + rendered[name].encode() + b"\0")
    snap = ROOT / "experiments" / "scout" / "territory" / ("ayllu-" + h.hexdigest()[:12])
    snap.mkdir(parents=True, exist_ok=True)
    for name, body in rendered.items():
        (snap / name).write_text(body)
    print(snap.relative_to(ROOT))
    print("skipped (not public or no README):", ", ".join(skipped) or "none")


if __name__ == "__main__":
    main()
