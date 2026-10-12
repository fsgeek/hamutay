"""Temporary-repository harness; imports no hamutay application code."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
from dataclasses import dataclass


SOURCE_ROOT = Path(__file__).resolve().parents[2]
SIGNING_KEY = "01193FA2631C8AE8E4DF266E216D3C9B920813A1"
STAMP_EMAIL = "hamutay@wamason.com"
STAMP_NAME = "Tony Mason"
PROOF_PREFIX = "fake OpenTimestamps proof for "


def executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)


def python_executable(path: Path, body: str) -> None:
    executable(path, f"#!{sys.executable}\n{body}")


EVENT_PREAMBLE = """import json, os, pathlib, sys
def record(kind, **fields):
    with open(os.environ['OTS_VALIDATION_EVENTS'], 'a') as stream:
        stream.write(json.dumps(dict(kind=kind, **fields)) + '\\n')
"""


@dataclass
class Runtime:
    bin_dir: Path
    env: dict[str, str]
    real_git: str
    signing_reason: str | None = None


def make_runtime(root: Path) -> Runtime:
    """Expose only chosen commands, keeping host git-lfs/ots out of PATH."""
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True)
    real_git = shutil.which("git")
    assert real_git, "Git is required for hook validation"
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        PATH=str(bin_dir),
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_TERMINAL_PROMPT="0",
        LC_ALL="C",
    )
    for name in ("bash", "cat", "chmod", "mkdir", "gpg"):
        target = shutil.which(name)
        if target:
            (bin_dir / name).symlink_to(target)
    # Git prepends its exec path to PATH before invoking hooks. Route that path
    # through our forwarding wrapper too, otherwise nested commits bypass the
    # signing-unavailable fallback and command recording. Preserve real Git's
    # helpers for local fetch/pull, excluding host LFS and OTS clients.
    exec_path = subprocess.run(
        [real_git, "--exec-path"], env=env, text=True, capture_output=True, check=True
    ).stdout.strip()
    for helper in Path(exec_path).iterdir():
        if helper.name in {"git", "git-lfs", "ots"}:
            continue
        destination = bin_dir / helper.name
        if not destination.exists():
            destination.symlink_to(helper)
    env["GIT_EXEC_PATH"] = str(bin_dir)
    python_executable(
        bin_dir / "git",
        EVENT_PREAMBLE
        + f"REAL_GIT = {real_git!r}\n"
        + """args = sys.argv[1:]
is_stamp = any(flag == '-m' and message.startswith('ots: stamp ')
               for flag, message in zip(args, args[1:]))
if is_stamp:
    record('git-stamp', argv=args, cwd=os.getcwd(),
           author_env={key: os.environ.get(key) for key in
                       ('GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_AUTHOR_DATE')})
    if os.environ.get('OTS_VALIDATION_UNSIGNED_STAMPS') == '1':
        args = [arg for arg in args if not arg.startswith('-S')]
os.execv(REAL_GIT, [REAL_GIT, *args])
""",
    )
    return Runtime(bin_dir, env, real_git)


def run_command(argv, *, cwd: Path, env, check=True):
    result = subprocess.run(
        [str(arg) for arg in argv],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if check:
        assert result.returncode == 0, (
            f"{argv!r} exited {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def signing_probe(runtime: Runtime, root: Path) -> str | None:
    """Check actual Git signing, rather than merely listing a secret key."""
    if not (runtime.bin_dir / "gpg").exists():
        return "gpg executable is unavailable"
    root.mkdir()
    env = dict(runtime.env)
    try:
        run_command([runtime.real_git, "init", "-b", "main"], cwd=root, env=env)
        result = run_command(
            [
                runtime.real_git,
                "-c", f"user.name={STAMP_NAME}",
                "-c", f"user.email={STAMP_EMAIL}",
                "-c", f"user.signingkey={SIGNING_KEY}",
                "-c", "core.hooksPath=/dev/null",
                "commit", "--allow-empty", "-S", "-m", "signing availability probe",
            ],
            cwd=root, env=env, check=False,
        )
        if result.returncode:
            diagnostic = subprocess.run(
                ["gpg", "--batch", "--local-user", SIGNING_KEY,
                 "--detach-sign", "--output", "-"],
                input=b"OpenTimestamps validation signing probe\n",
                cwd=root, env=env, capture_output=True, timeout=10,
            )
            detail = diagnostic.stderr.decode(errors="replace").strip()
            return (
                f"Git signing with {SIGNING_KEY} failed: {result.stderr.strip()}"
                + (f"; gpg: {detail}" if detail else "")
            )
        result = run_command(
            [runtime.real_git, "verify-commit", "--raw", "HEAD"],
            cwd=root, env=env, check=False,
        )
        if result.returncode or SIGNING_KEY not in result.stderr:
            return f"Git signature verification unavailable: {result.stderr.strip()}"
    except subprocess.TimeoutExpired as exc:
        return f"Git signing/verification with {SIGNING_KEY} timed out after {exc.timeout} seconds"
    return None


class Repo:
    def __init__(self, root: Path, runtime: Runtime, *, install=True):
        self.root = root
        self.runtime = runtime
        root.mkdir(parents=True)
        self.event_file = root.parent / f"{root.name}-events.jsonl"
        self.trace_file = root.parent / f"{root.name}-git-trace.log"
        self.env = dict(runtime.env)
        self.env.update(
            OTS_VALIDATION_EVENTS=str(self.event_file),
            GIT_TRACE=str(self.trace_file),
        )
        if runtime.signing_reason:
            self.env["OTS_VALIDATION_UNSIGNED_STAMPS"] = "1"
        self.git("init", "-b", "main")
        # Deliberately conflict with the required stamp identity/key.
        for key, value in {
            "user.name": "Ordinary Developer",
            "user.email": "developer@example.invalid",
            "user.signingkey": "DEADBEEFDEADBEEF",
            "commit.gpgsign": "false",
            "core.autocrlf": "false",
            "core.hooksPath": str(root / ".git" / "hooks"),
        }.items():
            self.git("config", key, value)
        for relative in (
            "scripts/hooks/post-commit",
            "scripts/hooks/post-merge",
            "scripts/install-hooks.sh",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE_ROOT / relative, destination)
        (root / ".gitignore").write_text(".venv/\n.worktrees/\n")
        (root / "base.txt").write_text("base\n")
        self.git("add", ".")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-m", "initial fixture")
        self.base = self.head
        self.add_ots()
        if install:
            self.install()
        self.clear_events()

    def git(self, *args, cwd=None, check=True):
        return run_command(
            ["git", *args], cwd=cwd or self.root, env=self.env, check=check
        )

    @property
    def head(self):
        return self.git("rev-parse", "HEAD").stdout.strip()

    @property
    def subject(self):
        return self.git("log", "-1", "--format=%s").stdout.strip()

    def install(self):
        """Execute the copied installer except its exact dependency-install line."""
        source = (self.root / "scripts/install-hooks.sh").read_text()
        lines = source.splitlines(keepends=True)
        assert lines.count("uv pip install opentimestamps-client\n") == 1
        filtered = "".join(
            line for line in lines if line != "uv pip install opentimestamps-client\n"
        )
        installer = self.root.parent / f"{self.root.name}-install-without-uv.sh"
        executable(installer, filtered)
        return run_command([installer], cwd=self.root, env=self.env)

    def add_ots(self, checkout=None):
        python_executable(
            (checkout or self.root) / ".venv/bin/ots",
            EVENT_PREAMBLE
            + f"PROOF_PREFIX = {PROOF_PREFIX!r}\n"
            + """assert sys.argv[1] == 'stamp' and len(sys.argv) == 3, sys.argv
target = pathlib.Path(sys.argv[2])
commit_hash = target.read_text().strip()
record('ots', argv=sys.argv[1:], hash=commit_hash, cwd=os.getcwd())
pathlib.Path(str(target) + '.ots').write_text(PROOF_PREFIX + commit_hash + '\\n')
""",
        )

    def add_lfs(self, exit_code=0):
        python_executable(
            self.runtime.bin_dir / "git-lfs",
            EVENT_PREAMBLE
            + f"record('lfs', argv=sys.argv[1:], cwd=os.getcwd())\nsys.exit({exit_code})\n",
        )

    def clear_events(self):
        self.event_file.write_text("")
        self.trace_file.write_text("")

    def hook_calls(self, name):
        """Parse Git trace arguments correctly even when hook paths need quotes."""
        calls = []
        for line in self.trace_file.read_text().splitlines():
            if "trace: run_command:" not in line:
                continue
            args = shlex.split(line.split("trace: run_command:", 1)[1])
            for index, arg in enumerate(args):
                if arg.endswith(f"/hooks/{name}"):
                    calls.append(args[index + 1:])
        return calls

    @property
    def events(self):
        return [json.loads(line) for line in self.event_file.read_text().splitlines()]

    def hook(self, name, *args, cwd=None, check=True):
        # The installed shim chooses the script using the active checkout.
        return run_command(
            [self.root / ".git/hooks" / name, *args],
            cwd=cwd or self.root, env=self.env, check=check,
        )

    def commit_file(self, filename, content, subject, *, branch=None):
        """Set up history without stamping; tests enable hooks for the action."""
        if branch:
            self.git("checkout", "-b", branch)
        (self.root / filename).write_text(content)
        self.git("add", filename)
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-m", subject)
        return self.head

    def divergent_branches(self, *, conflict=False):
        filename = "base.txt" if conflict else "feature.txt"
        feature = self.commit_file(filename, "feature\n", "feature change", branch="feature")
        self.git("checkout", "main")
        filename = "base.txt" if conflict else "main.txt"
        main = self.commit_file(filename, "main\n", "main change")
        self.clear_events()
        return main, feature

    def seed_proof(self, commit_hash, location):
        directory = self.root / "timestamps"
        if location == "anchored":
            directory /= "anchored"
        directory.mkdir(parents=True, exist_ok=True)
        proof = directory / f"{commit_hash}.ots"
        proof.write_text("existing proof: must stay unchanged\n")
        return proof


def assert_stamp(repo: Repo, target: str, *, cwd=None):
    """Assert stamping behavior; identity and crypto have independent tests."""
    checkout = cwd or repo.root
    stamp = repo.git("rev-parse", "HEAD", cwd=checkout).stdout.strip()
    subject = repo.git("log", "-1", "--format=%s", cwd=checkout).stdout.strip()
    assert subject == f"ots: stamp {target}"
    parents = repo.git("show", "-s", "--format=%P", stamp, cwd=checkout).stdout.split()
    assert parents == [target], (
        f"Stamp must have exactly one parent, the stamped commit {target}; "
        f"actual parent count: {len(parents)}, parents: {parents}"
    )
    assert repo.git("rev-list", "--count", f"{target}..HEAD", cwd=checkout).stdout.strip() == "1"
    assert (checkout / "timestamps" / target).read_text() == target + "\n"
    assert (checkout / "timestamps" / f"{target}.ots").read_text() == PROOF_PREFIX + target + "\n"
    # Compare explicitly with the target so a malformed merge stamp cannot hide
    # its changed files through diff-tree's default merge-commit suppression.
    changed = repo.git("diff", "--name-only", target, stamp, cwd=checkout).stdout.splitlines()
    assert set(changed) == {f"timestamps/{target}", f"timestamps/{target}.ots"}
    assert repo.git("status", "--porcelain", cwd=checkout).stdout == ""
    for name in ("MERGE_HEAD", "MERGE_MSG", "MERGE_MODE", "AUTO_MERGE"):
        state = Path(repo.git("rev-parse", "--git-path", name, cwd=checkout).stdout.strip())
        if not state.is_absolute():
            state = checkout / state
        assert not state.exists(), f"Stamp must clear merge state: {state}"
    branch = repo.git("symbolic-ref", "HEAD", cwd=checkout).stdout.strip()
    assert branch.startswith("refs/heads/")
    assert repo.git("rev-parse", branch, cwd=checkout).stdout.strip() == stamp
    reflog = repo.git("reflog", "show", "--format=%H%x09%gs", branch, cwd=checkout).stdout.splitlines()
    assert any(entry.startswith(stamp + "\t") and subject in entry.split("\t", 1)[1]
               for entry in reflog), f"Branch reflog must mention {subject!r}: {reflog}"
    ots_events = [event for event in repo.events if event["kind"] == "ots"]
    assert len(ots_events) == 1
    assert ots_events[0]["hash"] == target
    assert ots_events[0]["argv"] == ["stamp", str(checkout / "timestamps" / target)]
    return stamp


def assert_stamp_identity(repo: Repo, *, cwd=None):
    metadata = repo.git(
        "show", "-s", "--format=%an%n%ae%n%cn%n%ce", cwd=cwd
    ).stdout.splitlines()
    assert metadata == [STAMP_NAME, STAMP_EMAIL, STAMP_NAME, STAMP_EMAIL], (
        f"Stamp author/committer must both use {STAMP_EMAIL}; actual metadata: {metadata}"
    )
