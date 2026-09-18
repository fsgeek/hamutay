import os
import pytest
import uuid
from pathlib import Path

@pytest.fixture
def run_id():
    return f"test-run-{uuid.uuid4().hex[:8]}"

@pytest.fixture
def dev_output_root(tmp_path):
    root = tmp_path / "experiments" / "turboquant" / "development"
    root.mkdir(parents=True, exist_ok=True)
    return root

@pytest.fixture
def reg_output_root(tmp_path):
    root = tmp_path / "experiments" / "turboquant" / "qualification"
    root.mkdir(parents=True, exist_ok=True)
    return root

@pytest.fixture
def author_qjl_checkout():
    checkout = os.environ.get("QJL_AUTHOR_CHECKOUT")
    if not checkout:
        pytest.skip("QJL_AUTHOR_CHECKOUT environment variable not set")
    return Path(checkout)
