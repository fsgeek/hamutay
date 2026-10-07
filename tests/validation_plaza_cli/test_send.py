import json
import os
import subprocess
import sys

import pytest

from hamutay.plaza.read import read_rows


def _run(root, *args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "hamutay.plaza", "--project-root", str(root), *args],
        cwd=cwd or root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=15,
    )


@pytest.mark.parametrize("to", ["plaza", "elder"])
def test_inline_text_is_persisted_verbatim_and_uses_the_cli_send_path(house, to):
    root, cfg, _ = house
    text = '  Hello, elder. "quoted" $literal; π\nSecond line\n'
    result = _run(root, "send", "--by", "tony", "--to", to, "--text", text)
    assert result.returncode == 0, result.stderr
    reply = json.loads(result.stdout)
    assert reply["sent"] is True
    assert reply["delivery"] == ("post" if to == "plaza" else "landed")
    rows = read_rows(cfg)
    assert len(rows) == 1
    assert rows[0]["text"] == text
    assert rows[0]["from"] == "tony" and rows[0]["via"] == "cli"
    assert rows[0]["to"] == ("plaza" if to == "plaza" else "door:elder")
    assert cfg.members["elder"].events.exists() is (to == "elder")


@pytest.mark.parametrize("file_kind", ["relative", "absolute"])
def test_text_file_resolution_and_content_are_preserved(house, tmp_path, file_kind):
    root, cfg, _ = house
    text = '  Text from the project file.\n"quotes" and ñ\n'
    (root / "message.txt").write_text(text)
    elsewhere = tmp_path / "different-cwd"
    elsewhere.mkdir()
    (elsewhere / "message.txt").write_text("wrong file from current directory")
    file_arg = "message.txt" if file_kind == "relative" else str(root / "message.txt")
    result = _run(root, "send", "--by", "custodian", "--to", "plaza", "--text-file", file_arg, cwd=elsewhere)
    assert result.returncode == 0, result.stderr
    assert read_rows(cfg)[0]["text"] == text


@pytest.mark.parametrize("body", [
    [],
    ["--text", "inline", "--text-file", "message.txt"],
    ["--text-file", "message.txt", "--text", "inline"],
], ids=["neither", "both-inline-first", "both-file-first"])
def test_exactly_one_text_source_is_required_before_any_send_write(house, body):
    root, cfg, _ = house
    (root / "message.txt").write_text("file text")
    before = set(root.rglob("*"))
    result = _run(root, "send", "--by", "tony", "--to", "plaza", *body)
    assert result.returncode == 2
    assert "Traceback" not in result.stdout + result.stderr
    assert "--text" in result.stderr and "--text-file" in result.stderr
    assert set(root.rglob("*")) == before
    assert not cfg.plaza.exists() and not cfg.members["elder"].events.exists()


@pytest.mark.parametrize("text", ["", " \n\t "])
def test_empty_inline_text_is_a_supplied_source_but_is_refused_without_writing(house, text):
    root, cfg, _ = house
    result = _run(root, "send", "--by", "tony", "--to", "plaza", "--text", text)
    assert result.returncode == 2
    assert result.stderr.startswith("send:")
    assert "Traceback" not in result.stderr
    assert not cfg.plaza.exists()
    assert not cfg.plaza.with_suffix(".jsonl.lock").exists()


def test_inline_text_honors_guest_admission_and_idempotency(house_guests):
    root, cfg, _ = house_guests
    args = ("send", "--by", "guest:levadura", "--to", "plaza", "--text", "Guest post", "--key", "guest-key")
    first = _run(root, *args)
    again = _run(root, *args)
    assert first.returncode == again.returncode == 0, first.stderr + again.stderr
    assert json.loads(again.stdout)["duplicate_of_seq"] == json.loads(first.stdout)["seq"]
    assert len(read_rows(cfg)) == 1
    refused = _run(root, "send", "--by", "guest:outsider", "--to", "plaza", "--text", "No admission")
    assert refused.returncode == 2 and "not admitted" in refused.stderr
    assert len(read_rows(cfg)) == 1


def test_send_help_documents_both_text_sources_and_the_relative_path_rule(house):
    root, _, _ = house
    result = _run(root, "send", "--help")
    assert result.returncode == 0
    assert "--text" in result.stdout and "--text-file" in result.stdout
    assert "--project-root" in result.stdout
