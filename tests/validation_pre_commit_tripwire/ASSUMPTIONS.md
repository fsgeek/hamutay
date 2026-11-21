# Blind validation assumptions

The only repository material used to design these tests is
`docs/superpowers/specs/2026-11-11-pre-commit-config-tripwire.md`. The hook and
installer are never opened or imported. The hook runs only by its absolute path,
with a throwaway repository under pytest's `tmp_path` as its working directory.

## Harness and environment

- Python, pytest, Git, a POSIX shell, and the hook's runtime dependencies are
  available. Git supports `init --initial-branch`, `includeIf` with `gitdir`,
  `gitdir/i`, and `onbranch`. A 30 second subprocess timeout is a harness bound,
  not a hook performance requirement.
- The test file stays at the requested location, so its second parent is the
  project root. That path is used solely to locate the executable hook.
- All Git setup, staging, inspection, commits, configuration files, HOME/XDG
  directories, and installed shims belong to temporary repositories. The
  project's own `.git` is never used by the tests.
- Every subprocess, including setup and diagnostic Git commands, receives an
  explicit environment with `GIT_CONFIG_GLOBAL` pointing at a temporary file
  and `GIT_CONFIG_NOSYSTEM=1`. Inherited `GIT_*` variables are removed first.
  `GIT_CONFIG_SYSTEM` also points at a temporary file; the system test verifies
  it is ignored. This cannot establish behavior with an actively loaded system
  configuration: disabling it is the requested isolation mechanism.
- Empty Git templates and isolated HOME/XDG directories prevent unrelated hooks
  and host configuration from affecting results. Local identity and
  `commit.gpgsign=false` permit commits without signing; no signing key is set.
  Staged content is ordinary prose, keeping the other checks out of the outcome.

## Inputs and assertions

- One representative name covers each named wildcard family, and additional
  arbitrary names cover the unrestricted `pager`, `sendemail`, `credential`,
  and `alias` families. These are finite representatives of wildcard rules,
  not an exhaustive enumeration of possible subsection names.
- Executable-valued keys use `/bin/true`, except `core.fsmonitor=false` to avoid
  launching a monitor. Values need not be executable or truthy to trigger the
  presence rule; empty, false, true, and command values are separately checked.
  Potentially disruptive keys are tested by direct hook execution. The commit
  test uses an alias so Git still reaches the installed shim.
- Ordinary boolean keys use values compatible with a normal working tree.
  `core.bare=true`, signing enabled without keys, and other settings that could
  make independent Git operations fail are outside the negative controls.
- Refusal means any nonzero exit status. Diagnostics may use stdout, stderr,
  or both, in any order, with any positive indentation width. Each required
  key must be the complete trimmed content of an indented line. Additional
  messages are allowed, and duplicate keys need not be printed repeatedly.
- Corrected 2026-11-11 after re-reading only the spec's Behaviour section:
  Git treats section and variable names case-insensitively, but subsection names
  are case-sensitive. Case-variation tests uppercase sections and variables;
  the fixed `ssh` and `x509` subsections in `gpg.ssh.*` and `gpg.x509.*` remain
  lowercase. Wildcard subsection names are still exercised in uppercase, and
  include condition values retain their Git-defined meaning. Diagnostic key
  comparisons normalize only section and variable case, preserving subsections.
  `GPG.SSH.PROGRAM` is stored as `gpg.SSH.program` and is not returned by
  `git config gpg.ssh.program`; the corrected spec does not require refusal of
  these fixed-subsection case variants, so no allow/refuse assertion is made
  for them.
- Git's own include semantics determine whether a conditional target is reached.
  Matching conditions are independently verified with `git config --local
  --includes` before requiring their target keys. A nonmatching condition must
  still cause refusal for its include key, but its target keys are not required.
- Relative include paths resolve against the config file containing them.
  Nested includes are covered as files transitively reached from local config.
  Arbitrary non-`path` variables under `include` and `includeIf` are covered
  because the spec explicitly says **any** such key is refused.
- The shim uses a POSIX `exec` and forwards arguments; this implements the
  specified installer effect without executing or inspecting the installer.
  Its hooks directory is created explicitly because an empty Git template need
  not provide one.
  The commit test first creates a clean HEAD, then asserts a refused commit
  leaves that HEAD unchanged and the staged change available.

## Implementation and execution plan

1. Create this assumptions document, the package marker, and a self-contained
   subprocess harness in `test_tripwire.py`.
2. Parameterize every denylist representative in canonical form and with
   uppercase sections and variables, preserving lowercase fixed subsections;
   assert refusal and individually indented diagnostics. Add combined-key and
   value-presence checks.
3. Cover every explicit ordinary key, global-only denylisted keys, disabled
   system configuration, and local/global scope separation.
4. Cover unconditional, matching conditional, nonmatching conditional, missing,
   empty, ordinary, nested, and global-only includes.
5. Exercise a real successful commit and refused successor through the shim.
6. Run `uv run pytest -q tests/validation_pre_commit_tripwire`; assess failures
   against the supplied spec without inspecting or modifying the implementation.

No implementation changes, commits, or stashes are part of this validation.
