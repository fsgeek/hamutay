"""Contract validation only; the backup implementation is deliberately unseen."""

import os
import shutil

import pytest

from conftest import payload, run_dirs


def test_full_recursive_snapshot_manifest_status_and_remote_copy(backup):
    backup.write("z.jsonl", b'{"id": 1}\n{"id": 2}\n')
    backup.write("a/deep/events.jsonl", b'{"text": "caf\xc3\xa9"}\n')
    backup.write("a/read me.txt", b"plain text\n")
    backup.write("a/\u03bb.bin", bytes(range(256)))
    backup.write(".hidden", b"hidden contents")
    backup.write("empty.bin", b"")
    (backup.src / "empty-directory" / "nested").mkdir(parents=True)
    row = backup.ok()
    for root in (backup.local, backup.remote):
        assert (root / row["run"] / "community/empty-directory/nested").is_dir()
        assert run_dirs(root) == [row["run"]]
        assert {"community", "MANIFEST.sha256"} <= {p.name for p in (root / row["run"]).iterdir()}


def test_empty_source_still_creates_empty_manifest_and_success_status(backup):
    row = backup.ok()
    assert row["files"] == 0
    for root in (backup.local, backup.remote):
        assert (root / row["run"] / "MANIFEST.sha256").read_bytes() == b""


@pytest.mark.parametrize("remote_root", ["vault/custom-records", "absolute", None],
                         ids=["relative-override", "absolute-override", "relative-default"])
def test_remote_root_configuration(backup, remote_root):
    if remote_root is None:
        backup.env.pop("REMOTE_ROOT")
    elif remote_root == "absolute":
        backup.env["REMOTE_ROOT"] = str(backup.remote_home / "absolute-records")
    else:
        backup.env["REMOTE_ROOT"] = remote_root
    backup.write("config.jsonl", b'{"config": true}\n')
    backup.ok()


def test_environment_paths_with_spaces(backup):
    source = backup.base / "source with spaces"
    local = backup.base / "local with spaces"
    backup.src.rename(source)
    backup.local.rename(local)
    backup.src, backup.local = source, local
    backup.env.update(SRC=str(source), LOCAL_ROOT=str(local), REMOTE_ROOT="vault/records with spaces")
    backup.write("dir with spaces/a.jsonl", b'{}\n')
    backup.ok()


@pytest.mark.parametrize(("contents", "partial"), [
    (b'{}\n[]\nnull\ntrue\n42\n"string"\n', False),
    (b'{}', False),
    (b'{}\n', False),
    (b'', False),
    (b'{}\r\n{"crlf": true}\r\n', False),
    (b'{}\n{"unfinished":', True),
    (b'{"unfinished":', True),
    (b'{}\n[', True),
], ids=["all-json-values", "valid-without-newline", "trailing-newline", "empty",
        "crlf", "incomplete-last", "only-incomplete", "incomplete-array"])
def test_jsonl_valid_lines_and_allowed_unterminated_tail(backup, contents, partial):
    name = "deep/path/events.jsonl"
    backup.write(name, contents)
    backup.ok(partial=[name] if partial else [])


def test_partial_tail_lists_all_and_only_affected_jsonl_files(backup):
    backup.write("z.jsonl", b'{"tail":')
    backup.write("nested/a.jsonl", b'{}\n{"tail":')
    backup.write("valid.jsonl", b'{"complete": true}')
    backup.write("not-jsonl.txt", b'not JSON\nstill not JSON\n')
    backup.ok(partial=["z.jsonl", "nested/a.jsonl"])


@pytest.mark.parametrize("contents", [
    b'not json\n{}\n',
    b'{}\nnot json\n{}\n',
    b'{}\n\n{}\n',
    b'{"unfinished":\n',
    b'{}\n{"unfinished":\n',
    b'not json\n{"unfinished":',
], ids=["invalid-first", "invalid-middle", "blank-middle", "terminated-invalid-only",
        "terminated-invalid-last", "bad-interior-before-partial-tail"])
def test_invalid_jsonl_fails_at_lines_stage(backup, contents):
    backup.write("nested/events.jsonl", contents)
    backup.fails("lines")


def test_hardlinks_changes_deletions_and_old_snapshot_immutability(backup):
    backup.write("unchanged.jsonl", b'{"id": 1}\n')
    backup.write("changed.jsonl", b'{"id": 2}\n')
    backup.write("deleted.bin", b"must remain in historical snapshots")
    first = backup.ok()
    second = backup.ok()
    history = {}
    for root in (backup.local, backup.remote):
        history[root] = payload(root / first["run"] / "community")
        for name in ("unchanged.jsonl", "changed.jsonl", "deleted.bin"):
            older = root / first["run"] / "community" / name
            newer = root / second["run"] / "community" / name
            assert os.path.samefile(older, newer), (root, name, "unchanged files must share an inode")
            assert older.stat().st_nlink > 1 and newer.stat().st_nlink > 1
    # Different size prevents rsync's size/mtime heuristic from hiding this edit.
    backup.write("changed.jsonl", b'{"id": 200, "edited": true}\n')
    (backup.src / "deleted.bin").unlink()
    backup.write("added/new.jsonl", b'[]\n')
    third = backup.ok()
    for root in (backup.local, backup.remote):
        old = root / second["run"] / "community"
        new = root / third["run"] / "community"
        assert os.path.samefile(old / "unchanged.jsonl", new / "unchanged.jsonl")
        assert not os.path.samefile(old / "changed.jsonl", new / "changed.jsonl")
        assert not (new / "deleted.bin").exists()
        assert payload(root / first["run"] / "community") == history[root]
        assert payload(old) == history[root], "source edits mutated the second snapshot"


@pytest.mark.parametrize("keep", [1, 2, None], ids=["keep-one", "keep-two", "default-fourteen"])
def test_prunes_newest_run_directories_on_both_sides_and_preserves_other_entries(backup, keep):
    if keep is None:
        backup.env.pop("KEEP")
        limit = 14
    else:
        backup.env["KEEP"] = str(keep)
        limit = keep
    backup.write("events.jsonl", b'{"old": true}\n')
    local_names = [f"202001{day:02d}T000000Z" for day in range(1, 19)]
    remote_names = [f"202002{day:02d}T000000Z" for day in range(1, 19)]
    backup.seed(backup.local, local_names)
    backup.seed(backup.remote, remote_names)
    for root in (backup.local, backup.remote):
        for name in ("manual-archive", ".keep", "19990101T000000Z"):
            directory = root / name
            directory.mkdir()
            (directory / "sentinel").write_bytes(b"do not prune")
        # A matching *file* must survive: only run directories may be pruned.
        (root / "20200101T010101Z").write_bytes(b"regular file, not a run directory")
    row = backup.ok()
    for root, names in ((backup.local, local_names), (backup.remote, remote_names)):
        assert run_dirs(root) == sorted(names + [row["run"]])[-limit:]
        for name in ("manual-archive", ".keep", "19990101T000000Z"):
            assert (root / name / "sentinel").read_bytes() == b"do not prune"
        assert (root / "20200101T010101Z").read_bytes() == b"regular file, not a run directory"


def test_missing_source_is_logged_as_source_failure(backup):
    shutil.rmtree(backup.src)
    backup.fails("source")


def test_source_file_instead_of_directory_fails_at_source(backup):
    shutil.rmtree(backup.src)
    backup.src.write_bytes(b"not a directory")
    backup.fails("source")


def test_snapshot_creation_failure_is_logged_even_when_directory_is_not_writable(backup):
    backup.write("events.jsonl", b'{}\n')
    (backup.local / "backup-log.jsonl").touch()
    backup.local.chmod(0o500)
    try:
        assert not os.access(backup.local, os.W_OK), "permission fault requires a non-root test user"
        backup.fails("snapshot")
    finally:
        backup.local.chmod(0o700)


@pytest.mark.parametrize(("fault", "stage"), [
    ("manifest", "manifest"), ("copy", "copy"), ("verify", "verify-remote"),
])
def test_injected_failure_is_nonzero_and_logs_the_failing_stage(backup, fault, stage):
    backup.write("events.jsonl", b'{"checksum": "original"}\n')
    backup.env["RECORDS_TEST_FAULT"] = fault
    backup.fails(stage)
    assert (backup.state / f"injected-{fault}").exists(), f"fault {fault} was never activated"


@pytest.mark.parametrize("side", ["local", "remote"])
def test_prune_failure_is_not_reported_as_success(backup, side):
    backup.env["KEEP"] = "1"
    backup.write("events.jsonl", b'{}\n')
    root = backup.local if side == "local" else backup.remote
    old = "20200101T000000Z"
    backup.seed(root, [old])
    protected = root / old / "community"
    protected.chmod(0o500)
    try:
        assert not os.access(protected, os.W_OK), "permission fault requires a non-root test user"
        backup.fails("prune")
    finally:
        if protected.exists():
            protected.chmod(0o700)


def test_failure_appends_after_success_and_next_success_recovers(backup):
    backup.write("events.jsonl", b'{}\n')
    first = backup.ok()
    backup.write("events.jsonl", b'not json\n{}\n')
    backup.fails("lines")
    backup.write("events.jsonl", b'{"recovered": true}\n')
    recovered = backup.ok()
    assert recovered["run"] > first["run"]
