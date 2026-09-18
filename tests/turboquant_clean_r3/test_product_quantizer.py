"""Tests for Task 4: Algorithm 2 Product Estimator and Bit Packing."""

from __future__ import annotations

import math
import numpy as np
import pytest

from hamutay.turboquant import (
    pack_signs,
    unpack_signs,
    ProductCodes,
    ProductQuantizer,
    MSEQuantizer,
    lloyd_max_codebook,
    gaussian_rotation,
)


def test_pack_signs_rejects_non_boolean_dtypes() -> None:
    """Verify pack_signs rejects any array whose dtype is not bool."""
    for invalid_dtype in [np.uint8, np.int32, np.float32]:
        arr = np.ones((16,), dtype=invalid_dtype)
        with pytest.raises((TypeError, ValueError)):
            pack_signs(arr)


def test_pack_unpack_signs_little_endian_roundtrip() -> None:
    """Verify pack_signs uses little-endian byte bit-packing and unpacks to FP32 in {-1, +1}."""
    # Test specific coordinate: bit 0 of byte 0, bit 1 of byte 0, bit 0 of byte 1
    signs = np.zeros((16,), dtype=bool)
    signs[0] = True   # Byte 0, bit 0 -> 0x01
    signs[3] = True   # Byte 0, bit 3 -> 0x08 -> Byte 0 = 0x09
    signs[9] = True   # Byte 1, bit 1 -> 0x02 -> Byte 1 = 0x02

    packed = pack_signs(signs)
    assert packed.dtype == np.uint8
    assert packed.shape == (2,)
    assert packed[0] == 0x09
    assert packed[1] == 0x02

    unpacked = unpack_signs(packed, 16)
    assert unpacked.dtype == np.float32
    assert unpacked.shape == (16,)
    assert unpacked[0] == 1.0
    assert unpacked[1] == -1.0
    assert unpacked[3] == 1.0
    assert unpacked[9] == 1.0
    assert unpacked[10] == -1.0


def test_zero_vector_packed_signs_contract() -> None:
    """Verify zero projected values map to +1, setting all in-range bits in packed signs."""
    # For sketch_dim = 128, all 128 coordinates are 0 -> mapped to +1 -> 16 bytes of 0xFF
    d = 128
    signs = np.ones((d,), dtype=bool)  # All True (+1)
    packed = pack_signs(signs)
    assert packed.shape == (16,)
    assert np.all(packed == 0xFF)

    # For sketch_dim not a multiple of 8, e.g. 10
    # Byte 0: 8 bits set (0xFF); Byte 1: bits 0,1 set (0x03), unused bits 2..7 cleared (0)
    signs_10 = np.ones((10,), dtype=bool)
    packed_10 = pack_signs(signs_10)
    assert packed_10[0] == 0xFF
    assert packed_10[1] == 0x03


def test_product_codes_dataclass_contract() -> None:
    """Verify ProductCodes is slotted, frozen, and validates structure."""
    d = 128
    rot = gaussian_rotation(d, "rot")
    cb = lloyd_max_codebook(d, 1)
    mse_q = MSEQuantizer(rot, cb)
    mse_codes = mse_q.quantize(np.zeros((2, d), dtype=np.float32))

    packed = np.full((2, 16), 0xFF, dtype=np.uint8)
    res_norms = np.zeros((2,), dtype=np.float32)

    pc = ProductCodes(mse=mse_codes, packed_signs=packed, residual_norms=res_norms)
    assert hasattr(ProductCodes, "__slots__")

    with pytest.raises((AttributeError, TypeError)):
        pc.packed_signs = np.zeros_like(packed)  # Frozen


def test_product_quantizer_reconstruction_and_zero_vector() -> None:
    """Verify ProductQuantizer zero-vector contract and general reconstruction properties."""
    d = 128
    rot = gaussian_rotation(d, "rot_prod")
    # Total bits = 2 implies 1-bit MSE codebook + 1-bit QJL sketch
    cb = lloyd_max_codebook(d, 1)
    mse_q = MSEQuantizer(rot, cb)

    proj = np.random.randn(d, d).astype(np.float32)
    prod_q = ProductQuantizer(mse_quantizer=mse_q, projection=proj)

    zero_vec = np.zeros((4, d), dtype=np.float32)
    codes = prod_q.quantize(zero_vec)

    # Zero vector properties
    assert np.all(codes.residual_norms == 0.0)
    assert np.all(codes.mse.norms == 0.0)
    assert np.all(codes.mse.indices == 0)
    # Packed signs have all in-range bits set (+1 convention for zero)
    assert np.all(codes.packed_signs == 0xFF)

    recon = prod_q.dequantize(codes)
    assert np.array_equal(recon, np.zeros_like(zero_vec))


def test_estimate_inner_products_shape_rejection_no_broadcast() -> None:
    """Verify estimate_inner_products enforces paired leading shapes and rejects broadcasting."""
    d = 128
    rot = gaussian_rotation(d, "rot_shape")
    cb = lloyd_max_codebook(d, 1)
    mse_q = MSEQuantizer(rot, cb)
    proj = np.random.randn(d, d).astype(np.float32)
    prod_q = ProductQuantizer(mse_quantizer=mse_q, projection=proj)

    vecs = np.random.randn(8, d).astype(np.float32)
    codes = prod_q.quantize(vecs)

    # Matching leading shape: queries (8, 128), codes (8,)
    valid_queries = np.random.randn(8, d).astype(np.float32)
    est = prod_q.estimate_inner_products(valid_queries, codes)
    assert est.shape == (8,)

    # Mismatched leading shapes must be rejected
    mismatched_queries = [
        np.random.randn(4, d).astype(np.float32),   # Batch size 4 vs 8
        np.random.randn(1, d).astype(np.float32),   # Broadcast attempt (1, d)
        np.random.randn(8, 2, d).astype(np.float32),# Extra dimension
    ]
    for q in mismatched_queries:
        with pytest.raises((ValueError, TypeError)):
            prod_q.estimate_inner_products(q, codes)


def test_estimate_inner_products_against_analytic_oracle() -> None:
    """Verify estimate_inner_products computes exact mathematical formula for MSE + QJL."""
    d = 128
    rot = gaussian_rotation(d, "rot_ip")
    cb = lloyd_max_codebook(d, 1)
    mse_q = MSEQuantizer(rot, cb)
    proj = np.random.randn(d, d).astype(np.float32)
    prod_q = ProductQuantizer(mse_quantizer=mse_q, projection=proj)

    vecs = np.random.randn(5, d).astype(np.float32)
    queries = np.random.randn(5, d).astype(np.float32)
    codes = prod_q.quantize(vecs)

    observed_ip = prod_q.estimate_inner_products(queries, codes)

    # Independent oracle calculation:
    # estimate(q, x) = dot(q, x_hat_mse) + sqrt(pi/2)/d * residual_norm * dot(q, S^T z)
    recon_mse = mse_q.dequantize(codes.mse)
    term1 = np.sum(queries * recon_mse, axis=-1)

    unpacked_signs = unpack_signs(codes.packed_signs, d)
    # residual reconstruction component = S^T z
    qjl_recon = unpacked_signs @ proj  # since proj stored as rows
    term2 = (
        math.sqrt(math.pi / 2.0)
        / float(d)
        * codes.residual_norms
        * np.sum(queries * qjl_recon, axis=-1)
    )

    expected_ip = term1 + term2
    assert np.allclose(observed_ip, expected_ip, rtol=1e-5, atol=1e-5)
