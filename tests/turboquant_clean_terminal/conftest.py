"""Pytest configuration and shared fixtures for TurboQuant clean terminal validation suite.

Transport Signing Identity:
    Tony Mason; hamutay@wamason.com; 01193FA2631C8AE8E4DF266E216D3C9B920813A1
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import uuid
import numpy as np
import pytest
import torch

from hamutay.turboquant.artifacts import create_run_directory
from hamutay.turboquant.qualify import main


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Returns the resolved root path of the actual repository."""
    return Path.cwd().resolve()


@pytest.fixture(scope="session")
def author_checkout_path() -> Path:
    """Resolves and validates the declared author checkout path from environment.
    
    Tests must fail in this declared environment if the required checkout is missing.
    """
    checkout_env = os.environ.get("QJL_AUTHOR_CHECKOUT")
    assert checkout_env is not None, (
        "Declared environment variable QJL_AUTHOR_CHECKOUT must be set; "
        "tests must fail for missing required evidence in this declared environment."
    )
    checkout = Path(checkout_env).resolve()
    assert checkout.is_dir(), (
        f"Declared author checkout path {checkout} does not exist or is not a directory."
    )
    return checkout


@pytest.fixture(scope="session")
def cuda_device() -> str:
    """Validates CUDA device availability in the declared environment."""
    assert torch.cuda.is_available(), (
        "CUDA must be available in declared environment; tests must fail if missing."
    )
    return "cuda:0"


@pytest.fixture(scope="session")
def author_adapter(repo_root: Path):
    """Loads the public author QJL adapter functions."""
    try:
        import scripts.turboquant.author_qjl_oracle as adapter
        return adapter
    except ImportError:
        script_path = repo_root / "scripts" / "turboquant" / "author_qjl_oracle.py"
        assert script_path.is_file(), f"Author adapter script missing at {script_path}"
        spec = importlib.util.spec_from_file_location("author_qjl_oracle", script_path)
        assert spec is not None and spec.loader is not None
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        return adapter


@pytest.fixture(scope="session")
def dev_run_output_root(repo_root: Path) -> Path:
    """Returns the declared repository-relative development output root."""
    root = repo_root / "experiments" / "turboquant" / "development"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture(scope="session")
def shared_dev_run_with_author(
    repo_root: Path,
    author_checkout_path: Path,
    dev_run_output_root: Path,
    cuda_device: str,
) -> Path:
    """Executes a development CLI run with author checkout using explicit small counts.
    
    Preserves research evidence using a unique run ID under experiments/turboquant/development.
    Task8 precedes registered scientific qualification: does NOT launch registered computation.
    """
    unique_run_id = f"tq_clean_val_{uuid.uuid4().hex[:10]}"
    run_dir = dev_run_output_root / unique_run_id

    argv = [
        "--profile", "development",
        "--output-root", str(dev_run_output_root),
        "--run-id", unique_run_id,
        "--dimension", "128",
        "--sample-count", "8000",
        "--batch-size", "4000",
        "--bootstrap-blocks", "10",
        "--bootstrap-resamples", "100",
        "--bits", "1,2,3,4",
        "--author-qjl-checkout", str(author_checkout_path),
    ]

    exit_code = main(argv)
    assert exit_code == 0, f"Development CLI invocation failed with exit code {exit_code}"
    assert run_dir.is_dir(), f"Expected run directory was not created: {run_dir}"
    return run_dir
