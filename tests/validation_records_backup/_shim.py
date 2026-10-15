"""Subprocess-only transport doubles; never import or execute a real ssh/scp."""

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


BASE = Path(os.environ["RECORDS_TEST_BASE"]).resolve()
REMOTE_HOME = Path(os.environ["RECORDS_TEST_REMOTE_HOME"]).resolve()
HOST = "records-validation.invalid"
STATE = BASE / "shim-state"
FAULT = os.environ.get("RECORDS_TEST_FAULT", "")


def record(kind, **fields):
    with (STATE / "calls.jsonl").open("a") as stream:
        stream.write(json.dumps({"tool": kind, **fields}) + "\n")


def reject(message):
    print(f"validation transport refused: {message}", file=sys.stderr)
    raise SystemExit(96)


def checked(path, cwd=None):
    result = Path(path)
    if not result.is_absolute():
        result = (cwd or Path.cwd()) / result
    if not result.resolve().is_relative_to(BASE):
        reject(f"path outside temporary tree: {path}")
    return result


def remote_path(path):
    if path.startswith(("'", '"')):
        pieces = shlex.split(path)
        if len(pieces) != 1:
            reject("ambiguous remote pathname")
        path = pieces[0]
    if path in ("", "~"):
        path = "."
    elif path.startswith("~/"):
        path = path[2:]
    elif path.startswith("~"):
        reject("another user's home")
    result = checked(path, REMOTE_HOME)
    return str(result) + ("/" if path.endswith("/") else "")


def map_operand(value):
    if ":" in value and not value.startswith(("/", "./", "../")):
        host, path = value.split(":", 1)
        if host != HOST:
            reject(f"unknown host {host}")
        return remote_path(path), True
    checked(value)
    return value, False


def injected(name):
    (STATE / f"injected-{name}").write_text("activated\n")


def copy_failure(remote):
    if FAULT == "copy" and remote:
        injected("copy")
        raise SystemExit(23)


def corrupt_remote():
    """Damage a complete transferred run before the script can verify it."""
    marker = STATE / "injected-verify"
    if FAULT != "verify" or marker.exists():
        return
    for manifest in sorted(REMOTE_HOME.rglob("MANIFEST.sha256"), reverse=True):
        community = manifest.parent / "community"
        if not re.fullmatch(r"20\d{6}T\d{6}Z", manifest.parent.name):
            continue
        files = sorted(p for p in community.rglob("*") if p.is_file())
        if files:
            with files[0].open("ab") as stream:
                stream.write(b"\nvalidation: damaged in transit\n")
            injected("verify")
            return


def ssh(args):
    # OpenSSH joins command arguments with spaces, then the remote shell parses.
    option_values = {"-o", "-p", "-i", "-F", "-l", "-S", "-J", "-E"}
    while args and args[0].startswith("-"):
        option = args.pop(0)
        if option in option_values:
            args.pop(0)
        elif option == "--":
            break
    if not args or args.pop(0) != HOST:
        reject("unknown or absent ssh host")
    if args and args[0] == "--":
        args.pop(0)
    command = " ".join(args)
    if not command or "/home/tony/backups" in command or "wam-nuc" in command:
        reject("empty command or production address/path")
    copy_failure(True)
    remote_env = dict(os.environ, HOME=str(REMOTE_HOME), RECORDS_TEST_ON_REMOTE="1")
    return subprocess.run(
        ["/bin/bash", "-c", command], cwd=REMOTE_HOME, env=remote_env
    ).returncode


def rsync(args):
    mapped = []
    has_remote = False
    option_values = {
        "-e", "--rsh", "--rsync-path", "--exclude", "--include",
        "--exclude-from", "--include-from", "--filter", "-f",
        "--files-from", "--out-format", "--chmod", "--timeout",
    }
    skip_value = False
    link_value = False
    for value in args:
        if skip_value:
            mapped.append(value)
            skip_value = False
        elif link_value:
            mapped.append(remote_path(value) if value.startswith("~/") else value)
            link_value = False
        elif value in ("--link-dest", "--copy-dest", "--compare-dest"):
            mapped.append(value)
            link_value = True
        elif value.startswith(("--link-dest=", "--copy-dest=", "--compare-dest=")):
            option, path = value.split("=", 1)
            if path.startswith("~/"):
                path = remote_path(path)
            mapped.append(f"{option}={path}")
        elif value.startswith("-"):
            mapped.append(value)
            skip_value = value in option_values
        else:
            value, remote = map_operand(value)
            has_remote |= remote
            mapped.append(value)
    copy_failure(has_remote)
    code = subprocess.run([os.environ["RECORDS_TEST_REAL_RSYNC"], *mapped]).returncode
    if code == 0 and has_remote:
        corrupt_remote()
    return code


def scp(args):
    operands = []
    skip_value = False
    has_remote = False
    for value in args:
        if skip_value:
            skip_value = False
        elif value in ("-o", "-P", "-i", "-F", "-S", "-c", "-J"):
            skip_value = True
        elif value.startswith("-"):
            continue
        else:
            value, remote = map_operand(value)
            has_remote |= remote
            operands.append(value)
    if len(operands) < 2:
        reject("scp requires source and destination")
    copy_failure(has_remote)
    code = subprocess.run([os.environ["RECORDS_TEST_REAL_CP"], "-a", *operands]).returncode
    if code == 0 and has_remote:
        corrupt_remote()
    return code


def sha256sum(args):
    if (
        FAULT == "manifest"
        and not os.environ.get("RECORDS_TEST_ON_REMOTE")
        and not any(a in ("-c", "--check") for a in args)
    ):
        injected("manifest")
        return 74
    return subprocess.run([os.environ["RECORDS_TEST_REAL_SHA256SUM"], *args]).returncode


if __name__ == "__main__":
    tool, *arguments = sys.argv[1:]
    record(tool, args=arguments, remote=bool(os.environ.get("RECORDS_TEST_ON_REMOTE")))
    raise SystemExit(globals()[tool](arguments))
