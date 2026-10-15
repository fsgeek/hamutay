"""Canonical random orthogonal rotations for TurboQuant studies."""

import numpy as np
from numpy.typing import NDArray

from .seeding import rng_for


def canonical_qr(matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return the Q factor with a nonnegative diagonal in the signed R factor."""
    q, r = np.linalg.qr(np.asarray(matrix, dtype=np.float64))
    sign = np.where(np.diag(r) < 0, -1.0, 1.0)
    return q * sign


def gaussian_rotation(
    dimension: int,
    *seed_fields: str | int,
) -> NDArray[np.float32]:
    """Generate a repeatable, canonicalized FP32 Gaussian orthogonal rotation."""
    if dimension <= 0:
        raise ValueError("dimension must be positive")
    matrix = rng_for(*seed_fields).standard_normal((dimension, dimension))
    rotation = canonical_qr(matrix)
    return np.ascontiguousarray(rotation, dtype=np.float32)
