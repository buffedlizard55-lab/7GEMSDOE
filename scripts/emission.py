"""Emission policies that turn a score field into a binary submission map.

Why thinning: the official kernel gives full credit within 0 px and partial
credit to 3 px, and the truth is made of thin traces. A blob of high scores
spends many emitted pixels on the same few truth pixels. The group's two
lowest-scoring uploads were the most blob-like (dispersion index 2.3-2.6);
the best were line-like (~5). See scripts/analyze_scored_files.py.

``ridge_nms`` keeps a pixel only if its (lightly smoothed) score is a local
maximum across the ridge direction given by the Hessian of the score.
"""
from __future__ import annotations

import numpy as np


def ridge_nms(score: np.ndarray, valid: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Boolean mask of ridge pixels (1 px wide) of a score field."""
    from scipy.ndimage import gaussian_filter
    s = np.where(valid, np.nan_to_num(score, nan=0.0, neginf=0.0), 0.0).astype(np.float32)
    ss = gaussian_filter(s, sigma) if sigma > 0 else s
    gy, gx = np.gradient(ss)
    hyy, hyx = np.gradient(gy)
    hxy, hxx = np.gradient(gx)
    hxy = 0.5 * (hxy + hyx)
    del gy, gx, hyx
    # eigenvector of the most negative eigenvalue = across-ridge direction
    tmp = np.sqrt(((hxx - hyy) * 0.5) ** 2 + hxy ** 2)
    lam = 0.5 * (hxx + hyy) - tmp  # most negative eigenvalue
    vx = hxy
    vy = lam - hxx
    small = (np.abs(vx) + np.abs(vy)) < 1e-12
    vx = np.where(small, 1.0, vx)
    vy = np.where(small, 0.0, vy)
    ang = np.mod(np.degrees(np.arctan2(vy, vx)), 180.0)
    del hxx, hyy, hxy, tmp, vx, vy
    # quantise to the four neighbour axes: 0 (E-W), 45, 90 (N-S), 135 degrees
    q = (np.round(ang / 45.0).astype(np.int8)) % 4
    pad = np.pad(ss, 1, mode="edge")
    h, w = ss.shape
    c = pad[1:-1, 1:-1]
    # (dy, dx) in array coordinates for each axis; arrays have y down, so a +45
    # degree vector (vx>0, vy>0 in array axes) points right-down.
    offs = {0: (0, 1), 1: (1, 1), 2: (1, 0), 3: (1, -1)}
    keep = np.zeros((h, w), bool)
    for k, (dy, dx) in offs.items():
        a = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        b = pad[1 - dy:1 - dy + h, 1 - dx:1 - dx + w]
        m = (q == k) & (c >= a) & (c >= b)
        keep |= m
    return keep & valid & (s > 0)


def top_k_mask(score: np.ndarray, candidates: np.ndarray, k: int) -> np.ndarray:
    """Top-k candidate pixels by score (ties broken by the partition order)."""
    idx = np.flatnonzero(candidates.ravel())
    if k <= 0 or idx.size == 0:
        return np.zeros(score.shape, bool)
    k = min(k, idx.size)
    vals = score.ravel()[idx]
    sel = idx[np.argpartition(vals, -k)[-k:]]
    out = np.zeros(score.size, bool)
    out[sel] = True
    return out.reshape(score.shape)


def dispersion_index(emitted: np.ndarray, valid: np.ndarray) -> float:
    from scipy.ndimage import binary_dilation
    n = int(emitted.sum())
    if n == 0:
        return float("nan")
    return float((binary_dilation(emitted, iterations=2) & valid).sum()) / n
