"""Shared fixtures and oracles for TurboQuant R1 validation."""

from __future__ import annotations

import os
from pathlib import Path
import pytest
import numpy as np


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root directory."""
    return Path.cwd()


@pytest.fixture
def unique_run_id() -> str:
    """Generate a unique run ID for isolated test evidence."""
    import uuid
    return f"val_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def dev_output_root(repo_root: Path) -> Path:
    """Return the canonical development output root."""
    path = repo_root / "experiments" / "turboquant" / "development"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def registered_output_root(repo_root: Path) -> Path:
    """Return the canonical registered qualification output root."""
    path = repo_root / "experiments" / "turboquant" / "qualification"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def author_checkout_path() -> Path | None:
    """Return the path to the pinned author QJL checkout if available."""
    checkout_str = os.environ.get("QJL_AUTHOR_CHECKOUT")
    if not checkout_str:
        return None
    path = Path(checkout_str)
    return path if path.exists() else None
