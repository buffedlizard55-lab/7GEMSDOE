"""Exact random-emission baseline for the official distance-weighted Tversky index.

If every pixel of a region is emitted independently with probability ``f`` (value
1), the expected weighted-TP credit of any single truth pixel is

    c(f) = sum_l w_l * P(best emitted kernel level is l)

where the kernel levels are the distinct weights k(d) = 1 - d/3 of the integer
offsets with d < 3 px (1 px at w=1, 4 at 2/3, 4 at 0.529, 4 at 1/3, 8 at 0.255,
4 at 0.057). With truth density rho (truth pixels / scored pixels),

    DTI_random(f, rho) ~= c rho / (0.2 c rho + 0.2 f (1 - kappa rho) + 0.8 rho)

where kappa ~ 5 corrects the false-positive weight of emitted pixels that land
near truth (negligible for rho ~ 0.3%). The metric identity TP_w + FN_w = |G|
and alpha = 1 - beta = 0.2 give the denominator (see scripts/metric.py).

Uses: (1) calibrate leaderboard scores as a skill multiple over random emission;
(2) invert a known near-random submission to bracket the hidden truth density.
These are model-based inferences, not official facts.
"""
from __future__ import annotations

import numpy as np

from metric import _kernel_offsets

ALPHA, BETA = 0.2, 0.8


def kernel_levels(r_pixels: float = 3.0):
    levels = {}
    for _dy, _dx, _d, w in _kernel_offsets(r_pixels):
        if w > 0:
            key = round(w, 12)
            levels[key] = levels.get(key, 0) + 1
    return sorted(levels.items(), reverse=True)  # [(weight, count)] descending


def coverage_random(f: float, r_pixels: float = 3.0) -> float:
    """Expected per-truth-pixel TP credit c(f) under i.i.d. Bernoulli(f) emission."""
    if not 0 <= f <= 1:
        raise ValueError("f must be in [0, 1]")
    c, none_so_far = 0.0, 1.0
    for w, n in kernel_levels(r_pixels):
        p_any = 1.0 - (1.0 - f) ** n
        c += w * p_any * none_so_far
        none_so_far *= (1.0 - f) ** n
    return c


def dti_random(f: float, rho: float, kappa: float = 5.0) -> float:
    c = coverage_random(f)
    return c * rho / (ALPHA * c * rho + ALPHA * f * (1 - kappa * rho) + BETA * rho)


def coverage_from_score(dti: float, f: float, rho: float, kappa: float = 5.0) -> float:
    """Invert DTI = c rho / (0.2 c rho + 0.2 f (1-kappa rho) + 0.8 rho) for c."""
    num = dti * (ALPHA * f * (1 - kappa * rho) + BETA * rho)
    den = rho * (1 - ALPHA * dti)
    return num / den


def rho_from_random_score(dti: float, f: float, kappa: float = 5.0) -> float:
    """Truth density implied if a submission at density f had zero skill."""
    c = coverage_random(f)
    # dti (0.2 c rho + 0.2 f - 0.2 f kappa rho + 0.8 rho) = c rho
    a = c - dti * (ALPHA * c - ALPHA * f * kappa + BETA)
    return dti * ALPHA * f / a


if __name__ == "__main__":  # pragma: no cover
    for f in (0.005, 0.01, 0.02, 0.03, 0.05, 0.1):
        print(f"f={f:.3f}  c(f)={coverage_random(f):.4f}")
