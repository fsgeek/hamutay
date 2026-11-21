"""Exercise the versioned hook without inspecting its implementation."""

import os
from pathlib import Path
import shlex
import subprocess

import pytest


HOOK = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "pre-commit"

# Every explicit key and every wildcard family in the supplied specification.
LISTED_KEYS = (
    "core.fsmonitor",
    "core.pager",
    "core.editor",
    "core.sshcommand",
    "core.hookspath",
    "core.askpass",
    "core.gitproxy",
    "core.alternaterefscommand",
    "sequence.editor",
    "interactive.difffilter",
    "pager.log",
    "pager.arbitrary-command",
    "gpg.program",
    "gpg.ssh.program",
    "gpg.ssh.defaultkeycommand",
    "gpg.x509.program",
    "filter.tripwire.clean",
    "filter.tripwire.smudge",
    "filter.tripwire.process",
    "diff.external",
    "diff.tripwire.command",
    "diff.tripwire.textconv",
    "merge.tripwire.driver",
    "mergetool.tripwire.cmd",
    "difftool.tripwire.cmd",
    "remote.tripwire.uploadpack",
    "remote.tripwire.receivepack",
    "sendemail.smtpserver",
    "sendemail.arbitrary-variable",
    "credential.helper",
    "credential.username",
    "credential.arbitrary-variable",
    "alias.tripwire",
    "alias.arbitrary-command",
)

ORDINARY_KEYS = (
    ("core.repositoryformatversion", "0"),
    ("core.filemode", "false"),
    ("core.bare", "false"),
    ("core.logallrefupdates", "true"),
    ("user.name", "Tripwire Validation"),
    ("user.email", "tripwire@example.invalid"),
    ("remote.origin.url", "https://example.invalid/repository.git"),
    ("remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"),
    ("branch.main.remote", "origin"),
    ("branch.main.merge", "refs/heads/main"),
    ("commit.gpgsign", "false"),
    ("lfs.repositoryformatversion", "0"),
    ("core.autocrlf", "false"),
)


class Repository:
    def __init__(self, root):
        self.path = root / "repository"
        self.path.mkdir()
        self.global_config = root / "global.config"
        self.system_config = root / "system.config"
        self.global_config.write_text("", encoding="utf-8")
        self.system_config.write_text("", encoding="utf-8")
        home = root / "home"
        home.mkdir()
        template = root / "empty-template"
        template.mkdir()

        # Remove inherited repository selection, injected config, signing keys,
        # indexes and object directories before any child Git process starts.
        self.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        self.env.update(
            GIT_CONFIG_GLOBAL=str(self.global_config),
            GIT_CONFIG_SYSTEM=str(self.system_config),
            GIT_CONFIG_NOSYSTEM="1",
            GIT_TERMINAL_PROMPT="0",
            HOME=str(home),
            XDG_CONFIG_HOME=str(home / "xdg"),
            LC_ALL="C",
        )
        self.git("init", "--initial-branch=main", f"--template={template}")
        self.set("user.name", "Tripwire Validation")
        self.set("user.email", "tripwire@example.invalid")
        self.set("commit.gpgsign", "false")

    def run(self, *args, check=True):
        result = subprocess.run(
            [str(arg) for arg in args],
            cwd=self.path,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check:
            assert result.returncode == 0, self.describe(result)
        return result

    def git(self, *args, check=True):
        return self.run("git", *args, check=check)

    def set(self, key, value=None, *, config_file=None):
        if value is None:
            # Values are inert; refusal is required because a key is present.
            value = "false" if key.lower() == "core.fsmonitor" else "/bin/true"
        scope = ["--local"] if config_file is None else ["--file", str(config_file)]
        self.git("config", *scope, "--add", key, value)

    def hook(self):
        return self.run(HOOK, check=False)

    @staticmethod
    def describe(result):
        return (
            f"command: {result.args!r}\nexit: {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    def stage(self, text):
        (self.path / "ordinary.txt").write_text(text, encoding="utf-8")
        self.git("add", "--", "ordinary.txt")

    def install_shim(self):
        shim = self.path / ".git" / "hooks" / "pre-commit"
        shim.parent.mkdir(parents=True, exist_ok=True)
        shim.write_text(
            f'#!/bin/sh\nexec {shlex.quote(str(HOOK))} "$@"\n', encoding="utf-8"
        )
        shim.chmod(0o755)


@pytest.fixture
def repo(tmp_path):
    return Repository(tmp_path)


def assert_allowed(result):
    assert result.returncode == 0, Repository.describe(result)


def normalize_section_and_key_case(key):
    parts = key.split(".")
    parts[0] = parts[0].lower()
    parts[-1] = parts[-1].lower()
    return ".".join(parts)


def assert_refused(result, *keys):
    diagnostic = Repository.describe(result)
    assert result.returncode != 0, diagnostic
    # stdout/stderr choice, indent width, ordering and other messages are free.
    # Each offending key must nevertheless occupy its own indented line.
    lines = (result.stdout + "\n" + result.stderr).splitlines()
    listed = {
        normalize_section_and_key_case(line.strip())
        for line in lines
        if line and line[0] in " \t"
    }
    for key in keys:
        assert normalize_section_and_key_case(key) in listed, (
            f"Missing indented key {key!r}\n{diagnostic}"
        )


def test_clean_local_configuration_is_allowed(repo):
    assert_allowed(repo.hook())


@pytest.mark.parametrize("key", LISTED_KEYS)
def test_every_listed_key_is_refused(repo, key):
    repo.set(key)
    assert_refused(repo.hook(), key)


@pytest.mark.parametrize("key", LISTED_KEYS)
def test_listed_key_sections_and_variables_are_case_insensitive(repo, key):
    section, *subsection, variable = key.upper().split(".")
    # Git preserves subsection case. These fixed names must stay lowercase;
    # wildcard subsection names still match when uppercase.
    if key.startswith(("gpg.ssh.", "gpg.x509.")):
        subsection = [part.lower() for part in subsection]
    cased_key = ".".join([section, *subsection, variable])
    repo.set(cased_key)
    assert_refused(repo.hook(), cased_key)


def test_every_offending_key_gets_its_own_indented_line(repo):
    for key in LISTED_KEYS:
        repo.set(key)
    assert_refused(repo.hook(), *LISTED_KEYS)


@pytest.mark.parametrize("value", ["", "false", "true", "/bin/true"])
def test_refusal_depends_on_key_presence_not_value(repo, value):
    repo.set("core.fsmonitor", value)
    assert_refused(repo.hook(), "core.fsmonitor")


@pytest.mark.parametrize("key,value", ORDINARY_KEYS, ids=[k for k, _ in ORDINARY_KEYS])
def test_each_explicitly_ordinary_key_is_allowed(repo, key, value):
    repo.set(key, value)
    assert_allowed(repo.hook())


def test_all_explicitly_ordinary_keys_together_are_allowed(repo):
    for key, value in ORDINARY_KEYS:
        repo.set(key, value)
    assert_allowed(repo.hook())


@pytest.mark.parametrize("key", LISTED_KEYS)
def test_listed_key_only_in_global_config_is_allowed(repo, key):
    repo.set(key, config_file=repo.global_config)
    assert_allowed(repo.hook())


def test_all_listed_keys_only_in_global_config_are_allowed(repo):
    for key in LISTED_KEYS:
        repo.set(key, config_file=repo.global_config)
    assert_allowed(repo.hook())


def test_system_config_is_disabled_in_every_child_environment(repo):
    for key in LISTED_KEYS:
        repo.set(key, config_file=repo.system_config)
    assert repo.env["GIT_CONFIG_NOSYSTEM"] == "1"
    # Establish that the supplied system config really is excluded by Git.
    assert repo.git("config", "--get", "alias.tripwire", check=False).returncode == 1
    assert_allowed(repo.hook())


def include_key(repo, kind):
    if kind == "include":
        return "include.path"
    if kind == "gitdir":
        return f"includeIf.gitdir:{repo.path}/.path"
    if kind == "gitdir-insensitive":
        return f"includeIf.gitdir/i:{str(repo.path).upper()}/.path"
    if kind == "onbranch":
        return "includeIf.onbranch:main.path"
    raise AssertionError(kind)


@pytest.mark.parametrize("kind", ["include", "gitdir", "gitdir-insensitive", "onbranch"])
@pytest.mark.parametrize("contents", ["empty", "ordinary", "listed", "missing"])
def test_local_includes_are_refused_and_reached_keys_are_listed(repo, kind, contents):
    included = repo.path / ".git" / "included.config"
    if contents != "missing":
        included.write_text("", encoding="utf-8")
    if contents == "ordinary":
        repo.set("user.name", "Included Name", config_file=included)
    if contents == "listed":
        repo.set("core.pager", config_file=included)
        repo.set("alias.tripwire", config_file=included)
    key = include_key(repo, kind)
    # Relative include paths resolve against the containing .git/config file.
    repo.set(key, included.name)
    if contents == "listed":
        # Independently establish that this condition actually matches in Git.
        reached = repo.git("config", "--local", "--includes", "--get", "core.pager")
        assert reached.stdout.strip() == "/bin/true"
        assert_refused(repo.hook(), key, "core.pager", "alias.tripwire")
    else:
        assert_refused(repo.hook(), key)


@pytest.mark.parametrize("key", ["include.extra", "includeIf.unmatched.extra"])
def test_include_families_cover_more_than_path_variables(repo, key):
    repo.set(key, "ordinary-value")
    assert_refused(repo.hook(), key)


@pytest.mark.parametrize("key", ["INCLUDE.PATH", "INCLUDEIF.onbranch:main.PATH"])
def test_include_sections_and_variables_are_case_insensitive(repo, key):
    included = repo.path / ".git" / "mixed-case.config"
    included.write_text("", encoding="utf-8")
    repo.set("core.pager", config_file=included)
    repo.set(key, str(included))
    assert_refused(repo.hook(), key, "core.pager")


@pytest.mark.parametrize("exists", [False, True], ids=["missing", "existing"])
def test_nonmatching_conditional_include_still_refuses(repo, exists):
    included = repo.path / ".git" / "unmatched.config"
    if exists:
        included.write_text("", encoding="utf-8")
        repo.set("core.pager", config_file=included)
    key = "includeIf.onbranch:never-matches-main.path"
    repo.set(key, str(included))
    assert repo.git(
        "config", "--local", "--includes", "--get", "core.pager", check=False
    ).returncode == 1
    assert_refused(repo.hook(), key)


def test_nested_relative_include_lists_transitively_reached_keys(repo):
    directory = repo.path / ".git" / "includes"
    directory.mkdir()
    first = directory / "first.config"
    second = directory / "second.config"
    first.write_text("", encoding="utf-8")
    second.write_text("", encoding="utf-8")
    repo.set("include.path", second.name, config_file=first)
    repo.set("filter.tripwire.process", config_file=second)
    repo.set("include.path", "includes/first.config")
    assert_refused(repo.hook(), "include.path", "filter.tripwire.process")


@pytest.mark.parametrize("kind", ["include", "onbranch"])
def test_include_and_reached_keys_only_in_global_config_are_allowed(repo, kind):
    included = repo.global_config.parent / "global-include.config"
    included.write_text("", encoding="utf-8")
    repo.set("core.pager", config_file=included)
    repo.set(include_key(repo, kind), str(included), config_file=repo.global_config)
    assert_allowed(repo.hook())


def test_global_benign_value_cannot_hide_a_listed_local_key(repo):
    repo.set("core.pager", "cat", config_file=repo.global_config)
    repo.set("core.pager", "cat")
    assert_refused(repo.hook(), "core.pager")


def test_commit_through_shim_succeeds_then_refuses_without_moving_head(repo):
    repo.install_shim()
    repo.stage("An ordinary validation fixture.\n")
    clean_commit = repo.git("commit", "-m", "Clean validation commit", check=False)
    assert_allowed(clean_commit)
    before = repo.git("rev-parse", "HEAD").stdout.strip()
    assert repo.git("show", "HEAD:ordinary.txt").stdout == "An ordinary validation fixture.\n"

    repo.stage("An ordinary validation fixture, changed.\n")
    # This listed key cannot reroute the shim or fire during commit setup.
    repo.set("alias.tripwire", "status")
    refused_commit = repo.git("commit", "-m", "Must be refused", check=False)
    after = repo.git("rev-parse", "HEAD").stdout.strip()
    assert after == before, Repository.describe(refused_commit)
    assert_refused(refused_commit, "alias.tripwire")
    assert repo.git("diff", "--cached", "--name-only").stdout.strip() == "ordinary.txt"
