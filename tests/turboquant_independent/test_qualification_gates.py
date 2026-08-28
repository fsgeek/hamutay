"""Independent tests of the R1 gate logic and streaming statistics.

The gates decide whether a scientific experiment is allowed to proceed, so
the adversarial emphasis here is on gates that must FAIL. A gate that passes
everything is worse than no gate at all.
"""

from __future__ import annotations

import numpy as np
import pytest

from hamutay.turboquant.qualification import (
    GateResult,
    QualificationConfig,
    QualificationMetrics,
    QualificationResult,
    analytic_codebook_distortion,
    bootstrap_mean_interval,
    evaluate_algorithm_gates,
    partition_block_ids,
)

from .conftest import (
    ANALYTIC_MSE_DISTORTION,
    REGISTERED_DIMENSION,
    reference_analytic_distortion,
)

REQUIRED_GATE_NAMES = {
    "round_trip_determinism",
    "mse_distortion",
    "qjl_bias_equivalence",
    "published_qjl_distortion",
    "author_code_differential",
}


def passing_metric(bits: int = 1) -> QualificationMetrics:
    """A metric set comfortably inside every registered gate boundary."""
    return QualificationMetrics(
        bits=bits,
        mse_observed=0.36,
        mse_analytic_target=0.36,
        mse_paper_target=0.36,
        product_observed=1.57 / REGISTERED_DIMENSION,
        product_paper_target=1.57 / REGISTERED_DIMENSION,
        normalized_bias_mean=0.0,
        normalized_bias_rmse=0.1,
        normalized_bias_ci95=(-0.0001, 0.0001),
        normalized_bias_ci9875=(-0.0002, 0.0002),
    )


def gate_named(result: QualificationResult, name: str) -> GateResult:
    return next(g for g in evaluate_algorithm_gates(result) if g.name == name)


class TestAnalyticCodebookDistortion:
    @pytest.mark.parametrize("bits", [1, 2, 3, 4])
    def test_matches_independent_quadrature_and_registered_values(self, bits):
        from hamutay.turboquant.codebook import lloyd_max_codebook

        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, bits)
        observed = analytic_codebook_distortion(codebook, REGISTERED_DIMENSION)

        assert abs(observed - reference_analytic_distortion(
            codebook, REGISTERED_DIMENSION
        )) < 1e-7
        expected = ANALYTIC_MSE_DISTORTION[bits]
        assert abs(observed - expected) / expected < 5e-6

    def test_is_computed_from_the_supplied_codebook_not_a_lookup_table(self):
        """Perturbing the codebook must raise its distortion; a hard-coded
        table would return the same value regardless of input."""
        from hamutay.turboquant.codebook import lloyd_max_codebook

        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, 2)
        optimal = analytic_codebook_distortion(codebook, REGISTERED_DIMENSION)

        perturbed = np.array(codebook, dtype=np.float32, copy=True)
        perturbed[0] = np.float32(perturbed[0] * 0.5)
        perturbed[-1] = np.float32(perturbed[-1] * 0.5)
        degraded = analytic_codebook_distortion(perturbed, REGISTERED_DIMENSION)

        assert degraded > optimal * 1.01

    def test_scaling_is_by_dimension(self):
        """Distortion is normalized as d * sum of per-cell squared error."""
        from hamutay.turboquant.codebook import lloyd_max_codebook

        for dimension in (64, 128):
            codebook = lloyd_max_codebook(dimension, 2)
            observed = analytic_codebook_distortion(codebook, dimension)
            assert abs(
                observed - reference_analytic_distortion(codebook, dimension)
            ) < 1e-7


class TestBlockPartitioning:
    def test_blocks_are_contiguous_and_cover_every_sample_once(self):
        ids = partition_block_ids(sample_count=12, block_count=4)
        assert ids.tolist() == [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3]

    def test_registered_shape_is_one_thousand_blocks_of_one_thousand(self):
        ids = partition_block_ids(sample_count=1_000_000, block_count=1000)
        assert ids.shape == (1_000_000,)
        counts = np.bincount(ids)
        assert counts.size == 1000
        assert np.all(counts == 1000)

    def test_non_divisible_inputs_are_rejected(self):
        """The spec forbids a short final block, which would silently
        down-weight the tail of the sample in the bootstrap."""
        with pytest.raises(ValueError):
            partition_block_ids(sample_count=10, block_count=3)


class TestBootstrap:
    def test_is_repeatable_for_a_fixed_generator(self):
        values = np.arange(20, dtype=np.float64)
        first = bootstrap_mean_interval(
            values, rng=np.random.default_rng(7), resamples=2000
        )
        second = bootstrap_mean_interval(
            values, rng=np.random.default_rng(7), resamples=2000
        )
        assert first == second
        assert first[0] < values.mean() < first[1]

    def test_interval_brackets_the_mean_and_is_ordered(self):
        rng = np.random.default_rng(8)
        values = rng.normal(loc=2.5, scale=1.0, size=500)
        low, high = bootstrap_mean_interval(
            values, rng=np.random.default_rng(9), resamples=2000
        )
        assert low < high
        assert low < float(values.mean()) < high

    def test_higher_confidence_gives_a_wider_interval(self):
        rng = np.random.default_rng(10)
        values = rng.normal(size=400)
        narrow = bootstrap_mean_interval(
            values, rng=np.random.default_rng(11), resamples=4000, confidence=0.95
        )
        wide = bootstrap_mean_interval(
            values, rng=np.random.default_rng(11), resamples=4000, confidence=0.9875
        )
        assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])

    def test_interval_narrows_as_the_sample_grows(self):
        rng = np.random.default_rng(12)
        small = bootstrap_mean_interval(
            rng.normal(size=50), rng=np.random.default_rng(13), resamples=2000
        )
        large = bootstrap_mean_interval(
            rng.normal(size=5000), rng=np.random.default_rng(13), resamples=2000
        )
        assert (large[1] - large[0]) < (small[1] - small[0])

    def test_zero_variance_input_gives_a_degenerate_interval(self):
        values = np.full(100, 3.0)
        low, high = bootstrap_mean_interval(
            values, rng=np.random.default_rng(14), resamples=500
        )
        assert low == pytest.approx(3.0)
        assert high == pytest.approx(3.0)


class TestGateEvaluation:
    def test_all_five_registered_gates_are_reported(self):
        result = QualificationResult(
            metrics=tuple(passing_metric(b) for b in (1, 2, 3, 4)),
            determinism_passed=True,
        )
        gates = evaluate_algorithm_gates(result)
        assert all(isinstance(gate, GateResult) for gate in gates)
        names = {gate.name for gate in gates}
        assert REQUIRED_GATE_NAMES.issubset(names)

    def test_values_inside_every_boundary_pass(self):
        metrics = tuple(
            QualificationMetrics(
                bits=bits,
                mse_observed=1.0049,
                mse_analytic_target=1.0,
                mse_paper_target=1.0049 / 1.149,
                product_observed=1.149,
                product_paper_target=1.0,
                normalized_bias_mean=0.0,
                normalized_bias_rmse=0.1,
                normalized_bias_ci95=(-0.0001, 0.0001),
                normalized_bias_ci9875=(-0.00199, 0.00199),
            )
            for bits in (1, 2, 3, 4)
        )
        result = QualificationResult(metrics=metrics, determinism_passed=True)
        gates = [
            g
            for g in evaluate_algorithm_gates(result)
            if g.name != "author_code_differential"
        ]
        assert gates and all(gate.passed for gate in gates)

    def test_analytic_mismatch_fails_even_when_the_paper_target_matches(self):
        metric = QualificationMetrics(
            bits=1,
            mse_observed=0.36,
            mse_analytic_target=0.35,
            mse_paper_target=0.36,
            product_observed=1.57 / REGISTERED_DIMENSION,
            product_paper_target=1.57 / REGISTERED_DIMENSION,
            normalized_bias_mean=0.0,
            normalized_bias_rmse=0.1,
            normalized_bias_ci95=(-0.0001, 0.0001),
            normalized_bias_ci9875=(-0.001, 0.001),
        )
        result = QualificationResult(metrics=(metric,), determinism_passed=True)
        assert not gate_named(result, "mse_distortion").passed

    def test_analytic_tolerance_boundary_is_half_a_percent(self):
        """Inside 0.5% passes, outside fails."""
        def build(observed: float) -> QualificationResult:
            metric = QualificationMetrics(
                bits=1,
                mse_observed=observed,
                mse_analytic_target=1.0,
                mse_paper_target=observed,
                product_observed=1.0,
                product_paper_target=1.0,
                normalized_bias_mean=0.0,
                normalized_bias_rmse=0.1,
                normalized_bias_ci95=(-0.0001, 0.0001),
                normalized_bias_ci9875=(-0.001, 0.001),
            )
            return QualificationResult(metrics=(metric,), determinism_passed=True)

        assert gate_named(build(1.004), "mse_distortion").passed
        assert not gate_named(build(1.02), "mse_distortion").passed

    def test_paper_mismatch_fails_even_when_the_analytic_target_matches(self):
        metric = QualificationMetrics(
            bits=1,
            mse_observed=1.0,
            mse_analytic_target=1.0,
            mse_paper_target=0.5,
            product_observed=1.0,
            product_paper_target=1.0,
            normalized_bias_mean=0.0,
            normalized_bias_rmse=0.1,
            normalized_bias_ci95=(-0.0001, 0.0001),
            normalized_bias_ci9875=(-0.001, 0.001),
        )
        result = QualificationResult(metrics=(metric,), determinism_passed=True)
        assert not gate_named(result, "mse_distortion").passed

    def test_bias_gate_rejects_an_interval_outside_the_equivalence_region(self):
        metric = QualificationMetrics(
            bits=1,
            mse_observed=0.36,
            mse_analytic_target=0.36,
            mse_paper_target=0.36,
            product_observed=1.57 / REGISTERED_DIMENSION,
            product_paper_target=1.57 / REGISTERED_DIMENSION,
            normalized_bias_mean=0.0005,
            normalized_bias_rmse=0.1,
            normalized_bias_ci95=(-0.0005, 0.0015),
            normalized_bias_ci9875=(-0.001, 0.0021),
        )
        result = QualificationResult(metrics=(metric,), determinism_passed=True)
        assert not gate_named(result, "qjl_bias_equivalence").passed

    def test_bias_gate_uses_the_simultaneous_interval_not_the_ordinary_one(self):
        """The 98.75% interval breaches +/-0.02*rmse while the 95% interval
        does not. Gating on the 95% interval would wrongly pass."""
        metric = QualificationMetrics(
            bits=1,
            mse_observed=0.36,
            mse_analytic_target=0.36,
            mse_paper_target=0.36,
            product_observed=1.57 / REGISTERED_DIMENSION,
            product_paper_target=1.57 / REGISTERED_DIMENSION,
            normalized_bias_mean=0.0,
            normalized_bias_rmse=0.1,
            normalized_bias_ci95=(-0.0015, 0.0015),
            normalized_bias_ci9875=(-0.0025, 0.0025),
        )
        result = QualificationResult(metrics=(metric,), determinism_passed=True)
        assert not gate_named(result, "qjl_bias_equivalence").passed

    def test_bias_gate_does_not_require_the_interval_to_contain_zero(self):
        """Spec: 'inclusion of zero is not itself a gate.' A tight interval
        wholly inside the equivalence region passes even if it excludes zero."""
        metric = QualificationMetrics(
            bits=1,
            mse_observed=0.36,
            mse_analytic_target=0.36,
            mse_paper_target=0.36,
            product_observed=1.57 / REGISTERED_DIMENSION,
            product_paper_target=1.57 / REGISTERED_DIMENSION,
            normalized_bias_mean=0.0005,
            normalized_bias_rmse=0.1,
            normalized_bias_ci95=(0.0004, 0.0006),
            normalized_bias_ci9875=(0.0003, 0.0007),
        )
        result = QualificationResult(metrics=(metric,), determinism_passed=True)
        assert gate_named(result, "qjl_bias_equivalence").passed

    def test_bias_gate_fails_when_any_single_bit_width_breaches(self):
        """Simultaneous equivalence: one bad bit width fails the whole gate."""
        good = [passing_metric(b) for b in (1, 2, 3)]
        bad = QualificationMetrics(
            bits=4,
            mse_observed=0.36,
            mse_analytic_target=0.36,
            mse_paper_target=0.36,
            product_observed=1.57 / REGISTERED_DIMENSION,
            product_paper_target=1.57 / REGISTERED_DIMENSION,
            normalized_bias_mean=0.05,
            normalized_bias_rmse=0.1,
            normalized_bias_ci95=(0.04, 0.06),
            normalized_bias_ci9875=(0.03, 0.07),
        )
        result = QualificationResult(
            metrics=tuple(good) + (bad,), determinism_passed=True
        )
        assert not gate_named(result, "qjl_bias_equivalence").passed

    def test_published_qjl_distortion_boundary_is_fifteen_percent(self):
        def build(observed: float) -> QualificationResult:
            metric = QualificationMetrics(
                bits=1,
                mse_observed=0.36,
                mse_analytic_target=0.36,
                mse_paper_target=0.36,
                product_observed=observed,
                product_paper_target=1.0,
                normalized_bias_mean=0.0,
                normalized_bias_rmse=0.1,
                normalized_bias_ci95=(-0.0001, 0.0001),
                normalized_bias_ci9875=(-0.001, 0.001),
            )
            return QualificationResult(metrics=(metric,), determinism_passed=True)

        assert gate_named(build(1.14), "published_qjl_distortion").passed
        assert not gate_named(build(1.20), "published_qjl_distortion").passed
        assert not gate_named(build(0.80), "published_qjl_distortion").passed

    def test_determinism_failure_fails_its_gate(self):
        result = QualificationResult(
            metrics=tuple(passing_metric(b) for b in (1, 2, 3, 4)),
            determinism_passed=False,
        )
        assert not gate_named(result, "round_trip_determinism").passed

    def test_author_differential_is_never_silently_passed_when_absent(self):
        """Development mode omits the checkout; the gate must then report
        not-run or failed, never passed."""
        result = QualificationResult(
            metrics=tuple(passing_metric(b) for b in (1, 2, 3, 4)),
            determinism_passed=True,
        )
        gates = {gate.name: gate for gate in evaluate_algorithm_gates(result)}
        differential = gates.get("author_code_differential")
        if differential is not None:
            assert not differential.passed


class TestConfigValidation:
    def test_registered_defaults_match_the_specification(self):
        config = QualificationConfig()
        assert config.dimension == 128
        assert config.sample_count == 1_000_000
        assert config.bootstrap_blocks == 1000
        assert config.bootstrap_resamples == 10_000
        assert tuple(config.bits) == (1, 2, 3, 4)
        assert config.sample_count % config.batch_size == 0
        assert config.sample_count % config.bootstrap_blocks == 0

    def test_non_divisible_batch_size_is_rejected(self):
        with pytest.raises(ValueError):
            QualificationConfig(sample_count=1000, batch_size=333)

    def test_non_divisible_block_count_is_rejected(self):
        with pytest.raises(ValueError):
            QualificationConfig(sample_count=1000, batch_size=100, bootstrap_blocks=3)

    def test_nonpositive_counts_are_rejected(self):
        for kwargs in (
            {"sample_count": 0},
            {"batch_size": 0},
            {"bootstrap_blocks": 0},
            {"bootstrap_resamples": 0},
        ):
            with pytest.raises(ValueError):
                QualificationConfig(**kwargs)

    def test_out_of_range_bit_widths_are_rejected(self):
        for bits in ((0,), (5,), (1, 9)):
            with pytest.raises(ValueError):
                QualificationConfig(bits=bits)
