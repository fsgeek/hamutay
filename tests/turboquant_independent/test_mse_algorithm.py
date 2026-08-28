"""Independent tests of Algorithm 1 (TurboQuant_mse) as a black box.

Focus areas: the row-major rotation convention, norm restoration, exact
zero-vector handling, orthogonality validation, and immutability of frozen
inputs. Several tests reimplement the algorithm from the paper's pseudocode
and compare end to end, rather than asserting shapes only.
"""

from __future__ import annotations

import numpy as np
import pytest

from hamutay.turboquant.codebook import lloyd_max_codebook, nearest_code_indices
from hamutay.turboquant.mse import MSEQuantizer
from hamutay.turboquant.rotation import gaussian_rotation

from .conftest import REGISTERED_DIMENSION


def build_quantizer(dimension: int, bits: int, *, identity: bool = False):
    rotation = (
        np.eye(dimension, dtype=np.float32)
        if identity
        else gaussian_rotation(dimension, "algorithm_1", 0, "k", 0, "rotation")
    )
    return MSEQuantizer(rotation, lloyd_max_codebook(dimension, bits))


class TestRepresentation:
    def test_codes_have_the_declared_shapes_and_dtypes(self):
        quantizer = build_quantizer(16, 3)
        vectors = np.random.default_rng(1).standard_normal((5, 16)).astype(np.float32)
        codes = quantizer.quantize(vectors)

        assert codes.indices.dtype == np.uint8
        assert codes.indices.shape == vectors.shape
        assert codes.norms.dtype == np.float32
        assert codes.norms.shape == vectors.shape[:-1]

    def test_stored_norms_are_the_input_norms(self):
        quantizer = build_quantizer(16, 3)
        vectors = np.random.default_rng(2).standard_normal((9, 16)).astype(np.float32)
        codes = quantizer.quantize(vectors)
        np.testing.assert_allclose(
            codes.norms, np.linalg.norm(vectors, axis=-1), rtol=1e-6
        )

    def test_codes_dataclass_is_frozen(self):
        quantizer = build_quantizer(8, 2)
        codes = quantizer.quantize(
            np.random.default_rng(3).standard_normal((2, 8)).astype(np.float32)
        )
        with pytest.raises(Exception):
            codes.norms = np.zeros_like(codes.norms)

    def test_multi_dimensional_batches_are_supported(self):
        """KV tensors arrive with (layer, head, token, d)-style leading axes."""
        quantizer = build_quantizer(16, 3)
        vectors = (
            np.random.default_rng(4).standard_normal((2, 3, 4, 16)).astype(np.float32)
        )
        codes = quantizer.quantize(vectors)
        assert codes.indices.shape == (2, 3, 4, 16)
        assert codes.norms.shape == (2, 3, 4)
        assert quantizer.dequantize(codes).shape == vectors.shape


class TestAlgorithmSemantics:
    def test_matches_an_independent_reimplementation_of_algorithm_1(self):
        """Rotate, normalize, scalar-quantize, inverse-rotate, rescale."""
        dimension, bits = REGISTERED_DIMENSION, 3
        quantizer = build_quantizer(dimension, bits)
        rotation = np.asarray(quantizer.rotation, dtype=np.float64)
        codebook = np.asarray(quantizer.codebook, dtype=np.float64)

        rng = np.random.default_rng(7)
        vectors = (rng.standard_normal((24, dimension)) * 3.0).astype(np.float32)

        codes = quantizer.quantize(vectors)
        observed = quantizer.dequantize(codes)

        norms = np.linalg.norm(vectors.astype(np.float64), axis=-1, keepdims=True)
        unit = vectors.astype(np.float64) / norms
        rotated = unit @ rotation.T
        indices = nearest_code_indices(
            rotated.astype(np.float32), quantizer.codebook
        )
        expected = (codebook[indices] @ rotation) * norms

        np.testing.assert_array_equal(codes.indices, indices)
        np.testing.assert_allclose(observed, expected, atol=1e-5, rtol=1e-4)

    def test_rotation_convention_is_row_major(self):
        """y = x @ R.T, not x @ R. With a non-symmetric R these differ, and
        using the wrong one still round-trips, so only a direct check catches it."""
        dimension = 32
        quantizer = build_quantizer(dimension, 4)
        rotation = np.asarray(quantizer.rotation, dtype=np.float64)
        assert not np.allclose(rotation, rotation.T, atol=1e-6)

        rng = np.random.default_rng(8)
        vectors = rng.standard_normal((16, dimension)).astype(np.float32)
        codes = quantizer.quantize(vectors)

        unit = vectors.astype(np.float64) / np.linalg.norm(
            vectors.astype(np.float64), axis=-1, keepdims=True
        )
        correct = nearest_code_indices(
            (unit @ rotation.T).astype(np.float32), quantizer.codebook
        )
        transposed = nearest_code_indices(
            (unit @ rotation).astype(np.float32), quantizer.codebook
        )

        assert not np.array_equal(correct, transposed)
        np.testing.assert_array_equal(codes.indices, correct)

    def test_reconstruction_error_is_scale_invariant(self):
        """Normalization means relative error must not depend on input magnitude."""
        quantizer = build_quantizer(REGISTERED_DIMENSION, 3)
        rng = np.random.default_rng(9)
        base = rng.standard_normal((32, REGISTERED_DIMENSION)).astype(np.float32)

        errors = []
        for scale in (1e-3, 1.0, 1e3):
            scaled = (base * scale).astype(np.float32)
            reconstructed = quantizer.dequantize(quantizer.quantize(scaled))
            relative = np.linalg.norm(
                reconstructed.astype(np.float64) - scaled.astype(np.float64), axis=-1
            ) / np.linalg.norm(scaled.astype(np.float64), axis=-1)
            errors.append(float(np.mean(relative)))

        assert max(errors) - min(errors) < 1e-3

    def test_reconstruction_distortion_tracks_the_paper_scale(self):
        """End-to-end normalized MSE at 128 dimensions, through the real
        rotation, must land near the published 3-bit distortion."""
        quantizer = build_quantizer(REGISTERED_DIMENSION, 3)
        rng = np.random.default_rng(10)
        vectors = rng.standard_normal((4000, REGISTERED_DIMENSION)).astype(np.float32)
        reconstructed = quantizer.dequantize(quantizer.quantize(vectors)).astype(
            np.float64
        )
        exact = vectors.astype(np.float64)
        normalized = np.sum((reconstructed - exact) ** 2, axis=-1) / np.sum(
            exact**2, axis=-1
        )
        observed = float(np.mean(normalized))
        assert abs(observed - 0.03) / 0.03 <= 0.15

    def test_higher_bit_width_reduces_error(self):
        rng = np.random.default_rng(11)
        vectors = rng.standard_normal((256, REGISTERED_DIMENSION)).astype(np.float32)
        previous = None
        for bits in (1, 2, 3, 4):
            quantizer = build_quantizer(REGISTERED_DIMENSION, bits)
            reconstructed = quantizer.dequantize(quantizer.quantize(vectors))
            error = float(
                np.mean(
                    np.linalg.norm(
                        reconstructed.astype(np.float64) - vectors.astype(np.float64),
                        axis=-1,
                    )
                )
            )
            if previous is not None:
                assert error < previous
            previous = error


class TestZeroVectors:
    def test_zero_vector_has_zero_norm_zero_codes_and_exact_zero_output(self):
        quantizer = build_quantizer(REGISTERED_DIMENSION, 3)
        vectors = np.zeros((3, REGISTERED_DIMENSION), dtype=np.float32)
        codes = quantizer.quantize(vectors)

        assert np.all(codes.indices == 0)
        assert np.all(codes.norms == 0.0)
        reconstructed = quantizer.dequantize(codes)
        assert np.array_equal(
            reconstructed, np.zeros((3, REGISTERED_DIMENSION), dtype=np.float32)
        )
        assert np.all(np.isfinite(reconstructed))

    def test_zero_rows_mixed_with_nonzero_rows_stay_exact(self):
        """A naive divide-by-norm produces NaN that propagates through the batch."""
        quantizer = build_quantizer(16, 3)
        vectors = np.array(
            [
                [0.0] * 16,
                [1.0] + [0.0] * 15,
                [0.0] * 16,
                list(np.arange(16, dtype=np.float32) - 7.5),
            ],
            dtype=np.float32,
        )
        codes = quantizer.quantize(vectors)
        reconstructed = quantizer.dequantize(codes)

        assert np.all(np.isfinite(reconstructed))
        np.testing.assert_array_equal(reconstructed[0], np.zeros(16, dtype=np.float32))
        np.testing.assert_array_equal(reconstructed[2], np.zeros(16, dtype=np.float32))
        assert np.linalg.norm(reconstructed[1]) > 0.0
        assert np.linalg.norm(reconstructed[3]) > 0.0
        assert np.all(codes.indices[0] == 0)
        assert np.all(codes.indices[2] == 0)


class TestValidationAndImmutability:
    def test_nonorthogonal_rotation_is_rejected(self):
        with pytest.raises(ValueError, match="orthogonal"):
            MSEQuantizer(np.ones((4, 4), dtype=np.float32), lloyd_max_codebook(4, 2))

    def test_scaled_orthogonal_rotation_is_rejected(self):
        """2*Q preserves direction but doubles norms; it is not a rotation."""
        rotation = 2.0 * gaussian_rotation(8, "algorithm_1", 0, "k", 0, "rotation")
        with pytest.raises(ValueError):
            MSEQuantizer(rotation.astype(np.float32), lloyd_max_codebook(8, 2))

    def test_nonsquare_rotation_is_rejected(self):
        with pytest.raises(ValueError):
            MSEQuantizer(np.zeros((4, 5), dtype=np.float32), lloyd_max_codebook(4, 2))

    def test_unsorted_codebook_is_rejected(self):
        rotation = gaussian_rotation(4, "algorithm_1", 0, "k", 0, "rotation")
        with pytest.raises(ValueError):
            MSEQuantizer(rotation, np.array([0.5, -0.5], dtype=np.float32))

    def test_mismatched_vector_dimension_is_rejected(self):
        quantizer = build_quantizer(8, 2)
        with pytest.raises(ValueError):
            quantizer.quantize(np.zeros((3, 7), dtype=np.float32))

    def test_out_of_range_indices_are_rejected_on_dequantize(self):
        quantizer = build_quantizer(8, 2)
        codes = quantizer.quantize(
            np.random.default_rng(12).standard_normal((2, 8)).astype(np.float32)
        )
        corrupted = type(codes)(
            indices=np.full_like(codes.indices, 200), norms=codes.norms
        )
        with pytest.raises(ValueError):
            quantizer.dequantize(corrupted)

    def test_quantize_does_not_mutate_its_input(self):
        quantizer = build_quantizer(16, 3)
        vectors = (
            np.random.default_rng(13).standard_normal((4, 16)).astype(np.float32)
        )
        original = vectors.copy()
        quantizer.quantize(vectors)
        np.testing.assert_array_equal(vectors, original)

    def test_frozen_rotation_and_codebook_are_not_writable_through_the_quantizer(self):
        """Mutating a shared rotation after construction would silently
        invalidate every artifact hash recorded for the run."""
        rotation = gaussian_rotation(8, "algorithm_1", 0, "k", 0, "rotation")
        codebook = lloyd_max_codebook(8, 2)
        quantizer = MSEQuantizer(rotation, codebook)
        snapshot = np.asarray(quantizer.rotation).copy()

        rotation[0, 0] = 999.0
        codebook[0] = -999.0
        np.testing.assert_array_equal(np.asarray(quantizer.rotation), snapshot)

        with pytest.raises(Exception):
            quantizer.rotation[0, 0] = 1234.0

    def test_repeated_quantization_is_bit_identical(self):
        quantizer = build_quantizer(REGISTERED_DIMENSION, 4)
        vectors = (
            np.random.default_rng(14)
            .standard_normal((64, REGISTERED_DIMENSION))
            .astype(np.float32)
        )
        first = quantizer.quantize(vectors)
        second = quantizer.quantize(vectors.copy())
        np.testing.assert_array_equal(first.indices, second.indices)
        np.testing.assert_array_equal(first.norms, second.norms)
        np.testing.assert_array_equal(
            quantizer.dequantize(first), quantizer.dequantize(second)
        )

    def test_two_quantizers_from_the_same_seed_agree_bitwise(self):
        left = build_quantizer(REGISTERED_DIMENSION, 3)
        right = build_quantizer(REGISTERED_DIMENSION, 3)
        vectors = (
            np.random.default_rng(15)
            .standard_normal((32, REGISTERED_DIMENSION))
            .astype(np.float32)
        )
        np.testing.assert_array_equal(
            left.quantize(vectors).indices, right.quantize(vectors).indices
        )
        np.testing.assert_array_equal(
            left.dequantize(left.quantize(vectors)),
            right.dequantize(right.quantize(vectors)),
        )
