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
   parentage, subject, author/committer identity, signing options and call counts.
3. Exercise ordinary commits, clean merges, resolved conflicts, squash merges,
   fast-forwards and local pulls, pending/anchored duplicate guards, ots subjects,
   missing clients and linked worktrees without their own virtual environment.
4. Probe real Git signing and verification with the specified key. If unavailable,
   skip only the cryptographic signature tests with the probe's diagnostic.
   Behavioral tests still execute: a Git forwarding wrapper records the exact
   original signing invocation and removes only `-S` from stamp commits when the
   probe failed. It never creates or pretends to verify a signature.
5. Run `uv run pytest tests/validation_ots_hooks -q`. Report genuine contract
   failures without changing scripts or marking disagreements as expected failures.

## Validation result (2026-10-09)

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
requested contract does not specify a single-parent proof commit, so this
observation is not treated as a test failure. Proof contents and first-parent
changes are checked explicitly.

The three source scripts match the copies taken before the first test run
byte for byte. No scripts were edited and nothing was committed in hamutay.
