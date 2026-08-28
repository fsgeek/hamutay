"""Algorithm 1 spherical MSE quantization reference implementation."""

from dataclasses import dataclass

import numpy as np

from .codebook import nearest_code_indices


@dataclass(frozen=True, slots=True)
class MSECodes:
    """Scalar quantization indices and the original vector norms."""

    indices: np.ndarray
    norms: np.ndarray


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
    """Return robust FP32 vector norms or reject values outside FP32 range."""
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
        raise ValueError("vector norms cannot be represented in FP32")
    return norms


class MSEQuantizer:
    """Quantize normalized, rotated vectors with a frozen scalar codebook."""

    def __init__(self, rotation: np.ndarray, codebook: np.ndarray) -> None:
        resolved_rotation = _float32_copy(rotation, name="rotation")
        resolved_codebook = _float32_copy(codebook, name="codebook")

        if (
            resolved_rotation.ndim != 2
            or resolved_rotation.shape[0] != resolved_rotation.shape[1]
        ):
            raise ValueError("rotation must be square")
        if resolved_codebook.ndim != 1 or resolved_codebook.size == 0:
            raise ValueError("codebook must be a nonempty one-dimensional array")
        if resolved_codebook.size > np.iinfo(np.uint8).max + 1:
            raise ValueError("codebook may contain at most 256 centroids")
        if not np.all(np.diff(resolved_codebook) > 0.0):
            raise ValueError("codebook must be strictly increasing")

        dimension = resolved_rotation.shape[0]
        if not np.allclose(
            resolved_rotation @ resolved_rotation.T,
            np.eye(dimension, dtype=np.float32),
            rtol=0.0,
            atol=2e-5,
        ):
            raise ValueError("rotation must be orthogonal")

        resolved_rotation.setflags(write=False)
        resolved_codebook.setflags(write=False)
        self._rotation = resolved_rotation
        self._codebook = resolved_codebook

    @property
    def rotation(self) -> np.ndarray:
        """The immutable row-vector rotation matrix."""
        return self._rotation

    @property
    def codebook(self) -> np.ndarray:
        """The immutable scalar codebook."""
        return self._codebook

    def quantize(self, vectors: np.ndarray) -> MSECodes:
        """Return scalar codes for vectors under Algorithm 1."""
        resolved_vectors = _float32_copy(vectors, name="vectors")
        if (
            resolved_vectors.ndim < 1
            or resolved_vectors.shape[-1] != self._rotation.shape[0]
        ):
            raise ValueError("vectors must have final dimension matching the rotation")

        norms = _fp32_norms(resolved_vectors)
        normalized = np.zeros_like(resolved_vectors)
        nonzero = norms != 0.0
        np.divide(
            resolved_vectors,
            norms[..., np.newaxis],
            out=normalized,
            where=nonzero[..., np.newaxis],
        )
        rotated = normalized @ self._rotation.T
        indices = nearest_code_indices(rotated, self._codebook)
        np.copyto(indices, 0, where=(~nonzero)[..., np.newaxis])

        return MSECodes(
            indices=np.array(indices, dtype=np.uint8, order="C", copy=True),
            norms=np.array(norms, dtype=np.float32, order="C", copy=True),
        )

    def dequantize(self, codes: MSECodes) -> np.ndarray:
        """Reconstruct approximate vectors from Algorithm 1 codes."""
        if not isinstance(codes, MSECodes):
            raise ValueError("codes must be an MSECodes instance")
        indices = np.asarray(codes.indices)
        norms = np.asarray(codes.norms)
        dimension = self._rotation.shape[0]
        if (
            indices.dtype != np.uint8
            or indices.ndim < 1
            or indices.shape[-1] != dimension
        ):
            raise ValueError("indices must be uint8 with final dimension matching the rotation")
        if norms.dtype != np.float32 or norms.shape != indices.shape[:-1]:
            raise ValueError("norms must be FP32 with indices' leading shape")
        if not np.all(np.isfinite(norms)) or np.any(norms < 0.0):
            raise ValueError("norms must be finite and nonnegative")
        if np.any(indices >= self._codebook.size):
            raise ValueError("indices contain a value outside the codebook")

        rotated_hat = self._codebook[indices]
        reconstructed = (rotated_hat @ self._rotation) * norms[..., np.newaxis]
        np.copyto(reconstructed, 0.0, where=(norms == 0.0)[..., np.newaxis])
        return np.array(reconstructed, dtype=np.float32, order="C", copy=True)
