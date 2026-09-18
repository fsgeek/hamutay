import numpy as np
import pytest
from hamutay.turboquant.mse import MSECodes, MSEQuantizer

def test_mse_codes_dataclass():
    idx = np.zeros((2, 128), dtype=np.uint8)
    norms = np.zeros(2, dtype=np.float32)
    codes = MSECodes(indices=idx, norms=norms)
    assert codes.indices.shape == (2, 128)
    assert codes.norms.shape == (2,)

def test_mse_quantizer_zero_vector_properties():
    rot = np.eye(128, dtype=np.float32)
    cb = np.array([-1.0, 1.0], dtype=np.float32)
    q = MSEQuantizer(rot, cb)
    
    vecs = np.zeros((3, 128), dtype=np.float32)
    codes = q.quantize(vecs)
    
    # Requirement: exact zero norm, all-zero indices, zero reconstruction
    np.testing.assert_array_equal(codes.indices, np.zeros((3, 128), dtype=np.uint8))
    np.testing.assert_array_equal(codes.norms, np.zeros(3, dtype=np.float32))
    
    rec = q.dequantize(codes)
    np.testing.assert_array_equal(rec, np.zeros((3, 128), dtype=np.float32))
    
def test_mse_quantizer_normal_vector():
    rot = np.eye(128, dtype=np.float32)
    cb = np.array([-1.0, 1.0], dtype=np.float32)
    q = MSEQuantizer(rot, cb)
    
    vecs = np.random.randn(3, 128).astype(np.float32)
    codes = q.quantize(vecs)
    
    assert codes.indices.dtype == np.uint8
    assert codes.norms.dtype == np.float32
    
    rec = q.dequantize(codes)
    assert rec.shape == (3, 128)
    assert rec.dtype == np.float32
