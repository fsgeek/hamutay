import pytest
import numpy as np

from hamutay.turboquant.qualification import (
    QualificationConfig, QualificationMetrics, QualificationResult, GateResult,
    partition_block_ids, analytic_codebook_distortion, bootstrap_mean_interval,
    evaluate_algorithm_gates
)

def test_partition_block_ids():
    blocks = partition_block_ids(sample_count=100, block_count=10)
    assert len(blocks) == 10
    assert all(len(b) == 10 for b in blocks)
    
    with pytest.raises(Exception):
        partition_block_ids(100, 3)

def test_qualification_types():
    config = QualificationConfig()
    assert config.dimension == 128
    assert config.bits == (1, 2, 3, 4)
    
    metrics = QualificationMetrics(
        bits=1,
        mse_observed=0.36,
        mse_analytic_target=0.36,
        mse_paper_target=0.36,
        product_observed=0.01,
        product_paper_target=0.01,
        normalized_bias_mean=0.0,
        normalized_bias_rmse=0.01,
        normalized_bias_ci95=(-0.01, 0.01),
        normalized_bias_ci9875=(-0.01, 0.01)
    )
    
    res = QualificationResult(metrics=(metrics,), determinism_passed=True, configuration=config)
    
    gates = evaluate_algorithm_gates(res)
    assert len(gates) == 4
    names = [g.name for g in gates]
    assert "round_trip_determinism" in names
    assert "mse_distortion" in names
    assert "qjl_bias_equivalence" in names
    assert "published_qjl_distortion" in names

def test_analytic_codebook_distortion():
    cb = np.array([-0.5, 0.5], dtype=np.float32)
    val = analytic_codebook_distortion(cb, dimension=128)
    assert isinstance(val, float)
    assert val > 0

def test_bootstrap_mean_interval():
    rng = np.random.default_rng(123)
    means = np.linspace(-1.0, 1.0, 100)
    low, high = bootstrap_mean_interval(means, rng=rng, resamples=1000, confidence=0.95)
    assert low <= np.mean(means) <= high

def test_evaluate_algorithm_gates_status():
    metrics = QualificationMetrics(
        bits=1,
        mse_observed=999.0, # Intentional huge error to fail mse_distortion
        mse_analytic_target=0.36,
        mse_paper_target=0.36,
        product_observed=999.0, # Intentional huge error to fail published_qjl_distortion
        product_paper_target=0.01,
        normalized_bias_mean=0.5, # Huge bias to fail qjl_bias_equivalence
        normalized_bias_rmse=0.01,
        normalized_bias_ci95=(0.4, 0.6),
        normalized_bias_ci9875=(0.4, 0.6)
    )
    res = QualificationResult(metrics=(metrics,), determinism_passed=False)
    gates = evaluate_algorithm_gates(res)
    
    for gate in gates:
        assert gate.passed is False
        assert gate.status == "failed"
