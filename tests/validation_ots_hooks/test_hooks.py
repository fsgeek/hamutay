"""Black-box contracts exercised through copied hooks and real Git operations."""

import pytest

from .helpers import (
    EVENT_PREAMBLE, SIGNING_KEY, STAMP_EMAIL, assert_stamp, assert_stamp_identity,
    executable, python_executable, run_command,
)


@pytest.mark.parametrize("commit_args", [[], ["--allow-empty"], ["--no-verify"]], ids=["ordinary", "empty", "no-verify"])
def test_non_ots_commit_creates_exactly_one_stamp_commit(repo, commit_args):
    if "--allow-empty" not in commit_args:
        (repo.root / "experiment.txt").write_text("pre-registered design\n")
        repo.git("add", "experiment.txt")
    repo.git("commit", *commit_args, "-m", "register experiment")
    target = repo.git("rev-parse", "HEAD^").stdout.strip()
    assert repo.git("show", "-s", "--format=%s", target).stdout.strip() == "register experiment"
    assert_stamp(repo, target)
    assert repo.git("rev-list", "--count", f"{repo.base}..HEAD").stdout.strip() == "2"
    assert not (repo.root / "timestamps" / repo.head).exists(), "stamp commit must not be stamped recursively"


@pytest.mark.parametrize("hook", ["post-commit", "post-merge"])
def test_stamp_creation_runs_no_git_hooks(repo, hook):
    # Invoke a saved copy of the installed shim so every installed hook can be
    # replaced by a recorder. There is no user commit to confuse with the stamp.
    trigger = repo.root.parent / f"saved-{hook}"
    executable(trigger, (repo.root / ".git/hooks" / hook).read_text())
    for name in ("pre-commit", "prepare-commit-msg", "commit-msg", "post-commit",
                 "post-merge", "reference-transaction"):
        python_executable(
            repo.root / ".git/hooks" / name,
            EVENT_PREAMBLE + f"record('hook', name={name!r}, argv=sys.argv[1:])\n",
        )
    target = repo.head
    repo.clear_events()
    run_command([trigger, *(["0"] if hook == "post-merge" else [])],
                cwd=repo.root, env=repo.env)
    # Ref observers may fire for the stamp update; commit-lifecycle hooks must not.
    calls = [event for event in repo.events
             if event["kind"] == "hook" and event["name"] != "reference-transaction"]
    assert calls == [], f"Stamp creation must invoke no commit-lifecycle hooks; recorded: {calls}"
    assert_stamp(repo, target)


@pytest.mark.parametrize("lfs_present", [False, True], ids=["without-lfs", "with-lfs"])
def test_clean_merge_stamps_the_merge_commit_via_post_merge(repo, lfs_present):
    main, feature = repo.divergent_branches()
    if lfs_present:
        repo.add_lfs()
    repo.git("merge", "--no-ff", "feature", "-m", "merge experiment")
    merge = repo.git("rev-parse", "HEAD^").stdout.strip()
    assert repo.git("show", "-s", "--format=%P", merge).stdout.split() == [main, feature]
    assert repo.git("show", "-s", "--format=%s", merge).stdout.strip() == "merge experiment"
    assert_stamp(repo, merge)
    if lfs_present:
        assert [e["kind"] for e in repo.events if e["kind"] != "git-stamp"] == ["lfs", "ots"]
        assert repo.events[0]["argv"] == ["post-merge", "0"]
    assert repo.hook_calls("post-merge") == [["0"]]
    # Git invokes post-merge for the merge; stamp creation invokes no hooks.
    assert repo.hook_calls("post-commit") == []


def test_conflicted_merge_resolved_with_git_commit_is_stamped_once(repo):
    main, feature = repo.divergent_branches(conflict=True)
    result = repo.git("merge", "--no-ff", "feature", "-m", "conflicted merge", check=False)
    assert result.returncode == 1
    assert "CONFLICT" in result.stdout
    assert repo.head == main
    assert repo.git("rev-parse", "MERGE_HEAD").stdout.strip() == feature
    assert repo.events == [], "an unresolved merge has no new commit to stamp"
    assert repo.hook_calls("post-merge") == []
    (repo.root / "base.txt").write_text("resolved feature and main\n")
    repo.git("add", "base.txt")
    repo.clear_events()
    repo.git("commit", "-m", "resolve merge conflict")
    merge = repo.git("rev-parse", "HEAD^").stdout.strip()
    assert repo.git("show", "-s", "--format=%P", merge).stdout.split() == [main, feature]
    assert_stamp(repo, merge)
    assert repo.hook_calls("post-merge") == []
    assert repo.hook_calls("post-commit") == [[]]
    stamp = repo.head
    repo.hook("post-merge", "0")
    assert repo.head == stamp
    assert len([e for e in repo.events if e["kind"] == "ots"]) == 1


def test_squash_merge_stamps_nothing_until_the_squash_is_committed(repo):
    repo.commit_file("feature.txt", "feature\n", "feature", branch="feature")
    repo.git("checkout", "main")
    repo.add_lfs()
    repo.clear_events()
    repo.git("merge", "--squash", "feature")
    assert repo.head == repo.base
    assert [e["kind"] for e in repo.events] == ["lfs"]
    assert repo.events[0]["argv"] == ["post-merge", "1"]
    assert not (repo.root / "timestamps").exists()
    assert repo.git("diff", "--cached", "--name-only").stdout.splitlines() == ["feature.txt"]
    assert repo.hook_calls("post-merge") == [["1"]]
    repo.clear_events()
    repo.git("commit", "-m", "commit squashed feature")
    target = repo.git("rev-parse", "HEAD^").stdout.strip()
    assert repo.git("show", "-s", "--format=%P", target).stdout.split() == [repo.base]
    assert_stamp(repo, target)


@pytest.mark.parametrize("squash", ["0", "1"])
def test_lfs_runs_first_and_receives_all_post_merge_arguments(repo, squash):
    repo.add_lfs()
    before = repo.head
    repo.hook("post-merge", squash, "argument with spaces")
    assert repo.events[0]["kind"] == "lfs"
    assert repo.events[0]["argv"] == ["post-merge", squash, "argument with spaces"]
    if squash == "1":
        assert repo.events == [repo.events[0]]
        assert repo.head == before
        assert not (repo.root / "timestamps").exists()
    else:
        assert [e["kind"] for e in repo.events if e["kind"] != "git-stamp"] == ["lfs", "ots"]
        assert_stamp(repo, before)


@pytest.mark.parametrize("squash", ["0", "1"])
@pytest.mark.parametrize("exit_code", [3, 23])
def test_lfs_failure_is_propagated_and_prevents_stamping(repo, squash, exit_code):
    repo.add_lfs(exit_code)
    before = repo.head
    result = repo.hook("post-merge", squash, check=False)
    assert result.returncode == exit_code
    assert repo.head == before
    assert [e["kind"] for e in repo.events] == ["lfs"]
    assert not (repo.root / "timestamps").exists()
    assert repo.git("status", "--porcelain").stdout == ""


def test_post_merge_works_when_git_lfs_is_absent(repo):
    assert not (repo.runtime.bin_dir / "git-lfs").exists()
    before = repo.head
    repo.hook("post-merge", "0")
    assert_stamp(repo, before)
    assert [e["kind"] for e in repo.events if e["kind"] != "git-stamp"] == ["ots"]


@pytest.mark.parametrize("hook", ["post-commit", "post-merge"])
@pytest.mark.parametrize("subject", ["ots: stamp some-hash", "ots: upgrade proofs", "ots:", "ots:anything"])
def test_all_ots_prefix_commits_are_ignored(repo, hook, subject):
    target = repo.commit_file("maintenance.txt", "maintenance\n", subject)
    repo.clear_events()
    repo.hook(hook, *(["0"] if hook == "post-merge" else []))
    assert repo.head == target
    assert repo.events == []
    assert not (repo.root / "timestamps").exists()


def test_git_commit_with_ots_subject_is_not_stamped(repo):
    repo.git("commit", "--allow-empty", "-m", "ots: maintenance")
    assert repo.subject == "ots: maintenance"
    assert repo.events == []
    assert not (repo.root / "timestamps").exists()
    assert repo.git("rev-list", "--count", f"{repo.base}..HEAD").stdout.strip() == "1"


@pytest.mark.parametrize("hook", ["post-commit", "post-merge"])
@pytest.mark.parametrize("location", ["pending", "anchored"])
def test_existing_proof_is_an_idempotency_guard_without_rewriting_it(repo, hook, location):
    target = repo.head
    proof = repo.seed_proof(target, location)
    before_status = repo.git("status", "--porcelain").stdout
    before_index = repo.git("ls-files", "--stage").stdout
    repo.clear_events()
    for _ in range(2):
        repo.hook(hook, *(["0"] if hook == "post-merge" else []))
    assert repo.head == target
    assert proof.read_text() == "existing proof: must stay unchanged\n"
    assert not (repo.root / "timestamps" / target).exists()
    assert repo.events == []
    assert repo.git("status", "--porcelain").stdout == before_status
    assert repo.git("ls-files", "--stage").stdout == before_index


def test_hash_file_without_a_proof_is_still_stamped(repo):
    target = repo.head
    directory = repo.root / "timestamps"
    directory.mkdir()
    (directory / target).write_text(target + "\n")
    repo.hook("post-commit")
    assert_stamp(repo, target)


def test_a_proof_for_another_commit_does_not_skip_the_current_commit(repo):
    repo.hook("post-commit")
    assert_stamp(repo, repo.base)
    previous_stamp = repo.head
    repo.clear_events()
    repo.git("commit", "--allow-empty", "-m", "second experiment")
    target = repo.git("rev-parse", "HEAD^").stdout.strip()
    assert repo.git("rev-parse", f"{target}^").stdout.strip() == previous_stamp
    assert_stamp(repo, target)
    assert (repo.root / "timestamps" / f"{repo.base}.ots").exists()


@pytest.mark.parametrize("operation", ["fast-forward", "pull"])
@pytest.mark.parametrize("location", ["pending", "anchored"])
def test_fast_forward_and_pull_do_not_restamp_existing_proofs(repo, operation, location):
    target = repo.commit_file("feature.txt", "feature\n", "incoming feature", branch="feature")
    repo.git("checkout", "main")
    proof = repo.seed_proof(target, location)
    repo.clear_events()
    if operation == "pull":
        repo.git("pull", "--ff-only", str(repo.root), "feature")
    else:
        repo.git("merge", "--ff-only", "feature")
    assert repo.head == target
    assert proof.read_text() == "existing proof: must stay unchanged\n"
    assert repo.events == []
    assert not (repo.root / "timestamps" / target).exists()
    assert repo.hook_calls("post-merge") == [["0"]]
    # Another post-merge invocation while HEAD still points at the source commit.
    repo.hook("post-merge", "0")
    assert repo.head == target
    assert repo.events == []


@pytest.mark.parametrize("operation", ["fast-forward", "pull"])
def test_fast_forward_and_pull_stamp_an_unstamped_tip_once(repo, operation):
    target = repo.commit_file("feature.txt", "feature\n", "incoming feature", branch="feature")
    repo.git("checkout", "main")
    repo.clear_events()
    if operation == "pull":
        repo.git("pull", "--ff-only", str(repo.root), "feature")
    else:
        repo.git("merge", "--ff-only", "feature")
    stamp = assert_stamp(repo, target)
    repo.hook("post-merge", "0")
    assert repo.head == stamp
    assert len([e for e in repo.events if e["kind"] == "ots"]) == 1


@pytest.mark.parametrize("hook", ["post-commit", "post-merge"])
def test_missing_ots_warns_and_exits_zero_without_committing(repo, hook):
    (repo.root / ".venv/bin/ots").unlink()
    before = repo.head
    result = repo.hook(hook, *(["0"] if hook == "post-merge" else []))
    assert result.returncode == 0
    assert "ots:" in result.stderr
    assert "client not found" in result.stderr
    assert "skipping timestamp" in result.stderr
    assert "scripts/install-hooks.sh" in result.stderr
    assert repo.head == before
    assert repo.events == []
    assert not (repo.root / "timestamps").exists()
    assert repo.git("status", "--porcelain").stdout == ""


def test_missing_ots_does_not_fail_a_real_user_commit(repo):
    (repo.root / ".venv/bin/ots").unlink()
    result = repo.git("commit", "--allow-empty", "-m", "experiment without OTS")
    assert "client not found" in result.stderr
    assert repo.subject == "experiment without OTS"
    assert repo.git("rev-list", "--count", f"{repo.base}..HEAD").stdout.strip() == "1"
    assert repo.events == []
    assert not (repo.root / "timestamps").exists()


@pytest.mark.parametrize("hook", ["post-commit", "post-merge"])
def test_ots_prefix_is_ignored_even_without_a_client(repo, hook):
    (repo.root / ".venv/bin/ots").unlink()
    target = repo.commit_file("maintenance.txt", "maintenance\n", "ots: maintenance")
    repo.clear_events()
    result = repo.hook(hook, *(["0"] if hook == "post-merge" else []))
    assert result.stderr == ""
    assert repo.head == target
    assert repo.events == []
    assert not (repo.root / "timestamps").exists()


@pytest.mark.parametrize("action", ["commit", "merge"])
def test_linked_worktree_without_venv_finds_main_checkout_ots(repo, action):
    if action == "merge":
        feature = repo.commit_file("feature.txt", "feature\n", "feature", branch="feature")
        repo.git("checkout", "main")
    worktree = repo.root / ".worktrees/x"
    repo.git("worktree", "add", "-b", "worktree-test", str(worktree), "main")
    assert (worktree / ".git").is_file()
    assert not (worktree / ".venv").exists()
    repo.clear_events()
    repo.git("commit", "--allow-empty", "-m", "worktree experiment", cwd=worktree)
    first_target = repo.git("rev-parse", "HEAD^", cwd=worktree).stdout.strip()
    assert_stamp(repo, first_target, cwd=worktree)
    if action == "merge":
        before = repo.git("rev-parse", "HEAD", cwd=worktree).stdout.strip()
        repo.clear_events()
        repo.git("merge", "--no-ff", "feature", "-m", "worktree merge", cwd=worktree)
        target = repo.git("rev-parse", "HEAD^", cwd=worktree).stdout.strip()
        assert repo.git("show", "-s", "--format=%P", target, cwd=worktree).stdout.split() == [before, feature]
        assert_stamp(repo, target, cwd=worktree)
        assert repo.hook_calls("post-merge") == [["0"]]
    assert repo.head == repo.base, "a worktree stamp must not advance the main branch"
    assert not (repo.root / "timestamps").exists()


def test_linked_worktree_warns_when_neither_checkout_has_ots(repo):
    (repo.root / ".venv/bin/ots").unlink()
    worktree = repo.root / ".worktrees/x"
    repo.git("worktree", "add", "-b", "without-ots", str(worktree))
    repo.clear_events()
    result = repo.git("commit", "--allow-empty", "-m", "worktree without client", cwd=worktree)
    assert "client not found" in result.stderr
    assert str(worktree / ".venv") in result.stderr
    assert str(repo.root / ".venv") in result.stderr
    assert repo.git("log", "-1", "--format=%s", cwd=worktree).stdout.strip() == "worktree without client"
    assert repo.events == []
    assert not (worktree / "timestamps").exists()
    assert not (repo.root / "timestamps").exists()


@pytest.mark.parametrize("hook", ["post-commit", "post-merge"])
def test_stamp_commit_has_a_real_valid_signature_despite_conflicting_config(repo, require_signing, hook):
    assert repo.git("config", "--get", "commit.gpgSign").stdout.strip() == "false"
    assert repo.git("config", "--get", "user.signingkey").stdout.strip() == "DEADBEEFDEADBEEF"
    assert "OTS_VALIDATION_UNSIGNED_STAMPS" not in repo.env
    target = repo.head
    repo.hook(hook, *(["0"] if hook == "post-merge" else []))
    stamp = assert_stamp(repo, target)
    assert_stamp_identity(repo)
    raw = repo.git("cat-file", "commit", stamp).stdout
    assert "\ngpgsig -----BEGIN PGP SIGNATURE-----\n" in raw
    verified = repo.git("verify-commit", "--raw", stamp)
    assert "[GNUPG:] VALIDSIG " in verified.stderr
    valid_signatures = [line.split() for line in verified.stderr.splitlines()
                        if line.startswith("[GNUPG:] VALIDSIG ")]
    assert any(SIGNING_KEY in (fields[2], fields[-1]) for fields in valid_signatures), verified.stderr
    assert STAMP_EMAIL in verified.stderr
    signature = repo.git("show", "-s", "--format=%G?%n%GF%n%GP", stamp).stdout.splitlines()
    assert signature[0] in {"G", "U"}, signature
    assert SIGNING_KEY in signature[1:], signature


@pytest.mark.parametrize("action", ["commit", "merge", "resolved-conflict", "worktree-commit"])
def test_stamp_author_and_committer_override_the_original_git_identity(repo, action):
    checkout = repo.root
    if action in {"merge", "resolved-conflict"}:
        repo.divergent_branches(conflict=action == "resolved-conflict")
        result = repo.git("merge", "--no-ff", "feature", "-m", "identity merge", check=False)
        if action == "resolved-conflict":
            assert result.returncode == 1
            (repo.root / "base.txt").write_text("resolved\n")
            repo.git("add", "base.txt")
            repo.git("commit", "-m", "identity conflict resolution")
        else:
            assert result.returncode == 0, result.stderr
    else:
        if action == "worktree-commit":
            checkout = repo.root / ".worktrees/identity"
            repo.git("worktree", "add", "-b", "identity-test", str(checkout))
            repo.clear_events()
        repo.git("commit", "--allow-empty", "-m", "identity experiment", cwd=checkout)
    target = repo.git("rev-parse", "HEAD^", cwd=checkout).stdout.strip()
    assert repo.git("log", "-1", "--format=%s", cwd=checkout).stdout.strip() == f"ots: stamp {target}"
    assert_stamp_identity(repo, cwd=checkout)
