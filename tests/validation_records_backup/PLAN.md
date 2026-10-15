# Records backup independent validation plan

Date: 2026-10-15

## Review and scope

The supplied contract has no blocking ambiguity. This suite treats both scripts
as executable interfaces and does not inspect `deploy/backup-records.sh`.
Only files in `tests/validation_records_backup/` are added; no commits are made.
The implementer supplies the real script at `deploy/backup-records.sh` relative
to the repository root. Missing scripts fail assertions, rather than skip or
xfail. The old checker is exercised directly at `deploy/check-backup.sh`.

## Isolation and oracle

- Every invocation sets SRC, LOCAL_ROOT, REMOTE, REMOTE_ROOT and KEEP to safe
  test values, except tests of the safe relative REMOTE_ROOT and KEEP defaults.
  Checker invocations set both LOCAL_ROOT and RECORDS_ROOT.
- HOME, temporary storage, source, local backups, remote home and tool state are
  in pytest temporary directories. The only accepted transport host is
  `records-validation.invalid`. Fake ssh executes shell commands locally with
  the temporary remote HOME and working directory. Remote commands referring
  to the production backup path are rejected.
- Fake rsync translates remote operands and delegates to the actual local
  rsync. Fake scp translates operands and delegates to local cp. No transport
  shim executes a real network tool. File operands outside the temporary test
  tree and unknown hosts are rejected. No default absolute production root or
  default production host is exercised.
- Python hashlib and direct byte comparisons provide independent content and
  manifest oracles. Real sha256sum checks each successful local and remote
  manifest. Source bytes, directory entries, modes and nanosecond mtimes are
  compared before and after every invocation, including failures.
- Repeated runs wait for the next actual UTC second, avoiding collisions
  without replacing date or imposing a timestamp implementation.

## Execution tasks and coverage

1. Build and smoke-test local transport shims, including real rsync hard links,
   local ssh HOME/cwd, local scp, rejection of unknown hosts and outside paths.
2. Exercise successful snapshots: recursive files, empty directories, dotfiles,
   binary data, spaces and Unicode names; exact layout; sorted manifest paths;
   UTC run/finished timestamps; required status fields and types; remote log
   equality; empty sources; configuration and safe relative-root default.
3. Exercise JSONL: multiple valid JSON values, empty files, valid unterminated
   last lines, CRLF, incomplete unterminated tails (including nested paths),
   malformed interior lines, blank interior lines, and newline-terminated
   malformed last lines. Compare partial_tail as a set with no duplicates;
   no ordering is imposed on that array.
4. Exercise repeated runs: one status append per invocation, unchanged local
   and remote files share inodes and have link count > 1, changed files share
   neither inode with their predecessors, removed files disappear from the new
   snapshot, and old snapshots retain their bytes after source edits.
5. Exercise KEEP=1, KEEP=2 and the default 14 with independently seeded local
   and remote histories. Retain by name, not mtime, and preserve directories
   and files outside the `20*Z` run-directory namespace.
6. Exercise source, snapshot, lines, manifest, copy, verify-remote and prune
   failures. Missing sources and invalid JSONL are data failures; snapshot and
   prune failures use filesystem permissions while leaving the log writable.
   A sha256sum shim can fail manifest generation (the only fault test that
   assumes use of that named command). Copy fails at the transport boundary;
   verification corrupts transferred bytes before the real verification.
   Fault markers distinguish activated faults from unrelated failures.
   The manifest fault test intentionally fails if generation bypasses
   sha256sum; adapt that injection if the eventual implementation uses a
   different hash generator, retaining the same observable stage assertions.
7. Check Arango nightly/restore behavior separately from the new records
   behavior. Cover fresh, missing, failed and stale records, near-threshold
   timestamps with a two-minute margin, last-line precedence, independent
   roots, one output line per check, and records-only failures changing exit
   status. Do not require particular human-readable wording beyond identifying
   the check and its success/failure.
8. Run `uv run pytest tests/validation_records_backup -q`, read the exact counts,
   and report expected failures against the absent backup script and old
   checker separately from passing existing-behavior and harness checks.

## Interpretation limits

Manifest sorting means ascending relative pathname order, as with sorted find
input to sha256sum. `bytes` is checked as a nonnegative integer: the contract
does not define its accounting basis. A trailing newline terminates the last
JSON value; an extra blank interior line is invalid. The suite does not require
atomic publication, retries, concurrent-run handling, symlink policy, rollback
of failed snapshots, or a particular failure-status schema beyond status/stage.
It tests permission failures as a non-root user. It does not execute unsafe
production defaults just to validate their spelling.

The requested run is the red validation baseline, not evidence that the unseen
implementation conforms. The implementer must rerun it after supplying both
scripts. Runtime cache locations can be redirected outside the repository to
keep the requested changes confined to this directory.

## Observed baseline

Command: `uv run pytest tests/validation_records_backup -q`

Result: **42 failed, 19 passed in 1.92s** (exit 1).

- `test_backup_records.py`: 34 failures, each asserting the contract script is absent.
- New records-check cases: 8 failures against the old two-check script.
- Existing Arango-check cases: 11 passes.
- Transport/isolation harness checks: 8 passes.
- No skips, xfails or collection/setup errors.

For this workspace's restricted permissions, the command used the existing
project environment with `UV_NO_SYNC=1`, a UV cache under `/tmp`, disabled Python
bytecode writes, and `PYTEST_ADDOPTS='-p no:cacheprovider'`. No repository cache,
environment, dependency or production-script files were changed.
