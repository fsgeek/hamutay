import os
import sys
from pathlib import Path
import pytest
import importlib.util

def load_oracle():
    script_path = Path.cwd() / "scripts" / "turboquant" / "author_qjl_oracle.py"
    if not script_path.exists():
        pytest.skip("Oracle script not found in expected relative path")
    spec = importlib.util.spec_from_file_location("author_qjl_oracle", script_path)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    return oracle

def test_verify_missing(tmp_path):
    oracle = load_oracle()
    with pytest.raises(Exception):
        oracle.verify_pinned_checkout(tmp_path)

def test_author_differential_flow(tmp_path):
    checkout_str = os.environ.get("QJL_AUTHOR_CHECKOUT")
    if not checkout_str:
        pytest.skip("QJL_AUTHOR_CHECKOUT not mapped in test environment")
    checkout = Path(checkout_str)
    
    oracle = load_oracle()
    
    result = oracle.verify_pinned_checkout(checkout)
    assert result["clean"] is True
    assert result["commit"] == "648b3641f96b6e95e091217220b94e4739fd4d82"
    
    preflight = oracle.preflight_author_qjl(checkout=checkout, device="cuda:0")
    assert "environment" in preflight
    assert "upstream" in preflight
    assert "status" not in preflight
    
    out = tmp_path / "diff"
    out.mkdir()
    diff = oracle.run_author_qjl_differential(checkout=checkout, output=out, device="cuda:0")
    
    assert diff["schema"] == "hamutay.turboquant.author-qjl.v1"
    assert "status" in diff
    assert "study_seed_hex" in diff
    assert "seed_fields" in diff
    assert "environment" in diff
    assert "upstream" in diff
    assert "extensions" in diff
    assert "batch" in diff
    assert "conventions" in diff
    assert "comparisons" in diff
    assert "gate" in diff
    assert "arrays" in diff
    assert "npz" in diff
    
    assert "status" not in diff["gate"]
    assert "passed" in diff["gate"]
    
    assert (out / "author_qjl_differential.json").exists()
    assert (out / "author_qjl_differential.npz").exists()
    
    # Standalone adapter refuses existing evidence
    with pytest.raises(Exception):
        oracle.run_author_qjl_differential(checkout=checkout, output=out, device="cuda:0")
