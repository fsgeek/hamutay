"""Fixtures keep hook tests independent of host Git configuration and clients."""

import pytest

from .helpers import Repo, make_runtime, signing_probe


@pytest.fixture(scope="session")
def signing_reason(tmp_path_factory):
    root = tmp_path_factory.mktemp("ots-signing-probe")
    runtime = make_runtime(root)
    return signing_probe(runtime, root / "repo")


@pytest.fixture
def runtime(tmp_path, signing_reason):
    runtime = make_runtime(tmp_path / "runtime")
    runtime.signing_reason = signing_reason
    return runtime


@pytest.fixture
def repo(tmp_path, runtime):
    # Spaces also test quoting of hook paths, OTS paths and installer paths.
    return Repo(tmp_path / "checkout with spaces", runtime)


@pytest.fixture
def require_signing(signing_reason):
    if signing_reason:
        pytest.skip(f"Real GPG signing unavailable: {signing_reason}")
