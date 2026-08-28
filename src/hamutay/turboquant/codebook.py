"""Dimension-specific scalar codebooks for spherical quantization."""

import operator

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import quad
from scipy.special import gammaln
from scipy.stats import beta


def _validated_dimension(dimension: int) -> int:
    try:
        resolved_dimension = operator.index(dimension)
    except TypeError as error:
        raise ValueError("dimension must be an integer at least 2") from error
    if resolved_dimension < 2:
        raise ValueError("dimension must be at least 2")
    return resolved_dimension


def sphere_coordinate_density(
    x: float | NDArray[np.floating], dimension: int
) -> float | NDArray[np.float64]:
    """Return the density of one coordinate of a uniform unit-sphere vector."""
    resolved_dimension = _validated_dimension(dimension)
    values = np.asarray(x, dtype=np.float64)
    result = np.zeros_like(values, dtype=np.float64)
    in_support = (values >= -1.0) & (values <= 1.0)
    log_normalization = (
        gammaln(resolved_dimension / 2.0)
        - 0.5 * np.log(np.pi)
        - gammaln((resolved_dimension - 1.0) / 2.0)
    )
    result[in_support] = np.exp(log_normalization) * np.power(
        1.0 - values[in_support] ** 2,
        (resolved_dimension - 3.0) / 2.0,
    )
    if result.ndim == 0:
        return float(result)
    return result


def _validated_bits(bits: int) -> int:
    try:
        resolved_bits = operator.index(bits)
    except TypeError as error:
        raise ValueError("bits must be an integer in 0..8") from error
    if not 0 <= resolved_bits <= 8:
        raise ValueError("bits must be in 0..8")
    return resolved_bits


def lloyd_max_codebook(
    dimension: int,
    bits: int,
    *,
    tolerance: float = 1e-12,
    max_iterations: int = 10_000,
) -> NDArray[np.float32]:
    """Construct a deterministic Lloyd-Max codebook for a sphere coordinate."""
    resolved_dimension = _validated_dimension(dimension)
    resolved_bits = _validated_bits(bits)
    if tolerance < 0.0:
        raise ValueError("tolerance must be nonnegative")
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive")
    if resolved_bits == 0:
        return np.array([0.0], dtype=np.float32)

    levels = 1 << resolved_bits
    beta_shape = (resolved_dimension - 1.0) / 2.0
    boundaries = 2.0 * beta.ppf(np.linspace(0.0, 1.0, levels + 1), beta_shape, beta_shape) - 1.0
    centroids = (boundaries[:-1] + boundaries[1:]) / 2.0

    def density(value: float) -> float:
        return sphere_coordinate_density(value, resolved_dimension)

    for _ in range(max_iterations):
        updated = np.empty_like(centroids)
        for index, (lower, upper) in enumerate(zip(boundaries[:-1], boundaries[1:])):
            mass, _ = quad(density, lower, upper, epsabs=1e-14, epsrel=1e-13, limit=200)
            moment, _ = quad(
                lambda value: value * density(value),
                lower,
                upper,
                epsabs=1e-14,
                epsrel=1e-13,
                limit=200,
            )
            updated[index] = moment / mass if mass > 0.0 else centroids[index]

        updated = (updated - updated[::-1]) / 2.0
        movement = np.max(np.abs(updated - centroids))
        centroids = updated
        if movement <= tolerance:
            return np.ascontiguousarray(centroids, dtype=np.float32)
        boundaries[1:-1] = (centroids[:-1] + centroids[1:]) / 2.0

    raise RuntimeError("Lloyd-Max codebook did not converge")


def nearest_code_indices(
    values: NDArray[np.float32], codebook: NDArray[np.float32]
) -> NDArray[np.uint8]:
    """Return nearest-centroid indices, resolving midpoint ties downward."""
    resolved_codebook = np.asarray(codebook)
    if (
        resolved_codebook.ndim != 1
        or resolved_codebook.size == 0
        or not np.all(np.diff(resolved_codebook) > 0)
    ):
        raise ValueError("codebook must be one-dimensional and strictly increasing")
    if resolved_codebook.size > np.iinfo(np.uint8).max + 1:
        raise ValueError("codebook may contain at most 256 centroids")
    boundaries = (resolved_codebook[:-1] + resolved_codebook[1:]) / 2.0
    return np.ascontiguousarray(
        np.searchsorted(boundaries, np.asarray(values), side="left"), dtype=np.uint8
    )
