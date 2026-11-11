# Spec: the pre-commit config tripwire (for blind tests)

`scripts/hooks/pre-commit` runs before every commit in hamut'ay. It is installed by `scripts/install-hooks.sh`
as a shim in `.git/hooks/pre-commit` that execs the versioned script. This spec covers **only its first check**:
the config tripwire. Its other checks (the secret scan and the signing-identity check) are out of scope. Tests
must run the hook in a way that keeps those checks from deciding the outcome. With nothing staged that looks like
a secret and no `user.signingkey` set, they pass (the identity check prints a warning and skips).

## Why it exists

Doors run as the same Unix user inside this checkout, so they can write `.git/config`, and git will then run
whatever program that config names. The tripwire can't prevent an entry that has already fired (for example,
`core.fsmonitor` runs on `git status`). What it does is refuse to let a commit go ahead while such an entry is
present.

## Behaviour

Run with the repository as its working directory (as git runs it), the hook **refuses** (exits non-zero, and lists
each offending key on its own line in its output, indented) when the repository's **local** configuration
(`.git/config`, including any file reached from it through `include.path` or `includeIf.<cond>.path`) sets any of
these keys. Section and key names match case-insensitively, as git treats them. **Subsection names are
case-sensitive in git**, so `GPG.SSH.PROGRAM` is stored as `gpg.SSH.program`, a different key from
`gpg.ssh.program` that git never reads. The hook need not refuse such variants of the fixed-subsection keys
(`gpg.ssh.*`, `gpg.x509.*`). (Corrected 2026-11-11 after Codex's first run. The first text said
"case-insensitively" without this exception, and git's behaviour was confirmed by experiment.) The keys:

- `core.fsmonitor`, `core.pager`, `core.editor`, `core.sshcommand`, `core.hookspath`, `core.askpass`,
  `core.gitproxy`, `core.alternaterefscommand`
- `sequence.editor`, `interactive.difffilter`
- `pager.<anything>`
- `gpg.program`, `gpg.ssh.program`, `gpg.ssh.defaultkeycommand`, `gpg.x509.program`
- `filter.<name>.clean`, `filter.<name>.smudge`, `filter.<name>.process`
- `diff.external`, `diff.<name>.command`, `diff.<name>.textconv`
- `merge.<name>.driver`, `mergetool.<name>.cmd`, `difftool.<name>.cmd`
- `remote.<name>.uploadpack`, `remote.<name>.receivepack`
- `sendemail.<anything>`
- `credential.<anything>` (including `credential.helper`)
- `alias.<anything>`

It also refuses when the local configuration contains **any** `include.*` or `includeif.*` key, whatever the
included file holds and whether or not that file exists. That key itself is listed.

When an include points to a file that sets one of the keys above, the refusal lists **both** the include key and
the key reached through it.

It **does not refuse** on account of:
- ordinary local keys (`core.repositoryformatversion`, `core.filemode`, `core.bare`, `core.logallrefupdates`,
  `user.name`, `user.email`, `remote.origin.url`, `remote.origin.fetch`, `branch.main.remote`, `branch.main.merge`,
  `commit.gpgsign`, `lfs.repositoryformatversion`, `core.autocrlf`);
- any of the listed keys when they are set only in **global** or **system** configuration (the tripwire looks
  only at the repository's own config). Tests can isolate global and system config through git's environment
  (`GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`).

With a clean local config and nothing else wrong, a commit made through the installed shim succeeds. With a
listed key present, the commit is refused and HEAD does not move.

## Known limits (do not test as failures)

It's a denylist: keys git adds in future versions are not covered. It doesn't stop an entry that has already
fired before the hook runs.
