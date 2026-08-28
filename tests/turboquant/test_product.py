from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from hamutay.turboquant.codebook import lloyd_max_codebook
from hamutay.turboquant.mse import MSEQuantizer
from hamutay.turboquant.product import (
    ProductCodes,
    ProductQuantizer,
    pack_signs,
    unpack_signs,
)


def product_quantizer(total_bits: int = 2) -> ProductQuantizer:
    mse_bits = total_bits - 1
    mse = MSEQuantizer(np.eye(4, dtype=np.float32), lloyd_max_codebook(4, mse_bits))
    projection = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        dtype=np.float32,
    )
    return ProductQuantizer(mse, projection)


def test_pack_signs_is_little_endian_and_zero_is_positive():
    raw = np.array([[1.0, -1.0, 0.0, 2.0, -2.0, -3.0, 4.0, 5.0, -1.0]])
    packed = pack_signs(raw >= 0)
    np.testing.assert_array_equal(packed, [[0b11001101, 0]])
    unpacked = unpack_signs(packed, 9)
    np.testing.assert_array_equal(unpacked, np.where(raw >= 0, 1.0, -1.0))
    assert packed.dtype == np.uint8
    assert unpacked.dtype == np.float32


def test_pack_signs_preserves_leading_shapes_and_owns_output():
    signs = np.array(
        [
            [[True, False, True, False, True]],
            [[False, True, False, True, False]],
        ]
    )

    packed = pack_signs(signs)
    unpacked = unpack_signs(packed, 5)

    assert packed.shape == (2, 1, 1)
    assert unpacked.shape == signs.shape
    assert packed.flags.c_contiguous and packed.flags.owndata
    assert unpacked.flags.c_contiguous and unpacked.flags.owndata
    np.testing.assert_array_equal(unpacked, np.where(signs, 1.0, -1.0))


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: pack_signs(np.array([1, 0], dtype=np.uint8)), "boolean"),
        (lambda: pack_signs(np.array(True)), "dimension"),
        (lambda: pack_signs(np.empty((2, 0), dtype=np.bool_)), "positive"),
        (
            lambda: unpack_signs(np.array([1], dtype=np.int16), 8),
            "uint8",
        ),
        (lambda: unpack_signs(np.array(1, dtype=np.uint8), 8), "dimension"),
        (lambda: unpack_signs(np.array([1], dtype=np.uint8), 0), "positive"),
        (lambda: unpack_signs(np.array([1], dtype=np.uint8), 9), "length"),
    ],
)
def test_pack_helpers_reject_ambiguous_inputs(call, message):
    with pytest.raises(ValueError, match=message):
        call()


def test_product_quantizer_matches_literal_formula():
    q = product_quantizer()
    keys = np.array([[0.9, -0.2, 0.3, -0.1]], np.float32)
    queries = np.array([[0.2, 0.4, -0.5, 0.7]], np.float32)
    codes = q.quantize(keys)
    mse_hat = q.mse_quantizer.dequantize(codes.mse)
    residual = keys - mse_hat
    signs = np.where(residual @ q.projection.T >= 0, 1.0, -1.0)
    literal = np.sum(queries * mse_hat, axis=-1) + np.sqrt(
        np.pi / 2.0
    ) / q.sketch_dim * codes.residual_norms * np.sum(
        (queries @ q.projection.T) * signs, axis=-1
    )
    np.testing.assert_allclose(
        q.estimate_inner_products(queries, codes), literal, atol=2e-7
    )


def test_rectangular_projection_matches_hand_computed_paired_formula():
    projection = np.array(
        [
            [1, 2, 0, -1],
            [-2, 0, 1, 1],
            [0, -1, 3, 0],
            [1, 0, -2, 2],
            [-1, 1, 0, 1],
        ],
        dtype=np.float32,
    )
    q = ProductQuantizer(
        MSEQuantizer(np.eye(4, dtype=np.float32), lloyd_max_codebook(4, 0)),
        projection,
    )
    keys = np.array(
        [
            [[1, 0, 0, 0], [0, 1, 0, 0]],
            [[0, 0, 1, 0], [0, 0, 0, 2]],
        ],
        dtype=np.float32,
    )
    queries = np.array(
        [
            [[1, 2, 3, 4], [-1, 0, 2, 1]],
            [[0.5, -1, 0, 2], [1, -2, 0.5, 0]],
        ],
        dtype=np.float32,
    )

    codes = q.quantize(keys)

    # Hand-derived sign rows are + - + + -, + + - + +,
    # + + + - +, and - + + + +. Their products with the projection are
    # [5, 0, 0, -1], [-1, 4, -4, 3], [-3, 2, 6, -1], and [-3, -2, 2, 5].
    coefficient = np.float32(np.sqrt(np.pi / 2.0) / 5.0)
    expected_reconstruction = coefficient * np.array(
        [
            [[5, 0, 0, -1], [-1, 4, -4, 3]],
            [[-3, 2, 6, -1], [-6, -4, 4, 10]],
        ],
        dtype=np.float32,
    )
    expected_estimates = coefficient * np.array([[1, -4], [-5.5, 4]], dtype=np.float32)

    assert q.sketch_dim == 5
    np.testing.assert_array_equal(
        codes.packed_signs,
        np.array([[[13], [27]], [[23], [30]]], dtype=np.uint8),
    )
    np.testing.assert_array_equal(codes.residual_norms, [[1, 1], [1, 2]])
    np.testing.assert_allclose(q.dequantize(codes), expected_reconstruction)
    np.testing.assert_allclose(
        q.estimate_inner_products(queries, codes), expected_estimates
    )


def test_estimator_sketches_the_original_query_not_an_mse_reconstruction():
    q = product_quantizer(total_bits=1)
    keys = np.array([[2.0, -1.0, 0.5, -0.25]], dtype=np.float32)
    queries = np.array([[0.3, -0.7, 1.1, -1.9]], dtype=np.float32)
    codes = q.quantize(keys)

    expected = (
        np.float32(np.sqrt(np.pi / 2.0) / 4.0)
        * np.linalg.norm(keys, axis=-1)
        * np.sum(np.abs(queries), axis=-1)
    )

    np.testing.assert_allclose(q.estimate_inner_products(queries, codes), expected)


def test_product_round_trip_is_repeatable_and_zero_safe():
    q = product_quantizer()
    vectors = np.array([[0, 0, 0, 0], [1, 2, 3, 4]], np.float32)
    first = q.quantize(vectors)
    second = q.quantize(vectors)
    assert np.array_equal(first.packed_signs, second.packed_signs)
    assert np.array_equal(first.residual_norms, second.residual_norms)
    assert np.array_equal(q.dequantize(first), q.dequantize(second))
    assert np.array_equal(q.dequantize(first)[0], np.zeros(4, np.float32))
    np.testing.assert_array_equal(first.packed_signs[0], [0b00001111])
    np.testing.assert_array_equal(
        q.estimate_inner_products(np.ones_like(vectors), first)[0],
        np.array(0.0, dtype=np.float32),
    )


def test_residual_norm_uses_original_scale_and_restores_it():
    q = product_quantizer(total_bits=1)
    vectors = np.array([[3.0, 4.0, 0.0, 0.0]], dtype=np.float32)

    codes = q.quantize(vectors)
    reconstructed = q.dequantize(codes)

    np.testing.assert_array_equal(codes.residual_norms, [5.0])
    expected = np.float32(np.sqrt(np.pi / 2.0) / 4.0) * 5.0
    np.testing.assert_allclose(
        reconstructed, [[expected, expected, expected, expected]]
    )


def test_representable_large_residual_norm_stays_finite_fp32():
    q = product_quantizer(total_bits=1)

    codes = q.quantize(np.array([[3e38, 0.0, 0.0, 0.0]], dtype=np.float32))

    assert codes.residual_norms.dtype == np.float32
    assert np.isfinite(codes.residual_norms).all()
    np.testing.assert_allclose(codes.residual_norms, [3e38])
    assert np.isfinite(q.dequantize(codes)).all()


def test_single_vector_preserves_scalar_norm_and_scalar_estimate_shapes():
    q = product_quantizer()
    vector = np.array([1.0, -2.0, 3.0, -4.0], dtype=np.float32)
    query = np.array([0.25, 0.5, -0.75, 1.0], dtype=np.float32)

    codes = q.quantize(vector)
    estimate = q.estimate_inner_products(query, codes)

    assert codes.packed_signs.shape == (1,)
    assert codes.residual_norms.shape == ()
    assert q.dequantize(codes).shape == (4,)
    assert estimate.shape == ()
    assert estimate.dtype == np.float32


def test_constructor_copies_and_freezes_projection():
    mse = MSEQuantizer(np.eye(4, dtype=np.float32), lloyd_max_codebook(4, 1))
    projection = np.eye(4, dtype=np.float64)

    q = ProductQuantizer(mse, projection)
    projection[0, 0] = 7.0

    assert q.mse_quantizer is mse
    assert q.projection.dtype == np.float32
    assert q.projection.flags.c_contiguous and q.projection.flags.owndata
    assert not q.projection.flags.writeable
    np.testing.assert_array_equal(q.projection, np.eye(4, dtype=np.float32))


@pytest.mark.parametrize(
    ("projection", "message"),
    [
        (np.zeros((0, 4), dtype=np.float32), "positive"),
        (np.zeros((4, 3), dtype=np.float32), "final dimension"),
        (np.zeros(4, dtype=np.float32), "two-dimensional"),
        (np.zeros((4, 4), dtype=np.int32), "floating-point"),
        (np.full((4, 4), np.nan, dtype=np.float32), "finite"),
    ],
)
def test_constructor_rejects_invalid_projection(projection, message):
    mse = MSEQuantizer(np.eye(4, dtype=np.float32), lloyd_max_codebook(4, 1))
    with pytest.raises(ValueError, match=message):
        ProductQuantizer(mse, projection)


def test_product_codes_are_frozen_and_quantize_outputs_are_independent():
    q = product_quantizer()
    vectors = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)

    codes = q.quantize(vectors)
    vectors[:] = 0.0

    with pytest.raises(FrozenInstanceError):
        codes.residual_norms = np.zeros(1, dtype=np.float32)
    assert codes.packed_signs.flags.c_contiguous and codes.packed_signs.flags.owndata
    assert (
        codes.residual_norms.flags.c_contiguous and codes.residual_norms.flags.owndata
    )
    assert codes.mse.indices.flags.owndata
    assert codes.mse.norms.flags.owndata
    assert codes.residual_norms[0] > 0.0


def test_product_methods_reject_mismatched_leading_shapes_and_malformed_codes():
    q = product_quantizer()
    codes = q.quantize(np.ones((2, 4), dtype=np.float32))

    with pytest.raises(ValueError, match="leading shape"):
        q.estimate_inner_products(np.ones((1, 4), dtype=np.float32), codes)
    with pytest.raises(ValueError, match="final dimension"):
        q.estimate_inner_products(np.ones((2, 3), dtype=np.float32), codes)
    with pytest.raises(ValueError, match="floating-point"):
        q.estimate_inner_products(np.ones((2, 4), dtype=np.int32), codes)
    with pytest.raises(ValueError, match="finite"):
        q.estimate_inner_products(np.full((2, 4), np.nan, dtype=np.float32), codes)

    with pytest.raises(ValueError, match="ProductCodes"):
        q.dequantize(codes.mse)
    with pytest.raises(ValueError, match="packed_signs"):
        q.dequantize(
            ProductCodes(
                mse=codes.mse,
                packed_signs=np.zeros((2, 2), dtype=np.uint8),
                residual_norms=codes.residual_norms,
            )
        )
    with pytest.raises(ValueError, match="residual_norms"):
        q.dequantize(
            ProductCodes(
                mse=codes.mse,
                packed_signs=codes.packed_signs,
                residual_norms=np.zeros((2, 1), dtype=np.float32),
            )
        )


@pytest.mark.parametrize("bad_norm", [np.nan, np.inf, -np.inf, -1.0])
def test_product_methods_reject_nonfinite_or_negative_residual_norms(bad_norm):
    q = product_quantizer()
    codes = q.quantize(np.ones(4, dtype=np.float32))
    malformed = ProductCodes(
        mse=codes.mse,
        packed_signs=codes.packed_signs,
        residual_norms=np.array(bad_norm, dtype=np.float32),
    )

    with pytest.raises(ValueError, match="residual_norms"):
        q.dequantize(malformed)
    with pytest.raises(ValueError, match="residual_norms"):
        q.estimate_inner_products(np.ones(4, dtype=np.float32), malformed)


def test_product_methods_reject_residual_norm_for_zero_original_norm():
    q = product_quantizer()
    zero = q.quantize(np.zeros(4, dtype=np.float32))
    impossible = ProductCodes(
        mse=zero.mse,
        packed_signs=zero.packed_signs,
        residual_norms=np.array(1.0, dtype=np.float32),
    )

    with pytest.raises(ValueError, match="zero original norm"):
        q.dequantize(impossible)
    with pytest.raises(ValueError, match="zero original norm"):
        q.estimate_inner_products(np.ones(4, dtype=np.float32), impossible)


def test_dequantize_returns_an_owning_fp32_copy():
    q = product_quantizer()
    result = q.dequantize(q.quantize(np.ones((2, 4), dtype=np.float32)))

    assert result.dtype == np.float32
    assert result.flags.c_contiguous and result.flags.owndata
