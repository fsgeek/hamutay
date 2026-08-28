"""Independent tests of Algorithm 2 (TurboQuant_prod) and the QJL estimator.

Covers the bit-packing wire format, the zero-sign rule, the literal estimator
formula as written in the paper, statistical unbiasedness, the published
inner-product distortion scale, and the b-1 bit accounting convention.
"""

from __future__ import annotations

import numpy as np
import pytest

from hamutay.turboquant.codebook import lloyd_max_codebook
from hamutay.turboquant.mse import MSEQuantizer
from hamutay.turboquant.product import (
    ProductQuantizer,
    pack_signs,
    unpack_signs,
)
from hamutay.turboquant.rotation import gaussian_rotation
from hamutay.turboquant.seeding import rng_for

from .conftest import (
    PAPER_PROD_DISTORTION_NUMERATOR,
    REGISTERED_DIMENSION,
    reference_pack_signs,
)


def build_product_quantizer(dimension: int, total_bits: int, *, sketch_dim=None):
    """Total-bit convention: b total bits == (b-1)-bit MSE codebook + sketch."""
    rotation = gaussian_rotation(dimension, "algorithm_2", 0, "k", 0, "rotation")
    mse = MSEQuantizer(rotation, lloyd_max_codebook(dimension, total_bits - 1))
    sketch_dim = dimension if sketch_dim is None else sketch_dim
    projection = rng_for("algorithm_2", 0, "k", 0, "projection").standard_normal(
        (sketch_dim, dimension)
    )
    return ProductQuantizer(mse, projection.astype(np.float32))


class TestBitPacking:
    def test_packing_is_little_endian_within_each_byte(self):
        raw = np.array([[1.0, -1.0, 0.0, 2.0, -2.0, -3.0, 4.0, 5.0, -1.0]])
        packed = pack_signs(raw >= 0)
        np.testing.assert_array_equal(packed, [[0b11001101, 0]])

    def test_packing_matches_an_independent_implementation(self):
        rng = np.random.default_rng(21)
        for sketch_dim in (1, 7, 8, 9, 16, 33, 128):
            flags = rng.standard_normal((5, sketch_dim)) >= 0
            np.testing.assert_array_equal(
                pack_signs(flags), reference_pack_signs(flags)
            )

    def test_bit_j_lives_in_byte_j_over_eight_at_position_j_mod_eight(self):
        """Directly asserts the spec's placement rule, one coordinate at a time."""
        sketch_dim = 24
        for coordinate in range(sketch_dim):
            flags = np.zeros((1, sketch_dim), dtype=bool)
            flags[0, coordinate] = True
            packed = pack_signs(flags)
            assert packed.shape == (1, 3)
            for byte_index in range(3):
                expected = (
                    np.uint8(1 << (coordinate % 8))
                    if byte_index == coordinate // 8
                    else np.uint8(0)
                )
                assert packed[0, byte_index] == expected

    def test_packed_shape_is_ceiling_of_sketch_dim_over_eight(self):
        for sketch_dim, expected_bytes in ((1, 1), (8, 1), (9, 2), (127, 16), (128, 16)):
            flags = np.ones((2, sketch_dim), dtype=bool)
            assert pack_signs(flags).shape == (2, expected_bytes)
            assert pack_signs(flags).dtype == np.uint8

    def test_unpack_inverts_pack_and_returns_plus_minus_one(self):
        rng = np.random.default_rng(22)
        for sketch_dim in (5, 8, 12, 128):
            flags = rng.standard_normal((4, sketch_dim)) >= 0
            recovered = unpack_signs(pack_signs(flags), sketch_dim)
            np.testing.assert_array_equal(recovered, np.where(flags, 1.0, -1.0))
            assert set(np.unique(recovered)).issubset({-1.0, 1.0})

    def test_padding_bits_do_not_leak_into_the_unpacked_sketch(self):
        """Trailing bits of the final byte must be ignored, not decoded."""
        sketch_dim = 9
        flags = np.ones((1, sketch_dim), dtype=bool)
        packed = pack_signs(flags)
        polluted = packed.copy()
        polluted[0, 1] |= 0b11111110
        np.testing.assert_array_equal(
            unpack_signs(polluted, sketch_dim), unpack_signs(packed, sketch_dim)
        )

    def test_unused_padding_bits_are_written_as_zero(self):
        packed = pack_signs(np.ones((1, 9), dtype=bool))
        assert packed[0, 1] == 0b00000001

    def test_multi_dimensional_leading_axes_are_preserved(self):
        flags = np.random.default_rng(23).standard_normal((2, 3, 16)) >= 0
        packed = pack_signs(flags)
        assert packed.shape == (2, 3, 2)
        np.testing.assert_array_equal(
            unpack_signs(packed, 16), np.where(flags, 1.0, -1.0)
        )


class TestZeroSignConvention:
    def test_exact_zero_maps_to_positive_in_the_transparent_reference(self):
        """Spec: 'In the transparent reference, every zero sign maps to +1.'
        The author kernel uses '> 0' and maps zero to -1; Task 7 records that
        as a declared difference, so the reference must not adopt it."""
        packed = pack_signs(np.array([[0.0, 0.0, 0.0, 0.0]]) >= 0)
        np.testing.assert_array_equal(packed, [[0b00001111]])
        np.testing.assert_array_equal(
            unpack_signs(packed, 4), [[1.0, 1.0, 1.0, 1.0]]
        )

    def test_zero_residual_projection_yields_all_positive_signs(self):
        """Drive an exact-zero sketch through the real quantizer.

        With an identity rotation and codebook {-c, +c}, a vector whose unit
        form has every coordinate exactly +/-c reconstructs exactly, leaving a
        zero residual and therefore an all-zero sketch. Under the reference
        convention every one of those signs must decode to +1.
        """
        dimension = 16
        centroid = 1.0 / np.sqrt(dimension)
        mse = MSEQuantizer(
            np.eye(dimension, dtype=np.float32),
            np.array([-centroid, centroid], dtype=np.float32),
        )
        quantizer = ProductQuantizer(mse, np.eye(dimension, dtype=np.float32))

        vectors = np.full((1, dimension), centroid, dtype=np.float32)
        codes = quantizer.quantize(vectors)

        assert float(codes.residual_norms[0]) == pytest.approx(0.0, abs=1e-6)
        np.testing.assert_array_equal(
            codes.packed_signs, np.full((1, dimension // 8), 0xFF, dtype=np.uint8)
        )
        np.testing.assert_array_equal(
            unpack_signs(codes.packed_signs, dimension),
            np.ones((1, dimension)),
        )


class TestLiteralEstimator:
    def test_estimator_matches_the_paper_literal_formula(self):
        quantizer = build_product_quantizer(REGISTERED_DIMENSION, 4)
        rng = np.random.default_rng(24)
        keys = rng.standard_normal((16, REGISTERED_DIMENSION)).astype(np.float32)
        queries = rng.standard_normal((16, REGISTERED_DIMENSION)).astype(np.float32)

        codes = quantizer.quantize(keys)
        mse_hat = quantizer.mse_quantizer.dequantize(codes.mse).astype(np.float64)
        projection = np.asarray(quantizer.projection, dtype=np.float64)
        residual = keys.astype(np.float64) - mse_hat
        signs = np.where(residual @ projection.T >= 0, 1.0, -1.0)

        literal = np.sum(queries.astype(np.float64) * mse_hat, axis=-1) + (
            np.sqrt(np.pi / 2.0)
            / quantizer.sketch_dim
            * codes.residual_norms.astype(np.float64)
            * np.sum((queries.astype(np.float64) @ projection.T) * signs, axis=-1)
        )

        observed = quantizer.estimate_inner_products(queries, codes)
        np.testing.assert_allclose(observed, literal, atol=1e-4, rtol=1e-4)

    def test_residual_norm_is_applied_exactly_once(self):
        """The paper's DeQuant_prod folds ||r|| into x_qjl and its estimator
        line multiplies by ||r|| again. Applying gamma twice is a real hazard
        and inflates the QJL term by a factor of ||r||."""
        quantizer = build_product_quantizer(REGISTERED_DIMENSION, 4)
        rng = np.random.default_rng(25)
        keys = (rng.standard_normal((8, REGISTERED_DIMENSION)) * 10.0).astype(
            np.float32
        )
        queries = rng.standard_normal((8, REGISTERED_DIMENSION)).astype(np.float32)

        codes = quantizer.quantize(keys)
        norms = codes.residual_norms.astype(np.float64)
        assert np.all(norms > 1.5), "test needs residual norms far from 1"

        mse_hat = quantizer.mse_quantizer.dequantize(codes.mse).astype(np.float64)
        projection = np.asarray(quantizer.projection, dtype=np.float64)
        signs = np.where(
            (keys.astype(np.float64) - mse_hat) @ projection.T >= 0, 1.0, -1.0
        )
        base = np.sum(queries.astype(np.float64) * mse_hat, axis=-1)
        term = (
            np.sqrt(np.pi / 2.0)
            / quantizer.sketch_dim
            * np.sum((queries.astype(np.float64) @ projection.T) * signs, axis=-1)
        )

        observed = np.asarray(
            quantizer.estimate_inner_products(queries, codes), dtype=np.float64
        )
        once = base + norms * term
        twice = base + norms * norms * term

        assert np.max(np.abs(observed - once)) < np.max(np.abs(observed - twice))
        np.testing.assert_allclose(observed, once, atol=1e-4, rtol=1e-4)

    def test_estimator_agrees_with_dequantized_reconstruction(self):
        """estimate_inner_products must equal <q, dequantize(codes)>."""
        quantizer = build_product_quantizer(REGISTERED_DIMENSION, 3)
        rng = np.random.default_rng(26)
        keys = rng.standard_normal((12, REGISTERED_DIMENSION)).astype(np.float32)
        queries = rng.standard_normal((12, REGISTERED_DIMENSION)).astype(np.float32)

        codes = quantizer.quantize(keys)
        reconstructed = quantizer.dequantize(codes).astype(np.float64)
        expected = np.sum(queries.astype(np.float64) * reconstructed, axis=-1)
        np.testing.assert_allclose(
            quantizer.estimate_inner_products(queries, codes),
            expected,
            atol=1e-3,
            rtol=1e-3,
        )

    def test_sqrt_pi_over_two_scaling_is_present(self):
        """A missing sqrt(pi/2) leaves the estimator biased low by ~20%."""
        dimension = REGISTERED_DIMENSION
        quantizer = build_product_quantizer(dimension, 1)
        rng = np.random.default_rng(27)
        count = 4000
        keys = rng.standard_normal((count, dimension)).astype(np.float32)
        queries = rng.standard_normal((count, dimension)).astype(np.float32)

        codes = quantizer.quantize(keys)
        estimates = np.asarray(
            quantizer.estimate_inner_products(queries, codes), dtype=np.float64
        )
        truth = np.sum(
            queries.astype(np.float64) * keys.astype(np.float64), axis=-1
        )

        # Regress estimates on truth; correct scaling gives slope ~1.
        slope = float(np.dot(estimates, truth) / np.dot(truth, truth))
        assert abs(slope - 1.0) < 0.05
        assert abs(slope - np.sqrt(2.0 / np.pi)) > 0.1

    def test_mismatched_query_and_code_shapes_are_rejected(self):
        quantizer = build_product_quantizer(16, 3)
        codes = quantizer.quantize(
            np.random.default_rng(28).standard_normal((4, 16)).astype(np.float32)
        )
        with pytest.raises(ValueError):
            quantizer.estimate_inner_products(
                np.zeros((5, 16), dtype=np.float32), codes
            )


class TestStatisticalProperties:
    def test_estimator_is_unbiased_over_random_pairs(self):
        """Normalized signed bias must be far inside the registered
        +/- 0.02 * RMSE equivalence region."""
        dimension = REGISTERED_DIMENSION
        quantizer = build_product_quantizer(dimension, 1)
        rng = np.random.default_rng(29)
        count = 40000
        keys = rng.standard_normal((count, dimension)).astype(np.float32)
        queries = rng.standard_normal((count, dimension)).astype(np.float32)

        codes = quantizer.quantize(keys)
        estimates = np.asarray(
            quantizer.estimate_inner_products(queries, codes), dtype=np.float64
        )
        truth = np.sum(
            queries.astype(np.float64) * keys.astype(np.float64), axis=-1
        )
        scale = np.linalg.norm(queries.astype(np.float64), axis=-1) * np.linalg.norm(
            keys.astype(np.float64), axis=-1
        )
        normalized = (estimates - truth) / scale

        mean = float(np.mean(normalized))
        rmse = float(np.sqrt(np.mean(normalized**2)))
        standard_error = float(np.std(normalized)) / np.sqrt(count)

        assert abs(mean) < 4.0 * standard_error
        assert abs(mean) <= 0.02 * rmse

    @pytest.mark.parametrize("total_bits", [1, 2, 3])
    def test_inner_product_distortion_matches_the_published_scale(self, total_bits):
        """Normalized MSE against the paper's (1.57, 0.56, 0.18)/d values.

        Four total bits is deliberately excluded from this gating assertion.
        The spec records that the 4-bit target inherits sensitivity to the
        paper's rounded 3-bit scalar value (0.03 against a true 0.033966),
        and directs that the residual be reported as a non-gating diagnostic.
        See test_four_bit_distortion_is_reported_as_a_diagnostic below.
        """
        dimension = REGISTERED_DIMENSION
        quantizer = build_product_quantizer(dimension, total_bits)
        rng = np.random.default_rng(30 + total_bits)
        count = 30000
        keys = rng.standard_normal((count, dimension)).astype(np.float32)
        queries = rng.standard_normal((count, dimension)).astype(np.float32)

        codes = quantizer.quantize(keys)
        estimates = np.asarray(
            quantizer.estimate_inner_products(queries, codes), dtype=np.float64
        )
        truth = np.sum(
            queries.astype(np.float64) * keys.astype(np.float64), axis=-1
        )
        squared = np.sum(queries.astype(np.float64) ** 2, axis=-1) * np.sum(
            keys.astype(np.float64) ** 2, axis=-1
        )
        observed = float(np.mean((estimates - truth) ** 2 / squared))
        expected = PAPER_PROD_DISTORTION_NUMERATOR[total_bits] / dimension

        assert abs(observed - expected) / expected <= 0.15

    def test_four_bit_distortion_is_reported_as_a_diagnostic(self):
        """Non-gating: assert only the loose order of magnitude.

        The paper's 0.047/d four-bit target inherits rounding from its 3-bit
        scalar value, so a correct implementation can sit slightly outside the
        registered 15% band here. Failing the suite on that would punish the
        implementation for the paper's rounding, so this test bounds the value
        generously and exists to surface the number, not to gate it.
        """
        dimension = REGISTERED_DIMENSION
        quantizer = build_product_quantizer(dimension, 4)
        rng = np.random.default_rng(34)
        count = 20000
        keys = rng.standard_normal((count, dimension)).astype(np.float32)
        queries = rng.standard_normal((count, dimension)).astype(np.float32)

        codes = quantizer.quantize(keys)
        estimates = np.asarray(
            quantizer.estimate_inner_products(queries, codes), dtype=np.float64
        )
        truth = np.sum(
            queries.astype(np.float64) * keys.astype(np.float64), axis=-1
        )
        squared = np.sum(queries.astype(np.float64) ** 2, axis=-1) * np.sum(
            keys.astype(np.float64) ** 2, axis=-1
        )
        observed = float(np.mean((estimates - truth) ** 2 / squared))
        expected = PAPER_PROD_DISTORTION_NUMERATOR[4] / dimension

        assert 0.5 * expected < observed < 1.5 * expected

    def test_distortion_decreases_with_total_bits(self):
        dimension = REGISTERED_DIMENSION
        rng = np.random.default_rng(41)
        count = 8000
        keys = rng.standard_normal((count, dimension)).astype(np.float32)
        queries = rng.standard_normal((count, dimension)).astype(np.float32)
        truth = np.sum(
            queries.astype(np.float64) * keys.astype(np.float64), axis=-1
        )
        squared = np.sum(queries.astype(np.float64) ** 2, axis=-1) * np.sum(
            keys.astype(np.float64) ** 2, axis=-1
        )

        previous = None
        for total_bits in (1, 2, 3, 4):
            quantizer = build_product_quantizer(dimension, total_bits)
            estimates = np.asarray(
                quantizer.estimate_inner_products(
                    queries, quantizer.quantize(keys)
                ),
                dtype=np.float64,
            )
            observed = float(np.mean((estimates - truth) ** 2 / squared))
            if previous is not None:
                assert observed < previous
            previous = observed

class TestProductRepresentation:
    def test_codes_have_the_declared_shapes_and_dtypes(self):
        dimension, sketch_dim = 32, 32
        quantizer = build_product_quantizer(dimension, 3, sketch_dim=sketch_dim)
        vectors = (
            np.random.default_rng(43).standard_normal((6, dimension)).astype(np.float32)
        )
        codes = quantizer.quantize(vectors)

        assert codes.packed_signs.dtype == np.uint8
        assert codes.packed_signs.shape == (6, (sketch_dim + 7) // 8)
        assert codes.residual_norms.dtype == np.float32
        assert codes.residual_norms.shape == (6,)
        assert codes.mse.indices.shape == vectors.shape

    def test_one_total_bit_uses_a_zero_bit_mse_codebook(self):
        """The b-1 convention: a 1-bit product quantizer stores only the sketch."""
        quantizer = build_product_quantizer(REGISTERED_DIMENSION, 1)
        assert quantizer.mse_quantizer.codebook.size == 1
        assert float(quantizer.mse_quantizer.codebook[0]) == 0.0

        vectors = (
            np.random.default_rng(44)
            .standard_normal((4, REGISTERED_DIMENSION))
            .astype(np.float32)
        )
        codes = quantizer.quantize(vectors)
        assert np.all(codes.mse.indices == 0)
        np.testing.assert_allclose(
            codes.residual_norms,
            np.linalg.norm(vectors, axis=-1),
            rtol=1e-5,
        )

    @pytest.mark.parametrize("total_bits", [2, 3, 4])
    def test_mse_component_is_one_bit_smaller_than_the_total(self, total_bits):
        quantizer = build_product_quantizer(REGISTERED_DIMENSION, total_bits)
        assert quantizer.mse_quantizer.codebook.size == 2 ** (total_bits - 1)

    def test_zero_vector_round_trips_to_exact_zero(self):
        quantizer = build_product_quantizer(REGISTERED_DIMENSION, 4)
        vectors = np.zeros((2, REGISTERED_DIMENSION), dtype=np.float32)
        codes = quantizer.quantize(vectors)

        assert np.all(codes.residual_norms == 0.0)
        assert np.all(codes.mse.indices == 0)
        assert np.all(codes.mse.norms == 0.0)
        reconstructed = quantizer.dequantize(codes)
        assert np.array_equal(reconstructed, vectors)
        assert np.all(np.isfinite(reconstructed))

    def test_zero_vector_estimates_exactly_zero_inner_product(self):
        quantizer = build_product_quantizer(REGISTERED_DIMENSION, 4)
        codes = quantizer.quantize(
            np.zeros((3, REGISTERED_DIMENSION), dtype=np.float32)
        )
        queries = (
            np.random.default_rng(45)
            .standard_normal((3, REGISTERED_DIMENSION))
            .astype(np.float32)
        )
        estimates = np.asarray(quantizer.estimate_inner_products(queries, codes))
        np.testing.assert_array_equal(estimates, np.zeros(3, dtype=estimates.dtype))

    def test_zero_and_nonzero_rows_coexist_without_nan(self):
        quantizer = build_product_quantizer(16, 3)
        vectors = np.zeros((3, 16), dtype=np.float32)
        vectors[1] = np.arange(16, dtype=np.float32) - 7.5
        codes = quantizer.quantize(vectors)
        reconstructed = quantizer.dequantize(codes)

        assert np.all(np.isfinite(reconstructed))
        np.testing.assert_array_equal(reconstructed[0], np.zeros(16, dtype=np.float32))
        np.testing.assert_array_equal(reconstructed[2], np.zeros(16, dtype=np.float32))

    def test_quantization_is_bit_repeatable(self):
        quantizer = build_product_quantizer(REGISTERED_DIMENSION, 4)
        vectors = (
            np.random.default_rng(46)
            .standard_normal((32, REGISTERED_DIMENSION))
            .astype(np.float32)
        )
        first = quantizer.quantize(vectors)
        second = quantizer.quantize(vectors.copy())
        np.testing.assert_array_equal(first.packed_signs, second.packed_signs)
        np.testing.assert_array_equal(first.residual_norms, second.residual_norms)
        np.testing.assert_array_equal(first.mse.indices, second.mse.indices)
        np.testing.assert_array_equal(
            quantizer.dequantize(first), quantizer.dequantize(second)
        )

    def test_registered_projection_is_not_orthogonalized(self):
        """The paper-literal projection is iid Gaussian. An orthogonalized
        matrix has near-constant row norms; an iid one does not."""
        quantizer = build_product_quantizer(REGISTERED_DIMENSION, 4)
        projection = np.asarray(quantizer.projection, dtype=np.float64)
        row_norms = np.linalg.norm(projection, axis=1)
        assert float(np.std(row_norms)) > 1e-3
        gram = projection @ projection.T
        off_diagonal = gram - np.diag(np.diag(gram))
        assert float(np.max(np.abs(off_diagonal))) > 1.0

    def test_sketch_dim_is_exposed_and_matches_the_projection(self):
        quantizer = build_product_quantizer(64, 3, sketch_dim=64)
        assert quantizer.sketch_dim == 64
        assert np.asarray(quantizer.projection).shape == (64, 64)
