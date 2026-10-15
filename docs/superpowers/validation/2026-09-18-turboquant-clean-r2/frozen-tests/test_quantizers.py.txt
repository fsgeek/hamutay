import numpy as np
import pytest

from hamutay.turboquant.mse import MSECodes, MSEQuantizer
from hamutay.turboquant.product import ProductCodes, ProductQuantizer, pack_signs, unpack_signs

def test_mse_codes_structure():
    idx = np.zeros((2, 128), dtype=np.uint8)
    norms = np.ones(2, dtype=np.float32)
    codes = MSECodes(indices=idx, norms=norms)
    assert codes.indices is idx
    assert codes.norms is norms

def test_mse_quantizer_zero_vector_convention():
    dim = 4
    rotation = np.eye(dim, dtype=np.float32)
    cb = np.array([-0.5, 0.5], dtype=np.float32)
    mq = MSEQuantizer(rotation=rotation, codebook=cb)
    
    vecs = np.array([
        [0.0, 0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0, 0.0]
    ], dtype=np.float32)
    
    codes = mq.quantize(vecs)
    # Zero vector: norm 0.0, all-zero indices
    assert codes.norms[0] == 0.0
    np.testing.assert_array_equal(codes.indices[0], [0, 0, 0, 0])
    
    deq = mq.dequantize(codes)
    # Exact zero reconstruction
    np.testing.assert_array_equal(deq[0], [0.0, 0.0, 0.0, 0.0])

def test_pack_unpack_signs():
    # True = +1 (set), False = -1 (clear)
    signs = np.array([True, False, True, True, False, False, True, False, True, True], dtype=bool)
    packed = pack_signs(signs)
    
    assert packed.dtype == np.uint8
    assert len(packed) == 2
    # byte 0: bits 0..7 -> 1, 0, 1, 1, 0, 0, 1, 0 -> 0b01001101 = 77
    # byte 1: bits 8..9 -> 1, 1 -> 0b00000011 = 3
    assert packed[0] == 77
    assert packed[1] == 3
    
    unpacked = unpack_signs(packed, sketch_dim=10)
    assert unpacked.dtype == np.float32
    expected = np.array([1, -1, 1, 1, -1, -1, 1, -1, 1, 1], dtype=np.float32)
    np.testing.assert_array_equal(unpacked, expected)

def test_product_quantizer_conventions():
    dim = 4
    rotation = np.eye(dim, dtype=np.float32)
    cb = np.array([-0.5, 0.5], dtype=np.float32)
    mq = MSEQuantizer(rotation=rotation, codebook=cb)
    projection = np.eye(dim, dtype=np.float32)
    
    pq = ProductQuantizer(mse_quantizer=mq, projection=projection)
    
    vecs = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
    codes = pq.quantize(vecs)
    
    # Zero vector zero norm check
    assert codes.residual_norms[0] == 0.0
    # Zero vector packed signs have all in-range bits SET
    # For dim 4, in-range bits are 4 -> 0b00001111 = 15
    assert codes.packed_signs[0, 0] == 15
    
    queries = np.array([[1.0, 1.0, 1.0, 1.0]], dtype=np.float32)
    est = pq.estimate_inner_products(queries, codes)
    assert est[0] == 0.0
    
    bad_queries = np.array([[1.0, 2.0]], dtype=np.float32)
    with pytest.raises(Exception):
        pq.estimate_inner_products(bad_queries, codes)
