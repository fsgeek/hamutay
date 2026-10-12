"""The unsigned fallback forwards real Git operations and never fakes crypto."""

import pytest

from .helpers import SIGNING_KEY


@pytest.mark.parametrize("command", ["commit", "commit-tree"])
@pytest.mark.parametrize("signing_flags", [["-S"], [f"-S{SIGNING_KEY}"], ["-S", f"-S{SIGNING_KEY}"]],
                         ids=["bare", "attached-key", "both"])
def test_unsigned_fallback_handles_stamp_messages_for_any_creation_command(repo, command, signing_flags):
    repo.env["OTS_VALIDATION_UNSIGNED_STAMPS"] = "1"
    target = repo.head
    message = f"ots: stamp {target}"
    if command == "commit-tree":
        tree = repo.git("write-tree").stdout.strip()
        result = repo.git(command, tree, "-p", target, *signing_flags, "-m", message)
        stamp = result.stdout.strip()
    else:
        repo.git("-c", "core.hooksPath=/dev/null", command, "--allow-empty",
                 *signing_flags, "-m", message)
        stamp = repo.head
    assert repo.git("show", "-s", "--format=%s", stamp).stdout.strip() == message
    assert repo.git("show", "-s", "--format=%P", stamp).stdout.split() == [target]
    raw = repo.git("cat-file", "commit", stamp).stdout
    assert "\ngpgsig " not in raw
    assert repo.git("verify-commit", stamp, check=False).returncode != 0
    assert repo.git("show", "-s", "--format=%G?", stamp).stdout.strip() == "N"


def test_unsigned_fallback_does_not_strip_signing_from_non_stamp_messages(repo):
    repo.env["OTS_VALIDATION_UNSIGNED_STAMPS"] = "1"
    before = repo.head
    result = repo.git("-c", "core.hooksPath=/dev/null", "commit", "--allow-empty",
                      "-S0000000000000000", "-m", "ordinary signed commit", check=False)
    assert result.returncode != 0
    assert repo.head == before
    assert repo.events == []
