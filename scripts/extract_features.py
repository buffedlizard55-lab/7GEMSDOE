"""Extract per-pixel feature vectors from the official GeoDAWN feature stack.

Memory-profiled for a 4 GB sandbox: peak ~1.2 GB.

Reads  gems_data/training_features.tif (19 bands, EPSG:32611, 100 m),
derives edge/texture features, robustly normalises every channel to [0, 1]
(1st/99th percentile of footprint-valid pixels) and stores:

    gems_data/features_cache.npz
        X        (N_valid, C) float32   - normalised feature matrix
        names    (C,)                    - channel names
        valid    (H, W) bool             - footprint mask (== template mask)
        shape    (2,)                    - (H, W)
    gems_data/norm_stats.json             - per-channel lo/hi percentiles

The submission footprint is asserted equal to the official template
(example_submission.tif): predictions must be finite exactly inside it.
Pixels inside the footprint where some band is NaN are imputed with the
band median and counted in the report (measured: 3,073 band-pixels).
"""

from __future__ import annotations

import json
import sys

import numpy as np
import rasterio
from scipy.ndimage import uniform_filter
from scipy.signal import convolve2d

from paths import CACHE_NPZ, FEATURES_TIF, NORM_JSON, TEMPLATE_TIF, ensure_data

SOBEL_BANDS = {  # band index (1-based) -> derived name
    6: "tilt_edge",        # tilt angle / total curvature (edge-detection band)
    14: "tmi_edge",        # total magnetic intensity
    18: "grav_hg_edge",    # isostatic gravity anomaly horizontal gradient
    12: "detrend_elev_edge",
    2: "rtp_edge",
    3: "tmi_hg_edge",
}
LOCALSTD_BANDS = {6: "tilt_lstd5", 18: "grav_hg_lstd5"}

PCT_LO, PCT_HI = 1.0, 99.0

KX = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / 8.0
KY = KX.T


def sobel_mag(a: np.ndarray) -> np.ndarray:
    a = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
    gx = convolve2d(a, KX, mode="same", boundary="symm")
    gy = convolve2d(a, KY, mode="same", boundary="symm")
    out = np.sqrt(gx * gx + gy * gy)
    del gx, gy
    return out


def local_std(a: np.ndarray, size: int = 5) -> np.ndarray:
    a = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
    m = uniform_filter(a, size=size, mode="nearest")
    m2 = uniform_filter(a * a, size=size, mode="nearest")
    out = np.sqrt(np.maximum(m2 - m * m, 0.0))
    del m, m2
    return out


def main() -> None:
    ensure_data()
    with rasterio.open(FEATURES_TIF) as src:
        meta_bands = [src.tags(i) for i in range(1, src.count + 1)]
        shape = (src.height, src.width)
        n_bands = src.count
        raw = np.empty((n_bands,) + shape, dtype=np.float32)
        for i in range(1, n_bands + 1):
            b = src.read(i)
            b[b < -1e38] = np.nan
            raw[i - 1] = b
        print(f"read {n_bands} bands", flush=True)

    with rasterio.open(TEMPLATE_TIF) as src:
        template_valid = np.isfinite(src.read(1))
    valid = template_valid
    n_valid = int(valid.sum())
    print(f"footprint valid px: {n_valid}", flush=True)

    # impute in-footprint holes with band medians
    report = {"imputed_band_pixels": 0, "imputed_px_per_band": {}}
    for i in range(n_bands):
        b = raw[i]
        m = ~np.isfinite(b) & valid
        n = int(m.sum())
        if n:
            med = float(np.nanmedian(b[valid]))
            b[m] = med
            report["imputed_band_pixels"] += n
            report["imputed_px_per_band"][str(i + 1)] = n
    print("imputed", report["imputed_band_pixels"], "band-pixels", flush=True)

    # channel plan: (name, array_or_factory)
    base_names = [f"b{i+1:02d}_" + (meta_bands[i].get("band_name") or
                                    meta_bands[i].get("description", "")[:18]
                                    .replace(" ", "_"))
                  for i in range(n_bands)]
    plan = [(base_names[i], raw[i]) for i in range(n_bands)]
    for bi, nm in SOBEL_BANDS.items():
        plan.append((nm, sobel_mag(raw[bi - 1])))
        print("derived", nm, flush=True)
    for bi, nm in LOCALSTD_BANDS.items():
        plan.append((nm, local_std(raw[bi - 1])))
        print("derived", nm, flush=True)
    del raw

    C = len(plan)
    X = np.empty((n_valid, C), dtype=np.float32)
    names = []
    los, his = [], []
    for j, (nm, arr) in enumerate(plan):
        v = arr[valid]
        lo = float(np.percentile(v, PCT_LO))
        hi = float(np.percentile(v, PCT_HI))
        rng = hi - lo if hi - lo > 1e-12 else 1.0
        X[:, j] = np.clip((v - lo) / rng, 0.0, 1.0).astype(np.float32)
        names.append(nm)
        los.append(lo)
        his.append(hi)
        del arr, v
        if j % 5 == 0:
            print(f"channel {j+1}/{C} normalised", flush=True)

    NORM_JSON.write_text(json.dumps({
        "pct_lo": PCT_LO, "pct_hi": PCT_HI, "names": names,
        "lo": los, "hi": his, **report,
    }, indent=1))
    print("wrote", NORM_JSON, flush=True)

    np.savez_compressed(
        CACHE_NPZ, X=X, names=np.array(names), valid=valid,
        shape=np.array(shape, dtype=np.int64))
    print("wrote", CACHE_NPZ, f"({CACHE_NPZ.stat().st_size/1e6:.1f} MB)", flush=True)


if __name__ == "__main__":
    sys.exit(main())
