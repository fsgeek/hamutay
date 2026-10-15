import pytest
import subprocess
from pathlib import Path

@pytest.mark.slow
def test_author_qjl_differential_oracle_script(author_qjl_checkout, dev_output_root, run_id):
    run_dir = dev_output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    res = subprocess.run([
        "python", "scripts/turboquant/author_qjl_oracle.py",
        "--checkout", str(author_qjl_checkout),
        "--output", str(run_dir),
        "--device", "cuda:0"
    ], capture_output=True, text=True)
    
    assert res.returncode == 0, f"Author oracle failed: {res.stderr}"
    
    assert (run_dir / "author_qjl_differential.json").exists()
    assert (run_dir / "author_qjl_differential.npz").exists()
