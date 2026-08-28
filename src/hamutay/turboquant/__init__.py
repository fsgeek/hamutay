"""Deterministic building blocks for TurboQuant studies."""

from .codebook import (
    lloyd_max_codebook,
    nearest_code_indices,
    sphere_coordinate_density,
)
from .rotation import canonical_qr, gaussian_rotation
from .seeding import STUDY_SEED_HEX, derive_seed, rng_for

__all__ = [
    "STUDY_SEED_HEX",
    "canonical_qr",
    "derive_seed",
    "gaussian_rotation",
    "lloyd_max_codebook",
    "nearest_code_indices",
    "rng_for",
    "sphere_coordinate_density",
]
