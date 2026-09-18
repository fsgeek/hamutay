import pytest
import numpy as np
from hamutay.turboquant.rotation import gaussian_rotation
from hamutay.turboquant.codebook import lloyd_max_codebook
from hamutay.turboquant.mse import MSEQuantizer
from hamutay.turboquant.product import ProductQuantizer

def test_zero_vector_behavior():
    dimension = 128
    bits = 1
    rotation = gaussian_rotation(dimension, "test_rot")
    codebook = lloyd_max_codebook(dimension, bits)
    mse_q = MSEQuantizer(rotation, codebook)
    
    projection = np.random.default_rng(42).standard_normal((128, dimension))
    prod_q = ProductQuantizer(mse_q, projection)
    
    zeros = np.zeros((5, dimension), dtype=np.float32)
    codes = prod_q.quantize(zeros)
    
    np.testing.assert_array_equal(codes.mse.norms, np.zeros(5, dtype=np.float32))
    np.testing.assert_array_equal(codes.mse.indices, np.zeros((5, dimension), dtype=np.uint8))
    np.testing.assert_array_equal(codes.residual_norms, np.zeros(5, dtype=np.float32))
    
    reconstructed = prod_q.dequantize(codes)
    np.testing.assert_array_equal(reconstructed, zeros)
    
    expected_packed = np.full((5, 16), 0xFF, dtype=np.uint8)
    np.testing.assert_array_equal(codes.packed_signs, expected_packed)

def test_estimate_inner_products_shape_mismatch():
    dimension = 128
    rotation = gaussian_rotation(dimension, "test_rot2")
    codebook = lloyd_max_codebook(dimension, 1)
    mse_q = MSEQuantizer(rotation, codebook)
    projection = np.random.default_rng(43).standard_normal((128, dimension))
    prod_q = ProductQuantizer(mse_q, projection)
    
    vectors = np.random.default_rng(44).standard_normal((10, dimension)).astype(np.float32)
    codes = prod_q.quantize(vectors)
    
    queries = np.random.default_rng(45).standard_normal((5, dimension)).astype(np.float32)
    
    with pytest.raises(Exception):
        prod_q.estimate_inner_products(queries, codes)

def test_round_trip_determinism():
    dimension = 128
    rotation = gaussian_rotation(dimension, "det_rot")
    codebook = lloyd_max_codebook(dimension, 2)
    mse_q = MSEQuantizer(rotation, codebook)
    projection = np.random.default_rng(100).standard_normal((128, dimension))
    prod_q = ProductQuantizer(mse_q, projection)
    
    vectors = np.random.default_rng(101).standard_normal((50, dimension)).astype(np.float32)
    
    codes1 = prod_q.quantize(vectors)
    recons1 = prod_q.dequantize(codes1)
    
    codes2 = prod_q.quantize(vectors)
    recons2 = prod_q.dequantize(codes2)
    
    np.testing.assert_array_equal(codes1.mse.indices, codes2.mse.indices)
    np.testing.assert_array_equal(codes1.packed_signs, codes2.packed_signs)
    np.testing.assert_array_equal(codes1.mse.norms, codes2.mse.norms)
    np.testing.assert_array_equal(codes1.residual_norms, codes2.residual_norms)
    np.testing.assert_array_equal(recons1, recons2)
