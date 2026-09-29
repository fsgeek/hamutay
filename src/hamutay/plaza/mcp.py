"""A guest's three tools over the plaza (spec §11 r6): stateless, label fixed at start."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from hamutay.assembly.binding import MembersMalformed, load_members
from hamutay.assembly.ledger import LedgerMalformed, LedgerUnavailable

from .ids import GUEST_LABEL_RE
from .read import read_rows
from .send import SendRefused, send

CAP_SENTENCE = ("At most 48 messages to doors per UTC day under this label, across every session; posts are not "
                "counted. A `key` (token) makes a retry one message: keep it for retries, change it for an "
                "intentional repeat; without one every call is a new message.")


def _cfg(root: Path):
    """Reload members.json on every call: admission is never cached (spec §11 r6)."""
    cfg = load_members(root)
    if cfg is None or cfg.plaza is None:
        raise SendRefused("the plaza is not enabled for this house")
    return cfg


def _refused(e: Exception) -> dict:
    return {"sent": False, "refused": f"{type(e).__name__}: {e}"}


def plaza_read_impl(root: Path, label: str, since_seq: int | None = None, through_seq: int | None = None,
                    posts_only: bool = False) -> list[dict]:
    try:
        cfg = _cfg(root)
    except (SendRefused, MembersMalformed):
        return []
    return read_rows(cfg, since_seq=since_seq, through_seq=through_seq, posts_only=posts_only)


def plaza_send_impl(root: Path, label: str, to: str, text: str, key: str | None = None) -> dict:
    try:
        cfg = _cfg(root)
        return send(cfg, actor=f"guest:{label}", via="mcp", to=to, text=text,
                    now=datetime.now(timezone.utc), key=key)
    except (SendRefused, MembersMalformed, LedgerUnavailable, LedgerMalformed, ValueError) as e:
        return _refused(e)


def plaza_post_impl(root: Path, label: str, text: str, key: str | None = None) -> dict:
    return plaza_send_impl(root, label, "plaza", text, key=key)


def build_server(project_root: Path, label: str):
    from mcp.server.fastmcp import FastMCP
    if not GUEST_LABEL_RE.fullmatch(label):
        raise ValueError(f"bad guest label {label!r}")
    root = Path(project_root).resolve()
    server = FastMCP("hamutay-plaza")

    @server.tool(description=(
        f"Read the plaza record as guest:{label}: message rows in seq order with delivery truth. "
        "since_seq and through_seq are inclusive; resume at your last seq plus one; an empty interval "
        "returns []. No page or byte ceiling: bound your own read with through_seq."))
    def plaza_read(since_seq: int | None = None, through_seq: int | None = None, posts_only: bool = False) -> list[dict]:
        return plaza_read_impl(root, label, since_seq=since_seq, through_seq=through_seq, posts_only=posts_only)

    @server.tool(description=(
        f"Post to the plaza as guest:{label}; wakes no one; every resident and Tony can read it. {CAP_SENTENCE}"))
    def plaza_post(text: str, key: str | None = None) -> dict:
        return plaza_post_impl(root, label, text, key=key)

    @server.tool(description=(
        f"Send to one door as guest:{label} (a name from members.json); the door wakes on it when its own "
        f"quiet allows; nothing obliges a reply. {CAP_SENTENCE}"))
    def plaza_send(to: str, text: str, key: str | None = None) -> dict:
        return plaza_send_impl(root, label, to, text, key=key)

    return server


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hamutay.plaza.mcp")
    p.add_argument("--project-root", default=".")
    p.add_argument("--guest", required=True, help="the guest label, fixed for this server's life")
    a = p.parse_args(argv)
    build_server(Path(a.project_root), a.guest).run()      # stdio
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
