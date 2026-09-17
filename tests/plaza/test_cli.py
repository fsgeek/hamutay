import json
import subprocess
import sys
from datetime import datetime, timezone

from hamutay.assembly.ledger import Ledger, iso
from hamutay.plaza.send import send

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _cli(root, *args):
    return subprocess.run([sys.executable, "-m", "hamutay.plaza", "--project-root", str(root), *args],
                          capture_output=True, text=True)


def _wake(ev):
    return {"cycle": 1, "record_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "event_id": ev,
            "run_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "started_at": iso(T0)}


def test_send_read_status_and_key(house):
    root, cfg, binding = house
    (root / "t.txt").write_text("hello door")
    out = _cli(root, "send", "--by", "tony", "--to", "qwen", "--text-file", "t.txt", "--key", "k1")
    assert out.returncode == 0, out.stderr
    r = json.loads(out.stdout); assert r["delivery"] == "landed" and r["seq"] == 1
    again = json.loads(_cli(root, "send", "--by", "tony", "--to", "qwen", "--text-file", "t.txt", "--key", "k1").stdout)
    assert again["duplicate_of_seq"] == 1
    assert _cli(root, "send", "--by", "someone", "--to", "qwen", "--text-file", "t.txt").returncode == 2
    assert _cli(root, "send", "--by", "tony", "--to", "nobody", "--text-file", "t.txt").returncode == 2
    # The CLI's own "hello door" send above stamped sent_at with the real wall clock (cmd_send
    # has no --now of its own), so these direct send() calls use the real wall clock too --
    # otherwise status's --now could never land on the same UTC day as both actors' sends.
    now = datetime.now(UTC)
    send(cfg, actor="door:elder", via="tool", to="plaza", text="post", now=now, wake=_wake("11111111-1111-4111-8111-111111111111"))
    send(cfg, actor="door:elder", via="tool", to="fable", text="e→f", now=now, wake=_wake("22222222-1111-4111-8111-111111111111"))
    rows = [json.loads(l) for l in _cli(root, "read").stdout.splitlines()]
    assert [r["text"] for r in rows] == ["hello door", "post", "e→f"] and rows[0]["truth"]["state"] == "landed"
    rows = [json.loads(l) for l in _cli(root, "read", "--since-seq", "3", "--through-seq", "4", "--for", "qwen").stdout.splitlines()]
    assert [r["text"] for r in rows] == ["post", "e→f"]
    rows = [json.loads(l) for l in _cli(root, "read", "--for", "fable").stdout.splitlines()]
    assert [r["text"] for r in rows] == ["hello door", "post"]           # e→f is mail to fable: excluded
    rows = [json.loads(l) for l in _cli(root, "read", "--posts").stdout.splitlines()]
    assert [r["text"] for r in rows] == ["post"]
    st = json.loads(_cli(root, "status", "--now", iso(now)).stdout)
    assert st["valid"] is True and st["sent_today"] == {"tony": 1, "door:elder": 1} and st["undelivered"] == []
    # Without --now, status still runs against the real clock (deterministic: it must always
    # exit 0 and report a sent_today key, whatever it contains on whatever day the suite runs).
    out_default = _cli(root, "status")
    assert out_default.returncode == 0
    assert "sent_today" in json.loads(out_default.stdout)


def test_status_reports_invalid_and_pass_runs(house):
    root, cfg, binding = house
    (root / "t.txt").write_text("x")
    _cli(root, "send", "--by", "custodian", "--to", "elder", "--text-file", "t.txt")
    out = _cli(root, "pass"); assert out.returncode == 0 and json.loads(out.stdout)["units"] == 0
    with cfg.plaza.open("a") as f:
        f.write(json.dumps({"record_type": "note", "seq": 3}) + "\n")
    out = _cli(root, "status"); assert out.returncode == 1 and json.loads(out.stdout)["valid"] is not True


def test_shim_is_executable_and_names_the_module():
    from pathlib import Path
    shim = Path(__file__).resolve().parents[2] / "deploy/ayllu-plaza"
    assert shim.exists() and (shim.stat().st_mode & 0o111)
    assert "python -m hamutay.plaza" in shim.read_text()


def test_read_reports_a_malformed_plaza_cleanly(house):
    """I4: `read` is the command an operator reaches for first when the pass has just
    emitted {"error": "plaza: line N ..."}. cmd_read's _read raises LedgerMalformed
    and main() caught only LedgerUnavailable, so it escaped as a traceback on a
    record the spec says is repaired by hand."""
    root, cfg, binding = house
    (root / "t.txt").write_text("x")
    _cli(root, "send", "--by", "tony", "--to", "qwen", "--text-file", "t.txt")
    with cfg.plaza.open("a") as f:
        f.write(json.dumps({"record_type": "note", "seq": 3}) + "\n")
    out = _cli(root, "read")
    assert out.returncode != 0
    assert "Traceback" not in out.stderr and "Traceback" not in out.stdout
    assert out.stderr.strip().count("\n") == 0                  # one line
    assert out.stderr.startswith("plaza: ") and "line 3" in out.stderr


def test_status_reports_the_cap_actors_at_zero_and_a_physical_line_count(house):
    """M4: the spec's 'per-door sends today against the cap' needs the cap in the
    output, and an actor at zero is a fact, not an omission. M5: on a malformed
    record `records` is reset to [], so seq reported 0 and understated the file."""
    root, cfg, binding = house
    now = datetime.now(UTC)
    send(cfg, actor="door:elder", via="tool", to="fable", text="e2f", now=now,
         wake=_wake("11111111-1111-4111-8111-111111111111"))
    send(cfg, actor="door:qwen", via="tool", to="plaza", text="post", now=now,
         wake=_wake("22222222-1111-4111-8111-111111111111"))
    st = json.loads(_cli(root, "status", "--now", iso(now)).stdout)
    from hamutay.plaza.records import SEND_CAP
    assert st["cap"] == SEND_CAP
    assert st["sent_today"]["door:elder"] == 1
    assert st["sent_today"]["door:qwen"] == 0        # an actor at zero is reported, not dropped

    with cfg.plaza.open("a") as f:
        f.write(json.dumps({"record_type": "note", "seq": 99}) + "\n")
    bad = _cli(root, "status", "--now", iso(now))
    assert bad.returncode == 1
    body = json.loads(bad.stdout)
    assert body["valid"] is not True
    physical = len([ln for ln in cfg.plaza.read_text().splitlines() if ln.strip()])
    assert body["seq"] in (physical, None) and body["seq"] != 0
    assert body["seq"] == physical
