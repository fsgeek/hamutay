import pytest
from pathlib import Path


@pytest.fixture
def ledger_path(tmp_path) -> Path:
    d = tmp_path / "community" / "plaza"
    d.mkdir(parents=True)
    return d / "assembly.jsonl"
