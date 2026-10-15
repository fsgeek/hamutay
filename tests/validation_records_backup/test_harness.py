"""Smoke checks for the isolation machinery, independent of production scripts."""

import os

import pytest


def test_ssh_runs_locally_in_the_temporary_remote_home(backup):
    result = backup.tool("ssh", "-o", "BatchMode=yes", "records-validation.invalid",
                         'printf "%s\\n" "$HOME" "$PWD"')
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [str(backup.remote_home)] * 2


def test_rsync_passthrough_maps_remote_destination_and_preserves_link_dest(backup):
    backup.write("payload", b"real bytes through real rsync\n")
    for destination, options in (("first", []), ("second", ["--link-dest=../first"])):
        result = backup.tool("rsync", "-a", *options, f"{backup.src}/",
                             f"records-validation.invalid:{destination}/")
        assert result.returncode == 0, result.stderr
    first = backup.remote_home / "first/payload"
    second = backup.remote_home / "second/payload"
    assert first.read_bytes() == b"real bytes through real rsync\n"
    assert os.path.samefile(first, second) and first.stat().st_nlink > 1


def test_scp_maps_destination_without_network_access(backup):
    source = backup.write("payload", b"scp payload")
    result = backup.tool("scp", "-q", str(source), "records-validation.invalid:copied")
    assert result.returncode == 0, result.stderr
    assert (backup.remote_home / "copied").read_bytes() == b"scp payload"


@pytest.mark.parametrize("tool", ["ssh", "rsync", "scp"])
def test_transport_rejects_unknown_hosts(backup, tool):
    source = backup.write("payload", b"must stay local")
    args = (["unconfigured.invalid", "true"] if tool == "ssh"
            else [str(source), "unconfigured.invalid:payload"])
    result = backup.tool(tool, *args)
    assert result.returncode == 96, (result.stdout, result.stderr)
    assert "refused" in result.stderr


def test_rsync_rejects_paths_outside_the_temporary_tree(backup):
    source = backup.write("payload", b"must stay local")
    result = backup.tool("rsync", str(source), "/outside-validation-tree/payload")
    assert result.returncode == 96, result.stderr
    assert "outside temporary tree" in result.stderr


def test_verification_fault_changes_transferred_bytes_not_the_source(backup):
    backup.write("events.jsonl", b'{}\n')
    name = "20260101T000000Z"
    backup.seed(backup.local, [name])
    backup.remote.mkdir(parents=True)
    backup.env["RECORDS_TEST_FAULT"] = "verify"
    result = backup.tool("rsync", "-a", f"{backup.local}/{name}/",
                         f"records-validation.invalid:backups/records/{name}/")
    assert result.returncode == 0, result.stderr
    assert (backup.state / "injected-verify").exists()
    assert (backup.src / "events.jsonl").read_bytes() == b'{}\n'
    assert (backup.remote / name / "community/events.jsonl").read_bytes() != b'{}\n'
