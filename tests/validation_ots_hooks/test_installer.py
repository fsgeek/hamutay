"""Validate actual installer output without invoking uv or installing packages."""

import os

import pytest

from .helpers import Repo, executable


@pytest.mark.parametrize("name", ["post-commit", "post-merge"])
def test_installer_writes_the_exact_executable_forwarding_shim(repo, name):
    shim = repo.root / ".git/hooks" / name
    expected = (
        "#!/bin/bash\n"
        f'exec "$(git rev-parse --show-toplevel)/scripts/hooks/{name}" "$@"\n'
    )
    assert shim.read_text() == expected
    assert os.access(shim, os.X_OK)


def test_installer_replaces_existing_hooks_and_is_safe_to_rerun(tmp_path, runtime):
    repo = Repo(tmp_path / "installer checkout with spaces", runtime, install=False)
    for name in ("post-commit", "post-merge"):
        executable(repo.root / ".git/hooks" / name, "#!/bin/bash\nexit 99\n")
    repo.install()
    before = {
        name: (repo.root / ".git/hooks" / name).read_bytes()
        for name in ("post-commit", "post-merge")
    }
    repo.install()
    for name in before:
        shim = repo.root / ".git/hooks" / name
        assert shim.read_bytes() == before[name]
        assert os.access(shim, os.X_OK)
        assert b"exit 99" not in shim.read_bytes()
    assert repo.head == repo.base
    assert repo.events == []
    assert repo.git("status", "--porcelain").stdout == ""


@pytest.mark.parametrize("name", ["post-commit", "post-merge"])
def test_installer_shim_forwards_arguments_exit_code_and_active_checkout(repo, name):
    # A sentinel script in a linked checkout proves the installed shim resolves
    # the active worktree rather than baking in the installer's main checkout.
    worktree = repo.root / ".worktrees/shim-test"
    repo.git("worktree", "add", "-b", "shim-test", str(worktree))
    output = worktree / "shim-arguments.txt"
    executable(
        worktree / "scripts/hooks" / name,
        '#!/bin/bash\nprintf "%s\\n" "$@" > shim-arguments.txt\nexit 37\n',
    )
    result = repo.hook(name, "1", "two words", "", cwd=worktree, check=False)
    assert result.returncode == 37
    assert output.read_text() == "1\ntwo words\n\n"
    assert not (repo.root / "shim-arguments.txt").exists()
    assert repo.events == []
