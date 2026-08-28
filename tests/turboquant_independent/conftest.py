"""Shared helpers for the independent black-box TurboQuant validation suite.

This suite was authored against the approved design specification, the
qualification plan's declared public interfaces, arXiv 2504.19874 v1, and the
pinned author-QJL contract, without reading the implementation under review.

Design intent: every assertion here is derived from the specification or from
the paper's mathematics, and is checked against an independently written
oracle inside the test rather than against a restatement of the plan's prose.
"""

from __future__ import annotations

import numpy as np

# Registered study constants, quoted from the design specification.
STUDY_SEED_HEX = "0b311d5d4eceaf773efde389305a1b5a"
MODEL_REVISION = "0e9e39f249a16976918f6564b8830bc894c89659"
REGISTERED_DIMENSION = 128

# Paper Table values (arXiv 2504.19874 v1).
PAPER_MSE_DISTORTION = {1: 0.36, 2: 0.117, 3: 0.03, 4: 0.009}
PAPER_PROD_DISTORTION_NUMERATOR = {1: 1.57, 2: 0.56, 3: 0.18, 4: 0.047}

# Registered analytic FP64 quadrature values for the dimension-128 codebooks.
# Reproduced independently by this validator before the suite was frozen.
ANALYTIC_MSE_DISTORTION = {
    1: 0.3608885936869029,
    2: 0.1160000702751112,
    3: 0.0339659257939010,
    4: 0.0093147879537958,
}


def reference_sphere_density(x, dimension: int):
    """Independent implementation of the paper's Lemma 1 coordinate density.

    f(x) = Gamma(d/2) / (sqrt(pi) Gamma((d-1)/2)) * (1 - x^2)^((d-3)/2)
    """
    from scipy.special import gammaln

    x = np.asarray(x, dtype=np.float64)
    log_norm = (
        gammaln(dimension / 2.0)
        - 0.5 * np.log(np.pi)
        - gammaln((dimension - 1) / 2.0)
    )
    inside = np.abs(x) < 1.0
    out = np.zeros_like(x, dtype=np.float64)
    safe = np.where(inside, x, 0.0)
    out[inside] = np.exp(
        log_norm + ((dimension - 3) / 2.0) * np.log1p(-safe[inside] ** 2)
    )
    return out if out.ndim else float(out)


def reference_cell_boundaries(codebook: np.ndarray) -> np.ndarray:
    """Midpoint decision boundaries implied by a sorted codebook."""
    centroids = np.asarray(codebook, dtype=np.float64)
    midpoints = (centroids[:-1] + centroids[1:]) / 2.0
    return np.concatenate(([-1.0], midpoints, [1.0]))


def reference_analytic_distortion(codebook: np.ndarray, dimension: int) -> float:
    """Independent FP64 quadrature of normalized distortion for a codebook.

    Integrates (x - c_i)^2 f(x) over each Lloyd-Max cell and scales by the
    dimension, matching the spec's "exact normalized scalar distortion".
    """
    from scipy.integrate import quad

    centroids = np.asarray(codebook, dtype=np.float64)
    boundaries = reference_cell_boundaries(centroids)
    total = 0.0
    for index, centroid in enumerate(centroids):
        value, _ = quad(
            lambda x, c=centroid: (x - c) ** 2
            * reference_sphere_density(np.float64(x), dimension),
            boundaries[index],
            boundaries[index + 1],
            epsabs=1e-14,
            epsrel=1e-13,
            limit=200,
        )
        total += value
    return total * dimension


def reference_derive_seed(*fields, study_seed_hex: str = STUDY_SEED_HEX) -> int:
    """Independent implementation of the spec's sub-seed wire format.

    "the first 16 bytes, interpreted as an unsigned big-endian integer, of
    SHA-256 over the UTF-8 string formed by joining the study seed, ... with
    `|`".  Integer fields use unpadded base-10 ASCII.
    """
    import hashlib

    wire = "|".join((study_seed_hex, *(str(field) for field in fields)))
    return int.from_bytes(hashlib.sha256(wire.encode("utf-8")).digest()[:16], "big")


def reference_pack_signs(boolean_signs: np.ndarray) -> np.ndarray:
    """Little-endian bit packing: coordinate j -> bit (j % 8) of byte (j // 8)."""
    flags = np.asarray(boolean_signs, dtype=bool)
    sketch_dim = flags.shape[-1]
    byte_count = (sketch_dim + 7) // 8
    lead = flags.shape[:-1]
    packed = np.zeros(lead + (byte_count,), dtype=np.uint8)
    for coordinate in range(sketch_dim):
        bit = np.uint8(1 << (coordinate % 8))
        packed[..., coordinate // 8] |= np.where(
            flags[..., coordinate], bit, np.uint8(0)
        ).astype(np.uint8)
    return packed


def gaussian_pairs(count: int, dimension: int, seed: int):
    """Deterministic independent query/key pairs for statistical assertions."""
    rng = np.random.default_rng(seed)
    queries = rng.standard_normal((count, dimension))
    keys = rng.standard_normal((count, dimension))
    return queries, keys
