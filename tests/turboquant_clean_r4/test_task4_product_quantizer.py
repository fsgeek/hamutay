import numpy as np
import pytest
from hamutay.turboquant.mse import MSEQuantizer, MSECodes
from hamutay.turboquant.product import (
    ProductCodes,
    ProductQuantizer,
    pack_signs,
    unpack_signs
)

def test_product_codes_dataclass():
    mse = MSECodes(indices=np.zeros((2, 128), dtype=np.uint8), norms=np.zeros(2, dtype=np.float32))
    packed = np.zeros((2, 16), dtype=np.uint8)
    res = np.zeros(2, dtype=np.float32)
    codes = ProductCodes(mse=mse, packed_signs=packed, residual_norms=res)
    assert codes.packed_signs.shape == (2, 16)
    assert codes.residual_norms.shape == (2,)

def test_pack_unpack_signs():
    # Little-endian within byte
    signs = np.array([True, False, True, False, False, False, False, False, True], dtype=bool)
    packed = pack_signs(signs)
    assert packed.dtype == np.uint8
    assert packed.shape == (2,)
    assert packed[0] == 5
    assert packed[1] == 1
    
    unpacked = unpack_signs(packed, 9)
    assert unpacked.dtype == np.float32
    expected = np.array([1, -1, 1, -1, -1, -1, -1, -1, 1], dtype=np.float32)
    np.testing.assert_array_equal(unpacked, expected)
    
def test_pack_signs_wrong_dtype_refusal():
    with pytest.raises(Exception):
        pack_signs(np.array([1, 0], dtype=np.int32))

def test_product_quantizer_zero_encoded_signs():
    rot = np.eye(128, dtype=np.float32)
    cb = np.array([-1.0, 1.0], dtype=np.float32)
    mq = MSEQuantizer(rot, cb)
    proj = np.eye(128, dtype=np.float32)
    pq = ProductQuantizer(mq, proj)
    
    vecs = np.zeros((1, 128), dtype=np.float32)
    codes = pq.quantize(vecs)
    
    # Zero vector: packed sign bytes have every in-range bit SET
    np.testing.assert_array_equal(codes.mse.indices, np.zeros((1, 128), dtype=np.uint8))
    np.testing.assert_array_equal(codes.packed_signs, np.full((1, 16), 255, dtype=np.uint8))
    np.testing.assert_array_equal(codes.residual_norms, np.zeros(1, dtype=np.float32))

def test_product_quantizer_zero_encoded_signs_odd_dimension():
    rot = np.eye(128, dtype=np.float32)
    cb = np.array([-1.0, 1.0], dtype=np.float32)
    mq = MSEQuantizer(rot, cb)
    
    proj = np.eye(9, 128, dtype=np.float32)
    pq = ProductQuantizer(mq, proj)
    
    vecs = np.zeros((1, 128), dtype=np.float32)
    codes = pq.quantize(vecs)
    
    assert codes.packed_signs.shape == (1, 2)
    assert codes.packed_signs[0, 0] == 255
    # Final byte unused high bits are zero, 1 in-range bit is SET
    assert codes.packed_signs[0, 1] == 1

def test_estimate_inner_products_shape_validation():
    rot = np.eye(128, dtype=np.float32)
    cb = np.array([-1.0, 1.0], dtype=np.float32)
    mq = MSEQuantizer(rot, cb)
    proj = np.eye(128, dtype=np.float32)
    pq = ProductQuantizer(mq, proj)
    
    vecs = np.random.randn(2, 128).astype(np.float32)
    codes = pq.quantize(vecs)
    
    queries = np.random.randn(2, 128).astype(np.float32)
    ests = pq.estimate_inner_products(queries, codes)
    assert ests.shape == (2,)
    
    # Mismatched leading shapes rejected
    with pytest.raises(Exception):
        pq.estimate_inner_products(np.random.randn(3, 128).astype(np.float32), codes)
