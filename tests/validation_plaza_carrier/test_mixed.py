"""Spec test 7: mixed history, cursors, repair, checkpoint bytes, gate removal."""
import hashlib
import importlib
import json
import os
import subprocess

from hamutay.plaza import mcp, records
from hamutay.plaza.pass_ import run_plaza_pass
from hamutay.plaza.read import read_rows
from hamutay.plaza.send import send
from tests.plaza.conftest import T0

from .helpers import REPO, api, cli, disk_rows, gate, message, tool, write_rows


def test_mixed_history_validates_reduces_reads_repairs_and_preserves_cursor(house_guests):
    root, cfg, binding = house_guests
    rows = [message(1, text="old"), message(2, carrier="alias", text="new-carrier"),
            message(3, text="new-without"), message(4, cfg=cfg, to="door:elder", carrier="directed-alias")]
    write_rows(cfg.plaza, rows)
    records.validate_plaza(rows, [1, 2, 3, 4])
    view = records.reduce(rows)
    assert [r["seq"] for r in view.messages] == [1, 2, 3, 4]
    assert view.undelivered() == [rows[3]]
    result = cli(root, "read", "--since-seq", "2", "--through-seq", "3")
    assert result.returncode == 0, result.stderr
    read = [json.loads(line) for line in result.stdout.splitlines()]
    assert [r["seq"] for r in read] == [2, 3]
    assert read[0]["carrier"] == "alias" and "carrier" not in read[1]
    server = mcp.build_server(root, "levadura")
    assert tool(server, "plaza_read", since_seq=2, through_seq=3) == read
    assert mcp.plaza_read_impl(root, "levadura", since_seq=2, through_seq=3) == read
    status = mcp.plaza_status_impl(root, "levadura")
    reads_path = cfg.plaza.parent / "reads.jsonl"
    reads_before = reads_path.read_bytes()
    result = cli(root, "pass")
    assert result.returncode == 0, result.stdout + result.stderr
    repaired = json.loads(result.stdout)
    assert repaired["landed"] == [rows[3]["message_id"]]
    assert reads_path.read_bytes() == reads_before
    assert mcp.plaza_status_impl(root, "levadura") == status
    final = disk_rows(cfg)
    records.validate_plaza(final, list(range(1, len(final) + 1)))
    assert final[-1]["record_type"] == "delivery" and "carrier" not in final[-1]
    assert read_rows(cfg)[-1]["truth"]["state"] == "landed"
    events = [json.loads(line) for line in cfg.members["elder"].events.read_text().splitlines()]
    assert events and "directed-alias" not in json.dumps(events)
    second_pass, _ = run_plaza_pass(binding, now=T0)
    assert second_pass["landed"] == []


def test_cursor_coverage_is_identical_for_same_messages_with_carriers(house_guests):
    root, cfg, _ = house_guests
    rows = [message(1), message(2), message(3)]
    write_rows(cfg.plaza, rows)
    mcp.plaza_read_impl(root, "levadura", since_seq=2, through_seq=2)
    before = mcp.plaza_status_impl(root, "levadura")
    for row in rows:
        row["carrier"] = "alias"
    write_rows(cfg.plaza, rows)
    assert mcp.plaza_status_impl(root, "levadura") == before


def test_checkpoint_digests_match_actual_mixed_file_bytes(house_guests):
    root, cfg, _ = house_guests
    write_rows(cfg.plaza, [message(), message(2, carrier="ñ🦙")])
    # Isolated empty git repo satisfies the script's staged-change guard.
    result = subprocess.run(["git", "init", "-q", str(root)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    result = subprocess.run(["bash", str(REPO / "deploy/checkpoint-community-log.sh"),
                             "--root", str(root), "--no-commit"], capture_output=True, text=True,
                            timeout=15, env={**os.environ, "AYLLU_STATE_DIR": str(root / "isolated-state")})
    assert result.returncode == 0, result.stderr
    actual = cfg.plaza.read_bytes()
    expected = f"plaza.jsonl:{hashlib.sha256(actual).hexdigest()}:{len(actual)}"
    assert expected in (cfg.plaza.parent / "CHECKPOINTS.txt").read_text().split()


def test_gate_is_checked_on_every_send_and_removal_preserves_history(house_guests):
    _, cfg, _ = house_guests
    send_module = importlib.import_module("hamutay.plaza.send")
    path = api(send_module, "carrier_gate")(cfg)
    assert path == cfg.plaza.parent / "carrier.enabled"
    for enabled, text in [(False, "before"), (True, "during"), (False, "after")]:
        gate(cfg, enabled)
        assert send(cfg, actor="guest:levadura", via="mcp", to="plaza", text=text, now=T0,
                    carrier="alias")["sent"]
    rows = disk_rows(cfg)
    assert [r.get("carrier") for r in rows] == [None, "alias", None]
    records.validate_plaza(rows, [1, 2, 3])
