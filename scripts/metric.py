"""Official competition metric: distance-weighted Tversky index (DTI).

Implemented verbatim from the "Performance metric" section of the problem page:
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric

Definitions (quoted formulas, our variable names):

  kernel            k(d) = max(1 - d/R, 0)          with R = 300 m (3 px at 100 m)
  TP_w = sum_{g in G}  max_{x : d(x,g) <= R}  p(x) * k(d(x,g))
  FP_w = sum_{x : p(x) > 0}  p(x) * [1 - max_{g in G} k(d(x,g))]
  FN_w = sum_{g in G}  [1 - max_{x : d(x,g) <= R} p(x) * k(d(x,g))]
  DTI(alpha, beta) = TP_w / (TP_w + alpha*FP_w + beta*FN_w + eps)

Competition parameters: alpha = 0.2, beta = 0.8, R = 3 pixels.

Notes
-----
* Distances are Euclidean in pixel units (100 m / px), exactly as the metric's
  own scoring example applies the triangular kernel on the pixel grid.
* Ground-truth pixels outside the raster footprint cannot exist (labels are
  defined only inside it); predictions use NaN outside the footprint and any
  non-finite prediction is treated as "no prediction" (p = 0).
* Identity (checked by tests): TP_w + FN_w == |G| for every prediction.
"""

from __future__ import annotations

import numpy as np

ALPHA = 0.2
BETA = 0.8
R_PIXELS = 3.0          # 300 m at 100 m resolution
EPS = 1e-10


def _kernel_offsets(r_pixels: float = R_PIXELS):
    """All integer pixel offsets inside the kernel radius, with kernel weight."""
    r = int(np.floor(r_pixels))
    offs = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = float(np.hypot(dx, dy))
            if d <= r_pixels:
                offs.append((dy, dx, d, max(1.0 - d / r_pixels, 0.0)))
    return offs


_OFFSETS = _kernel_offsets()


def _shift(arr: np.ndarray, dy: int, dx: int, fill: float = 0.0) -> np.ndarray:
    """Shift array so that out[y, x] = arr[y - dy, x - dx]; fill outside."""
    out = np.full_like(arr, fill, dtype=np.float64)
    h, w = arr.shape
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = arr[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def dtvi_components(pred: np.ndarray, truth: np.ndarray,
                    r_pixels: float = R_PIXELS) -> dict:
    """Compute TP_w, FP_w, FN_w for a prediction/truth pair.

    Parameters
    ----------
    pred : (H, W) float array, values in [0, 1]; non-finite = no prediction.
    truth : (H, W) array; positive where ground-truth fault (> 0 counts).

    Returns
    -------
    dict with TP_w, FP_w, FN_w, n_truth, predicted_mass.
    """
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth)
    if pred.shape != truth.shape:
        raise ValueError(f"shape mismatch: {pred.shape} vs {truth.shape}")

    p = np.where(np.isfinite(pred), pred, 0.0)
    if p.min() < 0.0 or p.max() > 1.0:
        raise ValueError("predictions must be in [0, 1] (non-finite treated as 0)")

    g_mask = truth > 0
    g_idx = np.argwhere(g_mask)          # (N, 2) rows of (y, x)
    n_truth = int(g_mask.sum())

    # --- TP_w and FN_w: for every truth pixel g, max over x within R of p(x)k(d) ---
    contrib = np.zeros(p.shape, dtype=np.float64)
    if n_truth:
        for dy, dx, _d, w in _kernel_offsets(r_pixels):
            if w == 0.0:
                continue
            shifted = _shift(p, dy, dx)          # shifted[g] == p[g - off]... see note
            contrib = np.maximum(contrib, shifted * w)
        # NOTE: _shift(p, dy, dx)[y, x] = p[y - dy, x - dx]; with the loop over all
        # symmetric offsets {(-dy, -dx)} == {(dy, dx)}, the set of sampled p around
        # each g is exactly {p(g + off) : |off| <= R}, so the max is correct.
        contrib = contrib[g_mask]

    tp_w = float(contrib.sum())
    fn_w = float(n_truth - contrib.sum())

    # --- FP_w: max_g k(d(x, g)) via distance transform to truth ---
    if n_truth:
        from scipy.ndimage import distance_transform_edt
        dist = distance_transform_edt(~g_mask)   # px distance to nearest truth px
        kern = np.maximum(1.0 - dist / r_pixels, 0.0)
    else:
        kern = np.zeros(p.shape, dtype=np.float64)
    fp_w = float((p[p > 0] * (1.0 - kern[p > 0])).sum())

    return {
        "TP_w": tp_w,
        "FP_w": fp_w,
        "FN_w": fn_w,
        "n_truth": n_truth,
        "predicted_mass": float(p.sum()),
    }


def dtvi(pred: np.ndarray, truth: np.ndarray, alpha: float = ALPHA,
         beta: float = BETA, r_pixels: float = R_PIXELS,
         eps: float = EPS) -> float:
    """Distance-weighted Tversky index (official competition metric)."""
    c = dtvi_components(pred, truth, r_pixels=r_pixels)
    denom = c["TP_w"] + alpha * c["FP_w"] + beta * c["FN_w"] + eps
    return float(c["TP_w"] / denom)


def dtvi_closed_form(tp_w: float, fp_w: float, n_truth: float,
                     alpha: float = ALPHA, beta: float = BETA,
                     eps: float = EPS) -> float:
    """Closed form using the identity FN_w = |G| - TP_w.

    Algebra: TP_w + alpha*FP_w + beta*FN_w
           = TP_w + alpha*FP_w + beta*(|G| - TP_w)
           = (1 - beta)*TP_w + alpha*FP_w + beta*|G|
           = alpha*(TP_w + FP_w) + beta*|G|      when alpha = 1 - beta
             (true for the competition's alpha = 0.2, beta = 0.8).
    So DTI = TP_w / (alpha*(TP_w + FP_w) + beta*|G| + eps)."""
    fn_w = n_truth - tp_w
    return float(tp_w / (tp_w + alpha * fp_w + beta * fn_w + eps))


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys
    # CLI: score a prediction GeoTIFF against a truth GeoTIFF
    import rasterio
    with rasterio.open(sys.argv[1]) as s:
        pred = s.read(1).astype(np.float64)
    with rasterio.open(sys.argv[2]) as t:
        truth = t.read(1).astype(np.float64)
        nod = t.nodata
    if nod is not None:
        truth = np.where(truth == nod, 0.0, truth)
    c = dtvi_components(pred, truth)
    c["DTI"] = dtvi(pred, truth)
    print(json.dumps(c, indent=1))
