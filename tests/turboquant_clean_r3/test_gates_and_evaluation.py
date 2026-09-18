"""Tests for Task 5: Streaming Statistics, Analytic Quadrature, and Gate Evaluation."""

from __future__ import annotations

import math
import numpy as np
import pytest

from hamutay.turboquant import (
    QualificationConfig,
    QualificationMetrics,
    QualificationResult,
    GateResult,
    partition_block_ids,
    analytic_codebook_distortion,
    evaluate_algorithm_gates,
    lloyd_max_codebook,
)


def test_partition_block_ids_contract() -> None:
    """Verify partition_block_ids assigns contiguous equal blocks and rejects indivisible counts."""
    # Divisible case: 12 samples, 3 blocks -> [0,0,0,0, 1,1,1,1, 2,2,2,2]
    ids = partition_block_ids(12, 3)
    assert ids.dtype == np.int64
    assert ids.shape == (12,)
    assert np.array_equal(ids, np.array([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2], dtype=np.int64))

    # Indivisible case: 10 samples, 3 blocks -> ValueError
    with pytest.raises(ValueError):
        partition_block_ids(10, 3)


def test_analytic_codebook_distortion_reference_targets() -> None:
    """Verify analytic_codebook_distortion against frozen regression reference values."""
    d = 128
    # Registered reference values from pre-implementation FP64 quadrature
    reference_targets = {
        1: 0.36088859,
        2: 0.11600007,
        3: 0.03396593,
        4: 0.00931479,
    }

    for bits, expected in reference_targets.items():
        cb = lloyd_max_codebook(d, bits)
        observed = analytic_codebook_distortion(cb, d)
        rel_err = abs(observed - expected) / expected
        assert rel_err < 1e-4, f"Analytic distortion at {bits} bits differed: {observed} vs {expected}"


def _make_dummy_metrics(
    bits: int,
    mse_obs: float,
    mse_analytic: float,
    mse_paper: float,
    prod_obs: float,
    prod_paper: float,
    bias_ci9875: tuple[float, float],
    rmse: float,
) -> QualificationMetrics:
    """Helper to construct a valid QualificationMetrics instance."""
    return QualificationMetrics(
        bits=bits,
        mse_observed=mse_obs,
        mse_analytic_target=mse_analytic,
        mse_paper_target=mse_paper,
        product_observed=prod_obs,
        product_paper_target=prod_paper,
        normalized_bias_mean=0.0,
        normalized_bias_rmse=rmse,
        normalized_bias_ci95=(-0.01 * rmse, 0.01 * rmse),
        normalized_bias_ci9875=bias_ci9875,
    )


def test_evaluate_algorithm_gates_all_pass() -> None:
    """Verify evaluate_algorithm_gates passes all 4 gates when acceptable evidence is provided."""
    d = 128
    paper_mse = (0.36, 0.117, 0.03, 0.009)
    analytic_mse = (0.36088859, 0.11600007, 0.03396593, 0.00931479)
    paper_prod = (1.57 / d, 0.56 / d, 0.18 / d, 0.047 / d)

    metrics_list = []
    for i, b in enumerate([1, 2, 3, 4]):
        rmse = 0.1
        # 98.75% CI safely within [-0.02 * rmse, +0.02 * rmse] = [-0.002, +0.002]
        ci9875 = (-0.015 * rmse, 0.015 * rmse)
        m = _make_dummy_metrics(
            bits=b,
            mse_obs=analytic_mse[i] * 1.002,  # 0.2% error (passes <= 0.5%)
            mse_analytic=analytic_mse[i],
            mse_paper=paper_mse[i],           # (passes <= 15%)
            prod_obs=paper_prod[i] * 1.05,    # 5% error (passes <= 15%)
            prod_paper=paper_prod[i],
            bias_ci9875=ci9875,
            rmse=rmse,
        )
        metrics_list.append(m)

    result = QualificationResult(
        metrics=tuple(metrics_list),
        determinism_passed=True,
        sample_count=1_000_000,
        dimension=d,
    )

    gates = evaluate_algorithm_gates(result)
    assert len(gates) == 4
    gate_dict = {g.name: g for g in gates}

    assert gate_dict["round_trip_determinism"].passed is True
    assert gate_dict["round_trip_determinism"].status == "passed"
    assert gate_dict["mse_distortion"].passed is True
    assert gate_dict["mse_distortion"].status == "passed"
    assert gate_dict["qjl_bias_equivalence"].passed is True
    assert gate_dict["qjl_bias_equivalence"].status == "passed"
    assert gate_dict["published_qjl_distortion"].passed is True
    assert gate_dict["published_qjl_distortion"].status == "passed"


def test_evaluate_algorithm_gates_determinism_rejection() -> None:
    """Verify round_trip_determinism fails when determinism_passed=False."""
    result = QualificationResult(
        metrics=(),
        determinism_passed=False,
    )
    gates = evaluate_algorithm_gates(result)
    gate_dict = {g.name: g for g in gates}
    assert gate_dict["round_trip_determinism"].passed is False
    assert gate_dict["round_trip_determinism"].status == "failed"


def test_evaluate_algorithm_gates_mse_distortion_boundaries() -> None:
    """Verify mse_distortion gate strictly enforces 0.5% analytic and 15% paper tolerances."""
    d = 128
    analytic_val = 0.36088859
    paper_val = 0.36
    rmse = 0.1

    # Case A: Fails analytic tolerance (0.51% > 0.5%) even if paper matches
    m_fail_analytic = _make_dummy_metrics(
        bits=1,
        mse_obs=analytic_val * 1.0051,
        mse_analytic=analytic_val,
        mse_paper=paper_val,
        prod_obs=1.57 / d,
        prod_paper=1.57 / d,
        bias_ci9875=(-0.001, 0.001),
        rmse=rmse,
    )
    res_fail_a = QualificationResult(metrics=(m_fail_analytic,), determinism_passed=True)
    gates_a = {g.name: g for g in evaluate_algorithm_gates(res_fail_a)}
    assert gates_a["mse_distortion"].passed is False
    assert gates_a["mse_distortion"].status == "failed"

    # Case B: Fails paper tolerance (15.1% > 15%) even if analytic matches
    m_fail_paper = _make_dummy_metrics(
        bits=1,
        mse_obs=analytic_val,
        mse_analytic=analytic_val,
        mse_paper=analytic_val / 1.151,  # Obs is 15.1% higher than paper
        prod_obs=1.57 / d,
        prod_paper=1.57 / d,
        bias_ci9875=(-0.001, 0.001),
        rmse=rmse,
    )
    res_fail_b = QualificationResult(metrics=(m_fail_paper,), determinism_passed=True)
    gates_b = {g.name: g for g in evaluate_algorithm_gates(res_fail_b)}
    assert gates_b["mse_distortion"].passed is False


def test_evaluate_algorithm_gates_qjl_bias_equivalence_boundaries() -> None:
    """Verify qjl_bias_equivalence fails when 98.75% CI extends beyond [-0.02*rmse, +0.02*rmse]."""
    d = 128
    rmse = 1.0  # equivalence region is [-0.02, +0.02]

    # Lower bound violation: ci_low = -0.0201
    m_fail_low = _make_dummy_metrics(
        bits=1,
        mse_obs=0.36088859,
        mse_analytic=0.36088859,
        mse_paper=0.36,
        prod_obs=1.57 / d,
        prod_paper=1.57 / d,
        bias_ci9875=(-0.0201, 0.015),
        rmse=rmse,
    )
    res_low = QualificationResult(metrics=(m_fail_low,), determinism_passed=True)
    gates_low = {g.name: g for g in evaluate_algorithm_gates(res_low)}
    assert gates_low["qjl_bias_equivalence"].passed is False

    # Upper bound violation: ci_high = +0.0201
    m_fail_high = _make_dummy_metrics(
        bits=1,
        mse_obs=0.36088859,
        mse_analytic=0.36088859,
        mse_paper=0.36,
        prod_obs=1.57 / d,
        prod_paper=1.57 / d,
        bias_ci9875=(-0.015, 0.0201),
        rmse=rmse,
    )
    res_high = QualificationResult(metrics=(m_fail_high,), determinism_passed=True)
    gates_high = {g.name: g for g in evaluate_algorithm_gates(res_high)}
    assert gates_high["qjl_bias_equivalence"].passed is False


def test_evaluate_algorithm_gates_published_qjl_distortion_boundaries() -> None:
    """Verify published_qjl_distortion fails when empirical error exceeds 15% tolerance."""
    d = 128
    paper_target = 1.57 / d
    rmse = 0.1

    # 15.1% relative error violation
    m_fail_qjl = _make_dummy_metrics(
        bits=1,
        mse_obs=0.36088859,
        mse_analytic=0.36088859,
        mse_paper=0.36,
        prod_obs=paper_target * 1.151,
        prod_paper=paper_target,
        bias_ci9875=(-0.001, 0.001),
        rmse=rmse,
    )
    res = QualificationResult(metrics=(m_fail_qjl,), determinism_passed=True)
    gates = {g.name: g for g in evaluate_algorithm_gates(res)}
    assert gates["published_qjl_distortion"].passed is False
    assert gates["published_qjl_distortion"].status == "failed"


def test_gate_result_contract_and_distinctions() -> None:
    """Verify GateResult dataclass properties, non-empty names/details, and status resolution."""
    # Status defaults to 'passed' if passed=True
    gr_pass = GateResult(
        name="test_gate",
        passed=True,
        observed=0.1,
        threshold=0.2,
        detail="Observed 0.1 <= threshold 0.2",
    )
    assert gr_pass.status == "passed"
    assert gr_pass.name != ""
    assert gr_pass.detail != ""

    # Status defaults to 'failed' if passed=False
    gr_fail = GateResult(
        name="test_gate",
        passed=False,
        observed=0.3,
        threshold=0.2,
        detail="Observed 0.3 > threshold 0.2",
    )
    assert gr_fail.status == "failed"
