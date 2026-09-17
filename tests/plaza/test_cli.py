import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

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
    send(cfg, actor="door:elder", via="tool", to="plaza", text="post", now=T0 + timedelta(minutes=1), wake=_wake("11111111-1111-4111-8111-111111111111"))
    send(cfg, actor="door:elder", via="tool", to="fable", text="e→f", now=T0 + timedelta(minutes=2), wake=_wake("22222222-1111-4111-8111-111111111111"))
    rows = [json.loads(l) for l in _cli(root, "read").stdout.splitlines()]
    assert [r["text"] for r in rows] == ["hello door", "post", "e→f"] and rows[0]["truth"]["state"] == "landed"
    rows = [json.loads(l) for l in _cli(root, "read", "--since-seq", "3", "--through-seq", "4", "--for", "qwen").stdout.splitlines()]
    assert [r["text"] for r in rows] == ["post", "e→f"]
    rows = [json.loads(l) for l in _cli(root, "read", "--for", "fable").stdout.splitlines()]
    assert [r["text"] for r in rows] == ["hello door", "post"]           # e→f is mail to fable: excluded
    rows = [json.loads(l) for l in _cli(root, "read", "--posts").stdout.splitlines()]
    assert [r["text"] for r in rows] == ["post"]
    st = json.loads(_cli(root, "status").stdout)
    assert st["valid"] is True and st["sent_today"] == {"tony": 1, "door:elder": 1} and st["undelivered"] == []


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
