# OpenTimestamps hook validation

Contract: the requested behavior and CLAUDE.md's “Pre-registration” and
“Git signing” sections. Only this test directory is authored; scripts are
copied from the working tree, including uncommitted changes. No commits or
OpenTimestamps network requests are made in the source repository.

1. Build temporary Git repositories with isolated Git configuration and PATH.
   Copy the scripts, omit exactly the installer's `uv pip install` line in a
   temporary copy, and execute the rest to install its real shims. Check both
   shims' full text, executable bits, argument forwarding and reinstall behavior.
2. Use a fake OTS executable that records calls and writes `<file>.ots`, and
   controlled fake LFS executables. Assert proof content, tracked files, commit
   parentage, subject, author/committer identity, repository state and call counts.
3. Exercise ordinary commits, clean merges, resolved conflicts, squash merges,
   fast-forwards and local pulls, pending/anchored duplicate guards, ots subjects,
   missing clients and linked worktrees without their own virtual environment.
4. Probe real Git signing and verification with the specified key. If unavailable,
   skip only the cryptographic signature tests with the probe's diagnostic.
   Behavioral tests still execute: a Git forwarding wrapper recognizes the
   `-m "ots: stamp ..."` message for any subcommand and strips `-S` and
   `-S<keyid>` when the
   probe failed. It never creates or pretends to verify a signature.
5. Run `uv run pytest tests/validation_ots_hooks -q`. Report genuine contract
   failures without changing scripts or marking disagreements as expected failures.

## Contract revision (2026-10-12)

The behavioral contract now requires every stamp to have exactly one parent,
the stamped commit, including ordinary commits, clean `--no-ff` merges,
conflicts resolved with `git commit`, linked worktrees and fast-forward/pull
of an unstamped tip. The earlier first-parent-only assertion missed the
post-merge `MERGE_HEAD` bug (governance, plaza seq 80; real commit 2b08455).

Stamps must be signed by `01193FA2631C8AE8E4DF266E216D3C9B920813A1` even
with `commit.gpgSign=false` and another repository `user.signingkey`.
Both author and committer must be Tony Mason <hamutay@wamason.com>.
Creating a stamp must run no commit-lifecycle hooks: pre-commit,
prepare-commit-msg, commit-msg, post-commit or post-merge. The
reference-transaction observer may fire for the stamp's ref update, but
is not required to fire. Afterwards the index and working tree must be
clean, merge state absent, the active branch must point at the stamp, and
its reflog must contain `ots: stamp <hash>` for the stamp update.

Git subcommands and stamp-creation argv are implementation choices. The
unsigned fallback must support both signing flag forms and any subcommand
with the stamp message; unsigned commits must never count as signed.
All existing guards, squash, LFS ordering/failure, missing-client handling,
worktree client lookup and installer coverage remain required.

Revision steps (execute inline, without commits or edits outside this directory):

- [x] Update `helpers.py`: message-based fallback; exact parent list; clean
  merge state, branch and reflog assertions; remove stamp argv requirements.
- [x] Update `test_hooks.py`: eliminate recursion expectations, record hooks
  behaviorally, and make conflicting signing configuration explicit.
- [x] Add forwarding-shim regression cases under this directory for porcelain
  and plumbing, both signing flag forms, and real unsigned commit objects.
- [x] Run `uv run pytest tests/validation_ots_hooks -q`, inspect exact totals
  and failures against the old implementation, and record the result here.

## Contract point 4 correction (2026-10-12)

Reviewed the correction: no blocking issue. “Creating the stamp runs no Git
hooks” applies to the five commit-lifecycle hooks listed above. Suppressing
reference-transaction would hide the stamp's ref update from observers;
its presence or absence is not a contract assertion.

Correction steps (execute inline, without commits or script edits):

- [x] Keep both parameters, all six recorders and `assert_stamp` in
  `test_stamp_creation_runs_no_git_hooks`; exclude only reference-transaction
  events from the forbidden hook calls and clarify the failure message.
- [x] Run `uv run pytest tests/validation_ots_hooks -q` and record the exact
  counts from this worktree's output, independently of the reported run
  against the unseen new implementation (61 passed, 2 failed, 0 skipped).

## Validation result after the correction (2026-10-12)

Full command (reuse the existing environment without dependency syncing and
keep caches in `/tmp`):

```bash
UV_PROJECT_ENVIRONMENT=/home/tony/projects/hamutay/.venv UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/hamutay-ots-validation-uv-cache PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-o cache_dir=/tmp/hamutay-ots-validation-pytest-cache' uv run pytest tests/validation_ots_hooks -q
```

Actual pytest summary: **6 failed, 55 passed, 2 skipped in 48.96s**;
63 tests total, exit 1. This run uses the local scripts in this worktree,
not the unseen new implementation from the user's reported run.

Both parameters of `test_stamp_creation_runs_no_git_hooks` still fail because
the local implementation invokes prepare-commit-msg and post-commit.
Reference-transaction events are excluded from the forbidden calls, with
no assertion requiring those events. The other four failures are unchanged:
both clean merge parameters and the linked-worktree merge produce stamps
with two parents, and the resolved-conflict case invokes post-commit twice.
The two real-signature cases are skipped in this environment.

All other checks in the corrected test are retained. Only `test_hooks.py`
and this plan were edited for the correction; prior uncommitted changes
were preserved. No scripts were edited and no commits were made.

## Prior validation result (2026-10-12, before the correction)

Full command:

```bash
UV_PROJECT_ENVIRONMENT=/home/tony/projects/hamutay/.venv UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/hamutay-ots-validation-uv-cache uv run pytest tests/validation_ots_hooks -q
```

**63 tests: 55 passed, 6 failed, 2 skipped**, in 48.05 seconds; exit 1.
These totals are read from the actual full run against the old hooks.
The default uv setup attempted dependency downloads and failed with a DNS
error for torchvision. The full run therefore reused the existing project
environment without syncing packages and used a temporary uv cache; the
partial virtual environment from the failed setup was removed.

All six failures are in `test_hooks.py`:

- `test_clean_merge_stamps_the_merge_commit_via_post_merge[without-lfs]`
  and `[with-lfs]`: each stamp has **2 parents**, `[merge, feature]`, where
  exactly `[merge]` is required. This reproduces the retained merge-state bug.
- `test_linked_worktree_without_venv_finds_main_checkout_ots[merge]`:
  the linked-worktree merge stamp also has **2 parents**, `[merge, feature]`.
  Its preceding ordinary worktree stamp passed the one-parent assertion.
- `test_conflicted_merge_resolved_with_git_commit_is_stamped_once`:
  its stamp passed the exactly-one-parent and repository-state assertions,
  but Git invoked post-commit **twice**, once for the resolution and once
  for the stamp; only the first invocation is permitted.
- `test_stamp_creation_runs_no_git_hooks[post-commit]` and `[post-merge]`:
  each recorded **4 hook calls** during stamping: prepare-commit-msg,
  reference-transaction (prepared and committed), and post-commit.
  Recording pre-commit and commit-msg hooks did not fire in these cases.

Both real-signature cases skipped because GPG cannot create a lock file
in the read-only `/home/tony/.gnupg`, cannot connect to its agent and reports
`No agent running`. A focused `-rs -k real_valid_signature` run confirmed
the diagnostic (2 skipped, 49 deselected). Unsigned fallback results are
not accepted as signatures. All four identity cases passed. One-parent stamps and post-stamp
state passed for ordinary commits, resolved conflicts, squash commits,
ordinary linked-worktree commits, and fast-forward/pull of unstamped tips.
The merge-parent failures occur before later state checks in `assert_stamp`;
those failed cases do not establish the remaining post-stamp assertions.

All seven forwarding-shim regressions passed, including porcelain/plumbing,
bare/attached signing flags, real unsigned commit objects, failing signature
verification and preservation of signing requests for non-stamp messages.
Before the shim update, five of those regressions failed as intended.
Existing guards, LFS ordering/failure, missing-client handling and installer
checks passed. No failures are marked expected. Source scripts were not
edited and no commits were made.

## Historical validation result (2026-10-09)

Final command:

```bash
UV_CACHE_DIR=/tmp/hamutay-ots-validation-uv-cache PYTEST_ADDOPTS=-rs uv run pytest tests/validation_ots_hooks -q
```

**54 collected: 49 passed, 3 failed, 2 skipped**, in 46.77 seconds; exit 1.
The default uv cache is read-only here, so the command uses a temporary cache.
`-rs` prints the detailed reasons for the two cryptographic-test skips.

The three failures are the identity test's ordinary commit, resolved-conflict
and linked-worktree commit cases. Their stamp commits have author
`Ordinary Developer <developer@example.invalid>` and committer
`Tony Mason <hamutay@wamason.com>`. Git exports `GIT_AUTHOR_NAME`,
`GIT_AUTHOR_EMAIL` and `GIT_AUTHOR_DATE` into post-commit's environment; the
hook's `-c user.name` and `-c user.email` flags do not override that author.
The recorded nested Git invocation confirms those inherited values and the
requested `-S`, signing-key and identity options. This disagrees with the
requirement that both author and committer use the project's signing identity.

The real-signature tests skipped because GPG cannot create its temporary lock
file in the read-only `/home/tony/.gnupg`, cannot connect to its agent and
reports `No agent running`. All noncryptographic assertions ran, including
actual author/committer checks; no signature validity is inferred from the
fallback's unsigned commits.

All stamping and duplicate-guard scenarios passed, including the conflicted
merge (two post-commit invocations: resolved commit and guarded proof commit;
zero post-merge invocations), squash suppression, LFS ordering/failure,
pending/anchored proofs after fast-forward and pull, worktree client discovery,
missing-client warnings, and installer shim text/forwarding/reinstallation.

Additional observation on this host's Git 2.34.1: a clean post-merge proof
commit has the stamped merge as its first parent and repeats the feature tip
as a second parent, because the nested commit still sees merge state. The
2026-10-09 contract did not specify a single-parent proof commit, so this
observation was not treated as a test failure in that run. The 2026-10-12
revision above now requires exactly one parent. Proof contents and first-parent
changes are checked explicitly.

The three source scripts match the copies taken before the first test run
byte for byte. No scripts were edited and nothing was committed in hamutay.
