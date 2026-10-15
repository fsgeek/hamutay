import numpy as np
import pytest
from hamutay.turboquant.qualification import (
    QualificationConfig,
    QualificationMetrics,
    QualificationResult,
    GateResult,
    run_synthetic_qualification,
    analytic_codebook_distortion,
    bootstrap_mean_interval,
    evaluate_algorithm_gates,
    partition_block_ids,
    author_code_differential_gate
)

def test_qualification_config_bounds():
    with pytest.raises(Exception):
        QualificationConfig(dimension=1, sample_count=10, batch_size=5, bootstrap_blocks=2, bootstrap_resamples=10, bits=(1,))
    with pytest.raises(Exception):
        QualificationConfig(dimension=128, sample_count=0, batch_size=5, bootstrap_blocks=2, bootstrap_resamples=10, bits=(1,))
    with pytest.raises(Exception):
        QualificationConfig(dimension=128, sample_count=10, batch_size=5, bootstrap_blocks=2, bootstrap_resamples=10, bits=(1, 5))
    with pytest.raises(Exception):
        QualificationConfig(dimension=128, sample_count=10, batch_size=5, bootstrap_blocks=2, bootstrap_resamples=10, bits=(1, 1))
    with pytest.raises(Exception):
        QualificationConfig(dimension=128, sample_count=10, batch_size=5, bootstrap_blocks=2, bootstrap_resamples=10, bits=())
    with pytest.raises(Exception): # boolean
        QualificationConfig(dimension=128, sample_count=10, batch_size=5, bootstrap_blocks=2, bootstrap_resamples=10, bits=(1, True))
    with pytest.raises(Exception): # indivisible
        QualificationConfig(dimension=128, sample_count=10, batch_size=3, bootstrap_blocks=2, bootstrap_resamples=10, bits=(1,))

def test_qualification_metrics_defaults():
    qm = QualificationMetrics(bits=1, mse_observed=0.1, mse_analytic_target=0.1, mse_paper_target=0.1, product_observed=0.1, product_paper_target=0.1, normalized_bias_mean=0.0, normalized_bias_rmse=0.1, normalized_bias_ci95=(0.0, 0.1), normalized_bias_ci9875=(0.0, 0.1))
    assert qm.sample_count == 0
    assert qm.product_mse_bits == 0
    assert qm.product_analytic_target == 0.0
    assert qm.sensitivity_product_observed == 0.0
    assert qm.sensitivity_normalized_bias_mean == 0.0
    assert qm.sensitivity_normalized_bias_rmse == 0.0
    assert qm.sensitivity_normalized_bias_ci95 == (0.0, 0.0)
    assert qm.sensitivity_normalized_bias_ci9875 == (0.0, 0.0)
    assert qm.mse_block_means == ()

def test_qualification_metrics_bounds():
    base = dict(bits=1, mse_observed=0.1, mse_analytic_target=0.1, mse_paper_target=0.1, product_observed=0.1, product_paper_target=0.1, normalized_bias_mean=0.0, normalized_bias_rmse=0.1, normalized_bias_ci95=(0.0, 0.1), normalized_bias_ci9875=(0.0, 0.1))
    with pytest.raises(Exception):
        QualificationMetrics(**{**base, "mse_observed": -0.1})
    with pytest.raises(Exception):
        QualificationMetrics(**{**base, "mse_analytic_target": 0.0})
    with pytest.raises(Exception):
        QualificationMetrics(**{**base, "normalized_bias_ci95": (0.1, 0.0)})
    with pytest.raises(Exception):
        QualificationMetrics(**{**base, "mse_observed": float("inf")})
    with pytest.raises(Exception):
        QualificationMetrics(**{**base, "mse_block_means": (1.0,), "product_block_means": (1.0, 2.0)})
    with pytest.raises(Exception):
        QualificationMetrics(**{**base, "bits": 5})
    with pytest.raises(Exception):
        QualificationMetrics(**{**base, "product_mse_bits": 4})

def test_qualification_result_bounds():
    qm = QualificationMetrics(bits=1, mse_observed=0.1, mse_analytic_target=0.1, mse_paper_target=0.1, product_observed=0.1, product_paper_target=0.1, normalized_bias_mean=0.0, normalized_bias_rmse=0.1, normalized_bias_ci95=(0.0, 0.1), normalized_bias_ci9875=(0.0, 0.1))
    qm2 = QualificationMetrics(bits=1, mse_observed=0.1, mse_analytic_target=0.1, mse_paper_target=0.1, product_observed=0.1, product_paper_target=0.1, normalized_bias_mean=0.0, normalized_bias_rmse=0.1, normalized_bias_ci95=(0.0, 0.1), normalized_bias_ci9875=(0.0, 0.1))
    
    with pytest.raises(Exception):
        QualificationResult(metrics=(), determinism_passed=True)
    with pytest.raises(Exception):
        QualificationResult(metrics=(qm, qm2), determinism_passed=True)
        
    qr = QualificationResult(metrics=(qm,), determinism_passed=np.bool_(True))
    assert type(qr.determinism_passed) is bool

def test_gate_result_bounds():
    with pytest.raises(Exception):
        GateResult(name="a", passed=True, observed=1, threshold=1, detail="a", status="failed")
    with pytest.raises(Exception):
        GateResult(name="", passed=True, observed=1, threshold=1, detail="a")
        
    gr = GateResult(name="a", passed=False, observed=1, threshold=1, detail="a", status="not_run")
    assert gr.status == "not_run"

def test_partition_block_ids():
    blocks = partition_block_ids(10, 2)
    np.testing.assert_array_equal(blocks, np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1]))
    with pytest.raises(Exception):
        partition_block_ids(10, 3)

def test_bootstrap_mean_interval_bounds():
    rng = np.random.default_rng(0)
    with pytest.raises(Exception):
        bootstrap_mean_interval(np.array([]), rng=rng, resamples=10, confidence=0.95)
    with pytest.raises(Exception):
        bootstrap_mean_interval(np.array([[1.0]]), rng=rng, resamples=10, confidence=0.95)
    with pytest.raises(Exception):
        bootstrap_mean_interval(np.array([float("inf")]), rng=rng, resamples=10, confidence=0.95)
    with pytest.raises(Exception):
        bootstrap_mean_interval(np.array([1.0, 2.0]), rng=rng, resamples=10, confidence=1.0)
    
    ci = bootstrap_mean_interval(np.array([1.0, 2.0]), rng=rng, resamples=10, confidence=0.95)
    assert len(ci) == 2
    assert ci[0] <= ci[1]

def test_author_code_differential_gate():
    gate = author_code_differential_gate(None)
    assert not gate.passed
    assert gate.status == "not_run"
    assert gate.observed == "not_run"
    
    gate2 = author_code_differential_gate({
        "status": "passed",
        "gate": {
            "name": "author_code_differential",
            "passed": True,
            "observed": "pass",
            "threshold": {"atol": 1e-5, "rtol": 1e-4},
            "detail": "ok"
        }
    })
    assert gate2.passed
    assert gate2.status == "passed"
    
    with pytest.raises(ValueError):
        author_code_differential_gate({
            "status": "failed",
            "gate": {
                "name": "author_code_differential",
                "passed": True,
                "observed": "pass",
                "threshold": {"atol": 1e-5, "rtol": 1e-4},
                "detail": "ok"
            }
        })

def test_evaluate_algorithm_gates_names():
    qm = QualificationMetrics(bits=1, mse_observed=0.1, mse_analytic_target=0.1, mse_paper_target=0.1, product_observed=0.1, product_paper_target=0.1, normalized_bias_mean=0.0, normalized_bias_rmse=0.1, normalized_bias_ci95=(0.0, 0.1), normalized_bias_ci9875=(0.0, 0.1))
    res = QualificationResult(metrics=(qm,), determinism_passed=True)
    gates = evaluate_algorithm_gates(res)
    assert len(gates) == 4
    names = [g.name for g in gates]
    assert names == ["round_trip_determinism", "mse_distortion", "qjl_bias_equivalence", "published_qjl_distortion"]

def test_run_synthetic_qualification():
    cfg = QualificationConfig(dimension=128, sample_count=4, batch_size=4, bootstrap_blocks=2, bootstrap_resamples=10, bits=(1,))
    res = run_synthetic_qualification(cfg)
    assert isinstance(res, QualificationResult)
    assert not res.determinism_passed

def test_analytic_codebook_distortion():
    cb = np.array([-1.0, 1.0], dtype=np.float32)
    val = analytic_codebook_distortion(cb, 128)
    assert isinstance(val, float)
    assert val >= 0.0
