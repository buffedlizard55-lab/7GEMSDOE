"""Mask-safe, fixed radiometric lineament features for GeoDAWN K/Th/U/TC.

The compact GeoDAWN product stores each source channel as an independently
quantised percentile-like uint8 value.  Consequently this module deliberately
does *not* calculate K/Th, K/U, or other geochemical ratios: ratios of the
quantised values would not be ratios of the original physical concentrations.
Instead it measures spatial boundaries at two fixed scales (about 100 and
300 m on the competition grid), which is the pre-registered H9b representation.

Missing values are zero in the source product.  Every smoothing operation uses
normalised convolution so the zero-coded survey edge does not become an
artificial high-gradient lineament.  Returned feature arrays are float16 to
keep the full-grid geographic experiment within the CPU runner's memory.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy.ndimage import binary_erosion, gaussian_filter, laplace

CHANNELS = ("K", "Th", "U", "TC")
SIGMAS = (1.0, 3.0)


def _check_inputs(raw: np.ndarray, valid: np.ndarray,
                  names: Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(raw)
    valid = np.asarray(valid, dtype=bool)
    if raw.ndim != 3 or raw.shape[0] != len(names):
        raise ValueError("raw radiometrics must have shape (channels, rows, cols)")
    if valid.shape != raw.shape[1:]:
        raise ValueError("valid mask shape must match the radiometric grid")
    if not np.issubdtype(raw.dtype, np.number):
        raise TypeError("raw radiometrics must be numeric")
    if not np.all(np.isfinite(raw)):
        raise ValueError("raw radiometrics contain NaN or infinity")
    return raw, valid


def normalized_gaussian(values: np.ndarray, valid: np.ndarray,
                        sigma: float) -> np.ndarray:
    """Gaussian smooth without treating missing cells as zero-valued geology."""
    values = np.asarray(values, dtype=np.float32)
    valid = np.asarray(valid, dtype=bool)
    if values.ndim != 2 or valid.shape != values.shape:
        raise ValueError("values and valid must be aligned 2-D arrays")
    if not np.isfinite(values).all():
        raise ValueError("values contain NaN or infinity")
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    weight = gaussian_filter(valid.astype(np.float32), sigma=sigma,
                             mode="nearest")
    total = gaussian_filter(np.where(valid, values, 0.0), sigma=sigma,
                            mode="nearest")
    out = np.divide(total, weight, out=np.zeros_like(total), where=weight > 1e-6)
    out[~valid] = 0.0
    return out


def build_lineament_features(raw: np.ndarray, valid: np.ndarray,
                             names: Sequence[str] = CHANNELS,
                             sigmas: Sequence[float] = SIGMAS
                             ) -> tuple[list[np.ndarray], list[str]]:
    """Return fixed multiscale edge/curvature/contrast features and names.

    ``raw`` may be the uint8 compact product or a numerical test fixture.  The
    scale factor is common to all derivatives; uint8 inputs are mapped to
    [0, 1].  It does not restore the original physical units.
    """
    raw, valid = _check_inputs(raw, valid, names)
    if not sigmas or any(float(s) <= 0 for s in sigmas):
        raise ValueError("at least one positive scale is required")
    scale = 255.0 if np.issubdtype(raw.dtype, np.integer) else 1.0
    channels = [raw[i].astype(np.float32) / scale for i in range(raw.shape[0])]
    # Finite differencing inspects immediate neighbours. Suppress the one-cell
    # inner survey rim so an outside zero cannot be interpreted as geology.
    derivative_support = binary_erosion(valid, structure=np.ones((3, 3), bool),
                                        border_value=0)
    features: list[np.ndarray] = []
    feature_names: list[str] = []
    sigma_values = tuple(map(float, sigmas))
    broad_sigma = sigma_values[-1]
    broad_contrasts: list[np.ndarray] = []

    for sigma in sigma_values:
        tag = f"s{sigma:g}"
        # Accumulate the tensor online rather than retaining 4 channels of
        # float32 gradients/magnitudes. This keeps a 12.3M-pixel build below
        # runner memory limits without changing the numerical definition.
        zeros = np.zeros(valid.shape, np.float32)
        jxx, jyy, jxy = zeros.copy(), zeros.copy(), zeros.copy()
        edge_sq = zeros.copy()
        edge_max = zeros.copy()
        del zeros
        for name, channel in zip(names, channels):
            smoothed = normalized_gaussian(channel, valid, sigma)
            gy, gx = np.gradient(smoothed)
            gx[~derivative_support] = 0.0
            gy[~derivative_support] = 0.0
            magnitude = np.hypot(gx, gy)
            curvature = np.abs(laplace(smoothed, mode="nearest"))
            magnitude[~derivative_support] = 0.0
            curvature[~derivative_support] = 0.0
            features.extend((magnitude.astype(np.float16),
                             curvature.astype(np.float16)))
            feature_names.extend((f"{name}_grad_{tag}", f"{name}_lapabs_{tag}"))
            jxx += gx * gx
            jyy += gy * gy
            jxy += gx * gy
            edge_sq += magnitude * magnitude
            np.maximum(edge_max, magnitude, out=edge_max)
            if sigma == broad_sigma:
                contrast = channel - smoothed
                contrast[~valid] = 0.0
                broad_contrasts.append(contrast.astype(np.float16))
            del smoothed, gx, gy, magnitude, curvature

        # A multi-channel edge is stronger when one or several radioelements
        # share a boundary. The structure tensor supplies orientation and
        # coherence without choosing a preferred fault strike.
        np.sqrt(edge_sq, out=edge_sq)
        energy = jxx + jyy
        anisotropy = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy ** 2)
        coherence = np.divide(anisotropy, energy, out=np.zeros_like(energy),
                              where=energy > 1e-12)
        cos2 = np.divide(jxx - jyy, energy, out=np.zeros_like(energy),
                         where=energy > 1e-12)
        sin2 = np.divide(2.0 * jxy, energy, out=np.zeros_like(energy),
                         where=energy > 1e-12)
        for array in (edge_sq, edge_max, coherence, cos2, sin2):
            array[~valid] = 0.0
        features.extend(array.astype(np.float16) for array in
                        (edge_sq, edge_max, coherence, cos2, sin2))
        feature_names.extend((f"edge_rss_{tag}", f"edge_max_{tag}",
                              f"edge_coherence_{tag}", f"edge_cos2_{tag}",
                              f"edge_sin2_{tag}"))

    # Fixed broad residual: a local departure from the 300 m (or largest
    # requested) background. This can express narrow alteration boundaries
    # without inventing physical element ratios from quantised channels.
    broad_tag = f"s{broad_sigma:g}"
    for name, contrast in zip(names, broad_contrasts):
        features.append(contrast)
        feature_names.append(f"{name}_contrast_{broad_tag}")

    if len(feature_names) != len(set(feature_names)):
        raise AssertionError("duplicate radiometric feature names")
    return features, feature_names
