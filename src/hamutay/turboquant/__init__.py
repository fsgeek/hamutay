"""Deterministic building blocks for TurboQuant studies."""

from .codebook import (
    lloyd_max_codebook,
    nearest_code_indices,
    sphere_coordinate_density,
)
from .mse import MSECodes, MSEQuantizer
from .product import ProductCodes, ProductQuantizer, pack_signs, unpack_signs
from .qualification import (
    GateResult,
    QualificationConfig,
    QualificationMetrics,
    QualificationResult,
    analytic_codebook_distortion,
    bootstrap_mean_interval,
    evaluate_algorithm_gates,
    partition_block_ids,
    run_synthetic_qualification,
)
from .rotation import canonical_qr, gaussian_rotation
from .seeding import STUDY_SEED_HEX, derive_seed, rng_for

__all__ = [
    "STUDY_SEED_HEX",
    "MSECodes",
    "MSEQuantizer",
    "ProductCodes",
    "ProductQuantizer",
    "GateResult",
    "QualificationConfig",
    "QualificationMetrics",
    "QualificationResult",
    "analytic_codebook_distortion",
    "bootstrap_mean_interval",
    "canonical_qr",
    "derive_seed",
    "evaluate_algorithm_gates",
    "gaussian_rotation",
    "lloyd_max_codebook",
    "nearest_code_indices",
    "pack_signs",
    "partition_block_ids",
    "rng_for",
    "run_synthetic_qualification",
    "sphere_coordinate_density",
    "unpack_signs",
]
