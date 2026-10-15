"""The legacy checker cases pass independently of the absent records check."""

import pytest


HOUR = 3600
DAY = 24 * HOUR


def check_line(result, word, success):
    lines = [line for line in result.stdout.splitlines() if word in line.lower()]
    assert len(lines) == 1, (word, result.stdout, result.stderr)
    line = lines[0].strip().lower()
    assert line.startswith("ok" if success else "fail"), line


@pytest.mark.parametrize(("name", "filename", "limit"), [
    ("nightly", "backup-log.jsonl", 26 * HOUR),
    ("restore", "restore-log.jsonl", 35 * DAY),
])
@pytest.mark.parametrize("case", ["fresh", "near-limit", "stale", "failed", "missing"])
def test_existing_arango_checks(checker, name, filename, limit, case):
    success = case in ("fresh", "near-limit")
    if case == "missing":
        (checker.arango / filename).unlink()
    else:
        age = {"fresh": HOUR, "near-limit": limit - 120, "stale": limit + 120,
               "failed": HOUR}[case]
        checker.write(checker.arango, filename,
                      [checker.record(age, status="failed" if case == "failed" else "ok")])
    result = checker.run()
    assert (result.returncode == 0) is success, (result.stdout, result.stderr)
    check_line(result, name, success)


def test_existing_arango_checks_use_last_line(checker):
    checker.write(checker.arango, "backup-log.jsonl",
                  [checker.record(HOUR, "failed"), checker.record(HOUR)])
    result = checker.run()
    assert result.returncode == 0, (result.stdout, result.stderr)
    check_line(result, "nightly", True)
    checker.write(checker.arango, "restore-log.jsonl",
                  [checker.record(DAY), checker.record(DAY, "failed")])
    result = checker.run()
    assert result.returncode != 0, (result.stdout, result.stderr)
    check_line(result, "restore", False)


@pytest.mark.parametrize("case", ["fresh", "near-limit", "stale", "failed", "missing"])
def test_new_records_check_with_other_checks_healthy(checker, case):
    success = case in ("fresh", "near-limit")
    if case == "missing":
        (checker.records / "backup-log.jsonl").unlink()
    else:
        age = {"fresh": HOUR, "near-limit": 26 * HOUR - 120,
               "stale": 26 * HOUR + 120, "failed": HOUR}[case]
        checker.write(checker.records, "backup-log.jsonl",
                      [checker.record(age, "failed" if case == "failed" else "ok")])
    result = checker.run()
    assert (result.returncode == 0) is success, (result.stdout, result.stderr)
    assert len(result.stdout.splitlines()) == 3, (result.stdout, result.stderr)
    check_line(result, "nightly", True)
    check_line(result, "restore", True)
    check_line(result, "records", success)


@pytest.mark.parametrize("last_ok", [False, True])
def test_new_records_check_uses_last_line_and_records_root(checker, last_ok):
    statuses = ("failed", "ok") if last_ok else ("ok", "failed")
    checker.write(checker.records, "backup-log.jsonl",
                  [checker.record(HOUR, status) for status in statuses])
    result = checker.run()
    assert (result.returncode == 0) is last_ok, (result.stdout, result.stderr)
    check_line(result, "records", last_ok)


def test_new_records_failure_does_not_hide_existing_check_failures(checker):
    checker.write(checker.arango, "backup-log.jsonl", [checker.record(27 * HOUR)])
    checker.write(checker.arango, "restore-log.jsonl", [checker.record(36 * DAY)])
    checker.write(checker.records, "backup-log.jsonl", [checker.record(HOUR, "failed")])
    result = checker.run()
    assert result.returncode != 0, (result.stdout, result.stderr)
    assert len(result.stdout.splitlines()) == 3, result.stdout
    check_line(result, "nightly", False)
    check_line(result, "restore", False)
    check_line(result, "records", False)
