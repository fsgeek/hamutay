"""Independent numerical validation of Task 5: Statistical measurement contracts,
analytical codebook distortion quadrature, block partitioning, bootstrap intervals,
and gate evaluation rules.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from hamutay.turboquant import (
    GateResult,
    QualificationConfig,
    QualificationMetrics,
    QualificationResult,
    analytic_codebook_distortion,
    bootstrap_mean_interval,
    evaluate_algorithm_gates,
    lloyd_max_codebook,
    partition_block_ids,
)
from hamutay.turboquant.qualification import author_code_differential_gate


class TestAnalyticDistortionQuadrature:
    """Validates analytic integration of squared error over Lloyd-Max cells in FP64."""

    @pytest.mark.parametrize(
        ("b", "registered_reference"),
        [
            (1, 0.36088859),
            (2, 0.11600007),
            (3, 0.03396593),
            (4, 0.00931479),
        ],
    )
    def test_analytic_distortion_frozen_regression_values(
        self, b: int, registered_reference: float
    ) -> None:
        """Contract: For d=128, exact quadrature matches registered values to high precision."""
        d = 128
        cb = lloyd_max_codebook(d, b)
        observed = analytic_codebook_distortion(cb, d)

        assert math.isclose(observed, registered_reference, rel_tol=1e-5)

    def test_analytic_distortion_strictly_monotonic(self) -> None:
        d = 128
        dists = [analytic_codebook_distortion(lloyd_max_codebook(d, b), d) for b in (1, 2, 3, 4)]
        assert dists[0] > dists[1] > dists[2] > dists[3]


class TestPartitionBlockIDs:
    """Validates sample partitioning into contiguous equal blocks."""

    def test_partition_contiguous_and_equal(self) -> None:
        sample_count = 12
        block_count = 3
        block_ids = partition_block_ids(sample_count, block_count)

        assert block_ids.dtype == np.int64
        assert block_ids.shape == (12,)
        expected = np.array([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2], dtype=np.int64)
        np.testing.assert_array_equal(block_ids, expected)

    def test_partition_indivisible_rejection(self) -> None:
        with pytest.raises(ValueError):
            partition_block_ids(10, 3)

    def test_partition_invalid_inputs(self) -> None:
        with pytest.raises(ValueError):
            partition_block_ids(0, 1)
        with pytest.raises(ValueError):
            partition_block_ids(10, 0)


class TestBootstrapMeanInterval:
    """Validates block-bootstrap percentile interval calculation."""

    def test_bootstrap_interval_properties(self) -> None:
        rng = np.random.default_rng(1212)
        # Block means drawn from N(0, 1)
        block_means = rng.standard_normal(1000)

        ci_95 = bootstrap_mean_interval(block_means, rng=rng, resamples=5000, confidence=0.95)
        ci_9875 = bootstrap_mean_interval(block_means, rng=rng, resamples=5000, confidence=0.9875)

        assert isinstance(ci_95, tuple) and len(ci_95) == 2
        assert isinstance(ci_95[0], float) and isinstance(ci_95[1], float)
        assert ci_95[0] < ci_95[1]

        # 98.75% CI must be strictly wider than 95% CI
        assert ci_9875[0] <= ci_95[0]
        assert ci_9875[1] >= ci_95[1]

        # Determinism with identical generator state
        rng_a = np.random.default_rng(42)
        rng_b = np.random.default_rng(42)
        ci_a = bootstrap_mean_interval(block_means, rng=rng_a, resamples=1000, confidence=0.95)
        ci_b = bootstrap_mean_interval(block_means, rng=rng_b, resamples=1000, confidence=0.95)
        assert ci_a == ci_b

    def test_bootstrap_invalid_arguments(self) -> None:
        rng = np.random.default_rng(1)
        with pytest.raises(ValueError):
            bootstrap_mean_interval([], rng=rng)
        with pytest.raises(ValueError):
            bootstrap_mean_interval([1.0, 2.0], rng=rng, confidence=1.0)
        with pytest.raises(ValueError):
            bootstrap_mean_interval([1.0, 2.0], rng=rng, confidence=0.0)


class TestGateEvaluation:
    """Validates algorithm gate evaluations against the 4 public algorithmic gates."""

    def _make_metric(self, bits: int, pass_mse: bool, pass_bias: bool, pass_prod: bool) -> QualificationMetrics:
        d = 128
        mse_target = {1: 0.36088859, 2: 0.11600007, 3: 0.03396593, 4: 0.00931479}[bits]
        paper_mse = {1: 0.36, 2: 0.117, 3: 0.03, 4: 0.009}[bits]
        prod_target = {1: 1.57 / d, 2: 0.56 / d, 3: 0.18 / d, 4: 0.047 / d}[bits]

        mse_obs = mse_target * (1.001 if pass_mse else 1.05)  # 0.5% tolerance
        prod_obs = prod_target * (1.01 if pass_prod else 1.25)  # 15% tolerance

        rmse = 0.1
        # Equivalence region: [-0.02*rmse, +0.02*rmse] = [-0.002, +0.002]
        ci9875 = (-0.001, 0.001) if pass_bias else (-0.005, 0.005)

        return QualificationMetrics(
            bits=bits,
            mse_observed=mse_obs,
            mse_analytic_target=mse_target,
            mse_paper_target=paper_mse,
            product_observed=prod_obs,
            product_paper_target=prod_target,
            normalized_bias_mean=0.0,
            normalized_bias_rmse=rmse,
            normalized_bias_ci95=(-0.0008, 0.0008),
            normalized_bias_ci9875=ci9875,
        )

    def test_evaluate_algorithm_gates_all_pass(self) -> None:
        metrics = tuple(self._make_metric(b, True, True, True) for b in (1, 2, 3, 4))
        result = QualificationResult(metrics=metrics, determinism_passed=True)

        gates = evaluate_algorithm_gates(result)
        assert len(gates) == 4
        gate_names = [g.name for g in gates]
        assert gate_names == [
            "round_trip_determinism",
            "mse_distortion",
            "qjl_bias_equivalence",
            "published_qjl_distortion",
        ]
        assert all(g.passed for g in gates)
        assert all(g.status == "passed" for g in gates)

    def test_evaluate_algorithm_gates_mse_failure(self) -> None:
        # Bit 2 fails MSE
        metrics = (
            self._make_metric(1, True, True, True),
            self._make_metric(2, False, True, True),
            self._make_metric(3, True, True, True),
            self._make_metric(4, True, True, True),
        )
        result = QualificationResult(metrics=metrics, determinism_passed=True)
        gates = evaluate_algorithm_gates(result)

        gate_map = {g.name: g for g in gates}
        assert gate_map["mse_distortion"].passed is False
        assert gate_map["mse_distortion"].status == "failed"

    def test_author_code_differential_gate_adapter(self) -> None:
        # When oracle_result is None -> not_run
        gate_none = author_code_differential_gate(None)
        assert isinstance(gate_none, GateResult)
        assert gate_none.name == "author_code_differential"
        assert gate_none.passed is False
        assert gate_none.status == "not_run"

        # Valid passing oracle payload
        oracle_payload = {
            "status": "passed",
            "gate": {
                "name": "author_code_differential",
                "passed": True,
                "threshold": {"atol": 1e-5, "rtol": 1e-4},
                "observed": {"inlier_sign_bytes_equal": True},
                "detail": "CUDA differential matched reference FP32",
            },
        }
        gate_passed = author_code_differential_gate(oracle_payload)
        assert gate_passed.passed is True
        assert gate_passed.status == "passed"
