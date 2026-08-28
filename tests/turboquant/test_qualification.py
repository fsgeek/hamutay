import json
from dataclasses import asdict

import numpy as np
import pytest

from hamutay.turboquant.codebook import lloyd_max_codebook
from hamutay.turboquant.mse import MSEQuantizer
from hamutay.turboquant.product import ProductQuantizer
from hamutay.turboquant.qualification import (
    GateResult,
    QualificationConfig,
    QualificationMetrics,
    QualificationResult,
    _bias_intervals,
    _normalized_product_errors,
    _paper_projection,
    _row_orthogonal_projection,
    analytic_codebook_distortion,
    bootstrap_mean_interval,
    evaluate_algorithm_gates,
    partition_block_ids,
    run_synthetic_qualification,
)
from hamutay.turboquant.rotation import canonical_qr, gaussian_rotation
from hamutay.turboquant.seeding import rng_for


def _passing_metric(bits: int) -> QualificationMetrics:
    return QualificationMetrics(
        bits=bits,
        mse_observed=1.0049,
        mse_analytic_target=1.0,
        mse_paper_target=1.0049 / 1.149,
        product_observed=23.0,
        product_paper_target=20.0,
        normalized_bias_mean=0.0,
        normalized_bias_rmse=0.1,
        normalized_bias_ci95=(-0.0001, 0.0001),
        normalized_bias_ci9875=(-0.002, 0.002),
    )


def _gate(result: QualificationResult, name: str) -> GateResult:
    return next(gate for gate in evaluate_algorithm_gates(result) if gate.name == name)


def test_registered_config_defaults_freeze_batch_and_block_counts():
    config = QualificationConfig()

    assert config == QualificationConfig(
        dimension=128,
        sample_count=1_000_000,
        batch_size=4000,
        bootstrap_blocks=1000,
        bootstrap_resamples=10_000,
        bits=(1, 2, 3, 4),
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"dimension": 1},
        {"sample_count": 0},
        {"batch_size": 0},
        {"bootstrap_blocks": 0},
        {"bootstrap_resamples": 0},
        {"sample_count": 12, "batch_size": 5},
        {"sample_count": 12, "bootstrap_blocks": 5},
        {"bits": ()},
        {"bits": (0,)},
        {"bits": (5,)},
        {"bits": (1, 1)},
    ],
)
def test_config_rejects_nonregistered_count_relationships(overrides):
    with pytest.raises(ValueError):
        QualificationConfig(**overrides)


def test_partition_block_ids_covers_each_sample_once():
    ids = partition_block_ids(sample_count=12, block_count=4)
    assert ids.tolist() == [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3]


@pytest.mark.parametrize(
    ("sample_count", "block_count"),
    [(0, 1), (12, 0), (12, 5), (True, 1)],
)
def test_partition_block_ids_rejects_invalid_registered_partitions(
    sample_count, block_count
):
    with pytest.raises(ValueError):
        partition_block_ids(sample_count=sample_count, block_count=block_count)


def test_bootstrap_mean_interval_is_repeatable():
    values = np.arange(20, dtype=np.float64)
    first = bootstrap_mean_interval(
        values, rng=np.random.default_rng(7), resamples=2000
    )
    second = bootstrap_mean_interval(
        values, rng=np.random.default_rng(7), resamples=2000
    )
    assert first == second
    assert first[0] < values.mean() < first[1]


def test_bootstrap_samples_block_means_as_the_resampling_unit():
    interval = bootstrap_mean_interval(
        np.array([0.0, 10.0], dtype=np.float64),
        rng=np.random.default_rng(11),
        resamples=2000,
        confidence=0.95,
    )

    assert interval == (0.0, 10.0)


def test_bias_intervals_use_exact_independent_95_and_9875_streams():
    block_means = (-3.0, -1.0, 0.0, 2.0, 8.0)
    expected = (
        bootstrap_mean_interval(
            block_means,
            rng=rng_for("qualification", "bootstrap", "bias", "0.95", 3),
            resamples=513,
            confidence=0.95,
        ),
        bootstrap_mean_interval(
            block_means,
            rng=rng_for("qualification", "bootstrap", "bias", "0.9875", 3),
            resamples=513,
            confidence=0.9875,
        ),
    )

    assert expected == ((-1.6, 4.6), (-2.3200000000000043, 5.7600000000000025))
    assert (
        _bias_intervals(block_means, bits=3, resamples=513, purpose="bias") == expected
    )


@pytest.mark.parametrize(
    ("values", "resamples", "confidence"),
    [
        ([], 10, 0.95),
        ([1.0, np.nan], 10, 0.95),
        ([1.0], 0, 0.95),
        ([1.0], 10, 0.0),
        ([1.0], 10, 1.0),
    ],
)
def test_bootstrap_rejects_invalid_inputs(values, resamples, confidence):
    with pytest.raises(ValueError):
        bootstrap_mean_interval(
            values,
            rng=np.random.default_rng(1),
            resamples=resamples,
            confidence=confidence,
        )


def test_normalized_product_errors_use_both_squared_vector_norms():
    queries = np.array([[3.0, 4.0]], dtype=np.float32)
    keys = np.array([[0.0, 2.0]], dtype=np.float32)
    estimates = np.array([10.0], dtype=np.float32)

    squared, signed = _normalized_product_errors(queries, keys, estimates)

    np.testing.assert_allclose(signed, [0.2], rtol=0.0, atol=2e-8)
    np.testing.assert_allclose(squared, [0.04], rtol=0.0, atol=2e-8)


def test_row_orthogonal_sensitivity_projection_has_sqrt_d_row_norms():
    projection = _row_orthogonal_projection(8)

    assert projection.dtype == np.float32
    np.testing.assert_allclose(
        np.linalg.norm(projection, axis=1), np.sqrt(8.0), rtol=0.0, atol=2e-6
    )
    np.testing.assert_allclose(
        projection @ projection.T, 8.0 * np.eye(8), rtol=0.0, atol=2e-5
    )


def _independent_registered_projections(
    dimension: int,
) -> tuple[np.ndarray, np.ndarray]:
    paper = rng_for(
        "qualification", "algorithm_2", "paper_literal", "projection"
    ).standard_normal((dimension, dimension))
    sensitivity_source = rng_for(
        "qualification", "algorithm_2", "row_orthogonal", "projection"
    ).standard_normal((dimension, dimension))
    sensitivity = canonical_qr(sensitivity_source.T).T * np.sqrt(dimension)
    return (
        np.ascontiguousarray(paper, dtype=np.float32),
        np.ascontiguousarray(sensitivity, dtype=np.float32),
    )


def test_paper_projection_matches_iid_seed_stream_and_differs_from_sensitivity():
    expected_paper, expected_sensitivity = _independent_registered_projections(8)

    np.testing.assert_array_equal(_paper_projection(8), expected_paper)
    np.testing.assert_array_equal(_row_orthogonal_projection(8), expected_sensitivity)
    assert not np.array_equal(expected_paper, expected_sensitivity)


def _independent_product_block_means(
    config: QualificationConfig, projection: np.ndarray
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    quantizer = ProductQuantizer(
        MSEQuantizer(
            gaussian_rotation(
                config.dimension, "qualification", "algorithm_1", "rotation"
            ),
            lloyd_max_codebook(config.dimension, 0),
        ),
        projection,
    )
    key_rng = rng_for("qualification", "synthetic", "keys")
    query_rng = rng_for("qualification", "synthetic", "queries")
    normalized_squared_batches: list[np.ndarray] = []
    normalized_bias_batches: list[np.ndarray] = []
    for _ in range(0, config.sample_count, config.batch_size):
        keys = key_rng.standard_normal(
            (config.batch_size, config.dimension), dtype=np.float32
        )
        queries = query_rng.standard_normal(
            (config.batch_size, config.dimension), dtype=np.float32
        )
        estimates = quantizer.estimate_inner_products(queries, quantizer.quantize(keys))
        exact = np.sum(queries * keys, axis=-1, dtype=np.float32)
        normalizer = np.sqrt(
            np.sum(queries * queries, axis=-1, dtype=np.float32)
        ) * np.sqrt(np.sum(keys * keys, axis=-1, dtype=np.float32))
        normalized_bias = (estimates - exact) / normalizer
        normalized_bias_batches.append(normalized_bias)
        normalized_squared_batches.append(normalized_bias * normalized_bias)

    block_size = config.sample_count // config.bootstrap_blocks
    normalized_squared = np.concatenate(normalized_squared_batches)
    normalized_bias = np.concatenate(normalized_bias_batches)
    squared_blocks = tuple(
        float(np.sum(block, dtype=np.float64) / block_size)
        for block in normalized_squared.reshape(config.bootstrap_blocks, block_size)
    )
    bias_blocks = tuple(
        float(np.sum(block, dtype=np.float64) / block_size)
        for block in normalized_bias.reshape(config.bootstrap_blocks, block_size)
    )
    return squared_blocks, bias_blocks


def test_streaming_metrics_wire_iid_and_sensitivity_projections_separately():
    config = QualificationConfig(
        dimension=8,
        sample_count=240,
        batch_size=60,
        bootstrap_blocks=12,
        bootstrap_resamples=31,
        bits=(1,),
    )
    expected_paper, expected_sensitivity = _independent_registered_projections(
        config.dimension
    )
    expected_paper_squared, expected_paper_bias = _independent_product_block_means(
        config, expected_paper
    )
    expected_sensitivity_squared, expected_sensitivity_bias = (
        _independent_product_block_means(config, expected_sensitivity)
    )

    metric = run_synthetic_qualification(config).metrics[0]

    np.testing.assert_allclose(
        metric.product_block_means, expected_paper_squared, rtol=0.0, atol=0.0
    )
    np.testing.assert_allclose(
        metric.normalized_bias_block_means,
        expected_paper_bias,
        rtol=0.0,
        atol=0.0,
    )
    np.testing.assert_allclose(
        metric.sensitivity_product_block_means,
        expected_sensitivity_squared,
        rtol=0.0,
        atol=0.0,
    )
    np.testing.assert_allclose(
        metric.sensitivity_bias_block_means,
        expected_sensitivity_bias,
        rtol=0.0,
        atol=0.0,
    )
    assert metric.product_block_means != metric.sensitivity_product_block_means


def test_values_inside_registered_gate_boundaries_pass():
    result = QualificationResult(
        metrics=tuple(_passing_metric(bits) for bits in (1, 2, 3, 4)),
        determinism_passed=True,
    )
    gates = evaluate_algorithm_gates(result)

    assert [gate.name for gate in gates] == [
        "round_trip_determinism",
        "mse_distortion",
        "qjl_bias_equivalence",
        "published_qjl_distortion",
    ]
    assert all(isinstance(gate, GateResult) for gate in gates)
    assert all(gate.passed for gate in gates)


def test_empty_metric_set_cannot_vacuously_pass_all_numerical_gates():
    with pytest.raises(ValueError, match="nonempty"):
        QualificationResult(metrics=(), determinism_passed=True)


def test_bias_gate_rejects_simultaneous_interval_outside_equivalence_region():
    metric = QualificationMetrics(
        bits=1,
        mse_observed=0.36,
        mse_analytic_target=0.36,
        mse_paper_target=0.36,
        product_observed=1.57 / 128,
        product_paper_target=1.57 / 128,
        normalized_bias_mean=0.0005,
        normalized_bias_rmse=0.1,
        normalized_bias_ci95=(-0.0005, 0.0015),
        normalized_bias_ci9875=(-0.001, 0.0021),
    )
    result = QualificationResult(metrics=(metric,), determinism_passed=True)

    assert not _gate(result, "qjl_bias_equivalence").passed


def test_bias_gate_uses_9875_interval_not_narrower_95_diagnostic():
    metric = _passing_metric(1)
    metric = QualificationMetrics(
        **{
            **asdict(metric),
            "normalized_bias_ci95": (-0.1, 0.1),
            "normalized_bias_ci9875": (-0.001, 0.001),
        }
    )

    assert _gate(
        QualificationResult(metrics=(metric,), determinism_passed=True),
        "qjl_bias_equivalence",
    ).passed


def test_mse_gate_rejects_analytic_mismatch_even_when_paper_matches():
    metric = QualificationMetrics(
        bits=1,
        mse_observed=0.36,
        mse_analytic_target=0.35,
        mse_paper_target=0.36,
        product_observed=1.57 / 128,
        product_paper_target=1.57 / 128,
        normalized_bias_mean=0.0,
        normalized_bias_rmse=0.1,
        normalized_bias_ci95=(-0.0001, 0.0001),
        normalized_bias_ci9875=(-0.001, 0.001),
    )
    result = QualificationResult(metrics=(metric,), determinism_passed=True)

    assert not _gate(result, "mse_distortion").passed


def test_mse_gate_uses_target_as_relative_error_denominator():
    metric = _passing_metric(1)
    metric = QualificationMetrics(
        **{
            **asdict(metric),
            "mse_observed": 100.5,
            "mse_analytic_target": 100.0,
            "mse_paper_target": 100.5,
        }
    )

    assert _gate(
        QualificationResult(metrics=(metric,), determinism_passed=True),
        "mse_distortion",
    ).passed


def test_product_gate_uses_fifteen_percent_closed_boundary():
    passing = _passing_metric(1)
    failing = QualificationMetrics(
        **{**asdict(passing), "bits": 2, "product_observed": 1.1500001}
    )
    result = QualificationResult(metrics=(passing, failing), determinism_passed=True)

    gate = _gate(result, "published_qjl_distortion")

    assert not gate.passed
    assert "four-bit" not in gate.detail


def test_published_gate_calls_out_four_bit_paper_rounding():
    result = QualificationResult(metrics=(_passing_metric(4),), determinism_passed=True)

    assert "four-bit" in _gate(result, "published_qjl_distortion").detail


def test_analytic_codebook_distortion_matches_frozen_dimension_128_targets():
    observed = tuple(
        analytic_codebook_distortion(lloyd_max_codebook(128, bits), 128)
        for bits in range(1, 5)
    )

    np.testing.assert_allclose(
        observed,
        (0.36088859, 0.11600007, 0.03396593, 0.00931479),
        rtol=2e-6,
        atol=2e-8,
    )
    assert tuple(round(value, 5) for value in observed) == (
        0.36089,
        0.116,
        0.03397,
        0.00931,
    )


@pytest.fixture(scope="module")
def reduced_results() -> tuple[QualificationResult, QualificationResult]:
    config = QualificationConfig(
        dimension=128,
        sample_count=20_000,
        batch_size=1000,
        bootstrap_blocks=100,
        bootstrap_resamples=200,
        bits=(1, 2),
    )
    return run_synthetic_qualification(config), run_synthetic_qualification(config)


def test_reduced_qualification_is_finite_complete_and_streamed(reduced_results):
    first, _ = reduced_results

    assert first.sample_count == 20_000
    assert first.batch_size == 1000
    assert first.bootstrap_blocks == 100
    assert [metric.bits for metric in first.metrics] == [1, 2]
    for metric in first.metrics:
        scalar_values = (
            metric.mse_observed,
            metric.mse_analytic_target,
            metric.mse_paper_target,
            metric.product_observed,
            metric.product_paper_target,
            metric.product_analytic_target,
            metric.normalized_bias_mean,
            metric.normalized_bias_rmse,
            metric.sensitivity_product_observed,
            metric.sensitivity_normalized_bias_mean,
            metric.sensitivity_normalized_bias_rmse,
        )
        assert np.isfinite(scalar_values).all()
        assert len(metric.mse_block_means) == 100
        assert len(metric.product_block_means) == 100
        assert len(metric.normalized_bias_block_means) == 100
        assert len(metric.sensitivity_product_block_means) == 100
        assert len(metric.sensitivity_bias_block_means) == 100
        assert metric.normalized_bias_ci95[0] <= metric.normalized_bias_ci95[1]
        assert metric.normalized_bias_ci9875[0] <= metric.normalized_bias_ci9875[1]
        assert (
            metric.sensitivity_normalized_bias_ci95[0]
            <= metric.sensitivity_normalized_bias_ci95[1]
        )
        assert (
            metric.sensitivity_normalized_bias_ci9875[0]
            <= metric.sensitivity_normalized_bias_ci9875[1]
        )


def test_reduced_qualification_uses_total_bits_minus_one_for_product(reduced_results):
    first, _ = reduced_results

    assert [metric.product_mse_bits for metric in first.metrics] == [0, 1]
    np.testing.assert_allclose(
        [metric.product_analytic_target for metric in first.metrics],
        [np.pi / (2.0 * 128.0), np.pi * 0.36088859 / (2.0 * 128.0)],
        rtol=2e-6,
        atol=1e-10,
    )


def test_reduced_product_distortion_and_bias_rmse_share_exact_denominator(
    reduced_results,
):
    first, _ = reduced_results

    for metric in first.metrics:
        assert metric.product_observed == pytest.approx(
            metric.normalized_bias_rmse**2, rel=2e-15, abs=1e-18
        )
        assert metric.sensitivity_product_observed == pytest.approx(
            metric.sensitivity_normalized_bias_rmse**2, rel=2e-15, abs=1e-18
        )


def test_reduced_qualification_serializes_identically_on_two_runs(reduced_results):
    first, second = reduced_results

    first_json = json.dumps(asdict(first), sort_keys=True, separators=(",", ":"))
    second_json = json.dumps(asdict(second), sort_keys=True, separators=(",", ":"))
    assert first_json == second_json
