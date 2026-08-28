import numpy as np
import pytest

from hamutay.turboquant.codebook import lloyd_max_codebook
from hamutay.turboquant.mse import MSECodes, MSEQuantizer


def quantizer(bits: int) -> MSEQuantizer:
    return MSEQuantizer(np.eye(4, dtype=np.float32), lloyd_max_codebook(4, bits))


def test_mse_quantizer_preserves_shape_and_norm_scale():
    vectors = np.array([[3.0, 0.0, 4.0, 0.0], [1.0, -2.0, 3.0, -4.0]], np.float32)
    codes = quantizer(3).quantize(vectors)
    reconstructed = quantizer(3).dequantize(codes)
    assert codes.indices.shape == vectors.shape
    np.testing.assert_allclose(codes.norms, np.linalg.norm(vectors, axis=-1))
    assert reconstructed.shape == vectors.shape
    assert reconstructed.dtype == np.float32


def test_zero_vector_round_trips_exactly():
    q = quantizer(2)
    codes = q.quantize(np.zeros((2, 4), np.float32))
    assert np.all(codes.indices == 0)
    assert np.array_equal(q.dequantize(codes), np.zeros((2, 4), np.float32))


def test_single_vector_uses_scalar_norm_and_round_trips_shape():
    q = quantizer(2)
    vectors = np.array([3.0, 0.0, 4.0, 0.0], dtype=np.float32)

    codes = q.quantize(vectors)

    assert codes.indices.shape == (4,)
    assert codes.norms.shape == ()
    assert q.dequantize(codes).shape == (4,)


def test_quantization_uses_row_vector_rotation_and_its_inverse():
    rotation = np.array([[0.0, -1.0], [1.0, 0.0]], dtype=np.float32)
    q = MSEQuantizer(rotation, np.array([-1.0, 0.0, 1.0], dtype=np.float32))

    codes = q.quantize(np.array([1.0, 0.0], dtype=np.float32))

    np.testing.assert_array_equal(codes.indices, [1, 2])
    np.testing.assert_array_equal(q.dequantize(codes), [1.0, 0.0])


def test_codes_and_reconstruction_are_bit_repeatable():
    q = quantizer(4)
    vectors = np.arange(32, dtype=np.float32).reshape(8, 4) - 15.5
    a = q.quantize(vectors)
    b = q.quantize(vectors.copy())
    assert np.array_equal(a.indices, b.indices)
    assert np.array_equal(a.norms, b.norms)
    assert np.array_equal(q.dequantize(a), q.dequantize(b))


def test_constructor_rejects_nonorthogonal_rotation():
    bad = np.ones((4, 4), np.float32)
    with pytest.raises(ValueError, match="orthogonal"):
        MSEQuantizer(bad, lloyd_max_codebook(4, 2))


def test_constructor_freezes_own_read_only_fp32_arrays():
    rotation = np.eye(4, dtype=np.float64)
    codebook = np.array([-1.0, 1.0], dtype=np.float64)
    q = MSEQuantizer(rotation, codebook)

    rotation[0, 0] = 2.0
    codebook[0] = -2.0

    assert q.rotation.dtype == np.float32
    assert q.codebook.dtype == np.float32
    assert q.rotation.flags.c_contiguous and q.rotation.flags.owndata
    assert q.codebook.flags.c_contiguous and q.codebook.flags.owndata
    assert not q.rotation.flags.writeable
    assert not q.codebook.flags.writeable
    np.testing.assert_array_equal(q.rotation, np.eye(4, dtype=np.float32))
    np.testing.assert_array_equal(q.codebook, [-1.0, 1.0])


def test_quantize_and_dequantize_reject_bad_shapes_and_codes():
    q = quantizer(2)
    with pytest.raises(ValueError, match="final dimension"):
        q.quantize(np.zeros((3, 5), np.float32))
    with pytest.raises(ValueError, match="floating-point"):
        q.quantize(np.zeros((3, 4), np.int32))
    with pytest.raises(ValueError, match="indices"):
        q.dequantize(
            MSECodes(
                indices=np.zeros((2, 3), dtype=np.uint8),
                norms=np.zeros(2, dtype=np.float32),
            )
        )
    with pytest.raises(ValueError, match="indices"):
        q.dequantize(
            MSECodes(
                indices=np.full((2, 4), 255, dtype=np.uint8),
                norms=np.zeros(2, dtype=np.float32),
            )
        )
    with pytest.raises(ValueError, match="norms"):
        q.dequantize(
            MSECodes(
                indices=np.zeros((2, 4), dtype=np.uint8),
                norms=np.zeros((2, 1), dtype=np.float32),
            )
        )
