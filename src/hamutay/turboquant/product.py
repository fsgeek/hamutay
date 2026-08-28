"""Algorithm 2 product estimation and sign-sketch packing."""

from dataclasses import dataclass

import numpy as np

from .mse import MSECodes, MSEQuantizer


@dataclass(frozen=True, slots=True)
class ProductCodes:
    """Algorithm 1 codes plus a packed residual sign sketch and norm."""

    mse: MSECodes
    packed_signs: np.ndarray
    residual_norms: np.ndarray


def _float32_copy(values: np.ndarray, *, name: str) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype.kind != "f":
        raise ValueError(f"{name} must have a floating-point dtype")
    with np.errstate(over="ignore"):
        resolved = np.array(array, dtype=np.float32, order="C", copy=True)
    if not np.all(np.isfinite(resolved)):
        raise ValueError(f"{name} must contain only finite values")
    return resolved


def _fp32_norms(vectors: np.ndarray) -> np.ndarray:
    """Compute vector norms without overflowing intermediate FP32 squares."""
    scales = np.max(np.abs(vectors), axis=-1)
    scaled = np.zeros_like(vectors)
    nonzero = scales != 0.0
    np.divide(
        vectors,
        scales[..., np.newaxis],
        out=scaled,
        where=nonzero[..., np.newaxis],
    )
    with np.errstate(over="ignore"):
        norms = scales * np.sqrt(np.sum(scaled * scaled, axis=-1, dtype=np.float32))
    norms = np.array(norms, dtype=np.float32, order="C", copy=True)
    if not np.all(np.isfinite(norms)):
        raise ValueError("residual norms cannot be represented in FP32")
    return norms


def pack_signs(signs: np.ndarray) -> np.ndarray:
    """Pack boolean signs little-endian within each byte."""
    resolved = np.asarray(signs)
    if resolved.dtype != np.bool_:
        raise ValueError("signs must have boolean dtype")
    if resolved.ndim < 1:
        raise ValueError("signs must have at least one dimension")
    if resolved.shape[-1] == 0:
        raise ValueError("signs must have a positive final dimension")
    packed = np.packbits(resolved, axis=-1, bitorder="little")
    return np.array(packed, dtype=np.uint8, order="C", copy=True)


def unpack_signs(packed: np.ndarray, sketch_dim: int) -> np.ndarray:
    """Unpack little-endian bits into FP32 values in ``{-1, +1}``."""
    resolved = np.asarray(packed)
    if resolved.dtype != np.uint8:
        raise ValueError("packed signs must have uint8 dtype")
    if resolved.ndim < 1:
        raise ValueError("packed signs must have at least one dimension")
    if (
        isinstance(sketch_dim, (bool, np.bool_))
        or not isinstance(sketch_dim, (int, np.integer))
        or sketch_dim <= 0
    ):
        raise ValueError("sketch_dim must be a positive integer")
    packed_length = (int(sketch_dim) + 7) // 8
    if resolved.shape[-1] != packed_length:
        raise ValueError("packed signs have the wrong final length for sketch_dim")

    bits = np.unpackbits(resolved, axis=-1, count=int(sketch_dim), bitorder="little")
    signs = bits.astype(np.float32) * np.float32(2.0) - np.float32(1.0)
    return np.array(signs, dtype=np.float32, order="C", copy=True)


class ProductQuantizer:
    """Paper-literal QJL residual product estimator."""

    def __init__(self, mse_quantizer: MSEQuantizer, projection: np.ndarray) -> None:
        if not isinstance(mse_quantizer, MSEQuantizer):
            raise ValueError("mse_quantizer must be an MSEQuantizer")
        resolved_projection = _float32_copy(projection, name="projection")
        if resolved_projection.ndim != 2:
            raise ValueError("projection must be two-dimensional")
        if resolved_projection.shape[0] == 0:
            raise ValueError("projection must have a positive sketch dimension")
        if resolved_projection.shape[1] != mse_quantizer.rotation.shape[0]:
            raise ValueError("projection final dimension must match the MSE quantizer")

        resolved_projection.setflags(write=False)
        self._mse_quantizer = mse_quantizer
        self._projection = resolved_projection

    @property
    def mse_quantizer(self) -> MSEQuantizer:
        """The Algorithm 1 quantizer used for the base reconstruction."""
        return self._mse_quantizer

    @property
    def projection(self) -> np.ndarray:
        """The immutable iid-Gaussian projection rows."""
        return self._projection

    @property
    def sketch_dim(self) -> int:
        """Number of residual sign-sketch coordinates."""
        return self._projection.shape[0]

    def quantize(self, vectors: np.ndarray) -> ProductCodes:
        """Quantize vectors once and retain their residual sign sketches."""
        resolved_vectors = _float32_copy(vectors, name="vectors")
        mse_codes = self._mse_quantizer.quantize(resolved_vectors)
        mse_hat = self._mse_quantizer.dequantize(mse_codes)

        with np.errstate(over="ignore", invalid="ignore"):
            residual = resolved_vectors - mse_hat
        if not np.all(np.isfinite(residual)):
            raise ValueError("residuals must be representable in FP32")
        residual_norms = _fp32_norms(residual)
        with np.errstate(over="ignore", invalid="ignore"):
            projected = residual @ self._projection.T
        if not np.all(np.isfinite(projected)):
            raise ValueError("projected residuals must be representable in FP32")
        packed_signs = pack_signs(projected >= np.float32(0.0))

        return ProductCodes(
            mse=mse_codes,
            packed_signs=np.array(packed_signs, dtype=np.uint8, order="C", copy=True),
            residual_norms=np.array(
                residual_norms, dtype=np.float32, order="C", copy=True
            ),
        )

    def _validate_codes(
        self, codes: ProductCodes
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not isinstance(codes, ProductCodes):
            raise ValueError("codes must be a ProductCodes instance")
        mse_hat = self._mse_quantizer.dequantize(codes.mse)
        leading_shape = mse_hat.shape[:-1]

        packed_signs = np.asarray(codes.packed_signs)
        expected_packed_shape = leading_shape + ((self.sketch_dim + 7) // 8,)
        if (
            packed_signs.dtype != np.uint8
            or packed_signs.shape != expected_packed_shape
        ):
            raise ValueError(
                "packed_signs must be uint8 with the MSE codes' leading shape"
            )

        residual_norms = np.asarray(codes.residual_norms)
        if (
            residual_norms.dtype != np.float32
            or residual_norms.shape != leading_shape
            or not np.all(np.isfinite(residual_norms))
            or np.any(residual_norms < 0.0)
        ):
            raise ValueError(
                "residual_norms must be finite nonnegative FP32 with the MSE "
                "codes' leading shape"
            )
        return mse_hat, packed_signs, residual_norms

    def dequantize(self, codes: ProductCodes) -> np.ndarray:
        """Reconstruct the Algorithm 2 vector estimator."""
        mse_hat, packed_signs, residual_norms = self._validate_codes(codes)
        signs = unpack_signs(packed_signs, self.sketch_dim)
        coefficient = np.float32(np.sqrt(np.pi / 2.0) / self.sketch_dim)
        with np.errstate(over="ignore", invalid="ignore"):
            reconstructed = mse_hat + (
                coefficient
                * residual_norms[..., np.newaxis]
                * (signs @ self._projection)
            )
        original_norms = np.asarray(codes.mse.norms)
        np.copyto(
            reconstructed,
            np.float32(0.0),
            where=(original_norms == 0.0)[..., np.newaxis],
        )
        if not np.all(np.isfinite(reconstructed)):
            raise ValueError("dequantized product values must be representable in FP32")
        return np.array(reconstructed, dtype=np.float32, order="C", copy=True)

    def estimate_inner_products(
        self, queries: np.ndarray, codes: ProductCodes
    ) -> np.ndarray:
        """Estimate paired query/key products directly from Algorithm 2 codes."""
        resolved_queries = _float32_copy(queries, name="queries")
        dimension = self._projection.shape[1]
        if resolved_queries.ndim < 1 or resolved_queries.shape[-1] != dimension:
            raise ValueError(
                "queries must have final dimension matching the projection"
            )

        mse_hat, packed_signs, residual_norms = self._validate_codes(codes)
        if resolved_queries.shape[:-1] != mse_hat.shape[:-1]:
            raise ValueError(
                "queries and codes must have exactly the same leading shape"
            )

        signs = unpack_signs(packed_signs, self.sketch_dim)
        coefficient = np.float32(np.sqrt(np.pi / 2.0) / self.sketch_dim)
        with np.errstate(over="ignore", invalid="ignore"):
            mse_products = np.sum(resolved_queries * mse_hat, axis=-1, dtype=np.float32)
            query_sketches = resolved_queries @ self._projection.T
            residual_products = (
                coefficient
                * residual_norms
                * np.sum(query_sketches * signs, axis=-1, dtype=np.float32)
            )
            estimates = mse_products + residual_products
        if not np.all(np.isfinite(estimates)):
            raise ValueError("inner-product estimates must be representable in FP32")
        return np.array(estimates, dtype=np.float32, order="C", copy=True)
