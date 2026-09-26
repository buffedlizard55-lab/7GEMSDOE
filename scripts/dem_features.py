"""H4b: region-scale native-lidar scarp evidence aggregated to the competition grid.

Why: faults that experts add to a Quaternary catalogue are most often recognised
as linear scarps in high-resolution topography. The competition supplies links to
USGS 3DEP 1 m DEMs, but the 100 m feature stack only carries coarse detrended
slope. This script turns each 1 m tile into physically interpretable 2 m scarp
descriptors, then aggregates them onto the official 100 m EPSG:32611 grid.

Scientific framing (not a claim of discovery):
* A fault scarp is a short-wavelength step superimposed on a gentler regional
  surface (Hilley et al. 2010, GRL, doi:10.1029/2009GL042044; Sare et al. 2019,
  JGR Solid Earth, doi:10.1029/2018JB016886). We therefore measure slope in excess
  of a 30-50 m regional slope, curvature at the crest/base and linear coherence.
* Roads, channels, terrace risers, paleo-shorelines, landslides and mines produce
  similar steps. These are uncalibrated descriptors, not fault detections.

Output per tile: ``<out>/<tile>.npz`` with the destination window on the official
grid and float32 channel arrays (NaN = no lidar). ``scripts/dem_merge.py`` mosaics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

# Official competition grid (verified against example_submission.tif by tests).
GRID_CRS = "EPSG:32611"
GRID_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
GRID_SHAPE = (3730, 3292)
WORK_RES = 2.0  # metres; scarps are ~5-50 m wide so 2 m keeps them resolved

CHANNELS = [
    # name, aggregation, short meaning
    ("s1_max", "max", "max 2 m slope (m/m) after 2 m smoothing"),
    ("ex_max", "max", "max slope in excess of 30 m regional slope"),
    ("ex_mean", "average", "mean slope excess (short-wavelength steepness)"),
    ("step_max", "max", "max 10 m-scale slope minus 50 m-scale slope"),
    ("lapneg_max", "max", "max crest convexity (-Laplacian of Gaussian, 6 m)"),
    ("lappos_max", "max", "max base concavity (+Laplacian of Gaussian, 6 m)"),
    ("rough", "average", "mean squared residual from 10 m surface (sqrt later)"),
    ("jxx_m_jyy", "average", "structure tensor Jxx-Jyy (doubled-angle cos)"),
    ("j2xy", "average", "structure tensor 2*Jxy (doubled-angle sin)"),
    ("jtrace", "average", "structure tensor trace (gradient energy)"),
    ("zmax", "max", "max elevation (m)"),
    ("zmin", "min", "min elevation (m)"),
    ("valid", "average", "fraction of valid lidar samples"),
]


def _nearest_fill(z: np.ndarray, valid: np.ndarray) -> np.ndarray:
    from scipy.ndimage import distance_transform_edt
    if valid.all():
        return z
    idx = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return z[tuple(idx)]


def scarp_channels(z: np.ndarray, valid: np.ndarray, res: float = WORK_RES) -> dict:
    """Compute per-pixel scarp descriptors on a regular metric grid.

    ``z`` elevation (m), ``valid`` boolean mask. Returns float32 arrays keyed by
    CHANNELS names (before aggregation). Invalid pixels (dilated by the largest
    filter support) are NaN so that nodata edges cannot masquerade as scarps.
    """
    from scipy.ndimage import binary_erosion, gaussian_filter, gaussian_laplace

    if z.ndim != 2 or z.shape != valid.shape:
        raise ValueError("z and valid must be equal 2-D arrays")
    if valid.mean() < 0.01:
        raise ValueError("tile has <1% valid samples")
    zf = _nearest_fill(z.astype(np.float32), valid)
    px = lambda metres: metres / res  # noqa: E731 - sigma in pixels
    # Odd (point) reflection keeps planar surfaces planar across the tile edge.
    # scipy's default even reflection makes a V-shaped surface whose smoothed
    # gradient collapses at the edge, i.e. a spurious step along every tile seam.
    pad = int(np.ceil(4 * px(50.0))) + 2
    zp = np.pad(zf, pad, mode="reflect", reflect_type="odd")
    del zf
    crop = (slice(pad, -pad), slice(pad, -pad))

    def smooth(sig_m):
        return gaussian_filter(zp, px(sig_m), mode="nearest")

    def grad(a):
        gy, gx = np.gradient(a, res)
        return gx, gy

    z1 = smooth(2.0); gx, gy = grad(z1); s1 = np.hypot(gx, gy)
    z15 = smooth(30.0); gx, gy = grad(z15); s15 = np.hypot(gx, gy); del z15
    z5 = smooth(10.0); gx, gy = grad(z5); s5 = np.hypot(gx, gy)
    z25 = smooth(50.0); gx, gy = grad(z25); s25 = np.hypot(gx, gy)
    ex = np.maximum(s1 - s15, 0); del s15
    step = np.maximum(s5 - s25, 0); del s5, s25
    lap = gaussian_laplace(zp, px(6.0), mode="nearest")
    rough = (zp - z5) ** 2
    # Orientation from the band-passed (10 m - 50 m) surface so a regional fan
    # or range-front gradient does not rotate the scarp strike estimate.
    gxb, gyb = grad(z5 - z25)
    del z25, z5, gx, gy
    sig_t = px(20.0)
    jxx = gaussian_filter(gxb * gxb, sig_t, mode="nearest")
    jyy = gaussian_filter(gyb * gyb, sig_t, mode="nearest")
    jxy = gaussian_filter(gxb * gyb, sig_t, mode="nearest")
    del gxb, gyb
    safe = binary_erosion(valid, iterations=int(np.ceil(px(50.0))), border_value=1)
    out = {
        "s1_max": s1, "ex_max": ex, "ex_mean": ex, "step_max": step,
        "lapneg_max": np.maximum(-lap, 0), "lappos_max": np.maximum(lap, 0),
        "rough": rough, "jxx_m_jyy": jxx - jyy, "j2xy": 2 * jxy, "jtrace": jxx + jyy,
        "zmax": z1, "zmin": z1,
    }
    for k in out:
        a = np.array(out[k][crop], dtype=np.float32)
        a[~safe] = np.nan
        out[k] = a
    out["valid"] = valid.astype(np.float32)
    return out


def grid_window_for_bounds(left, bottom, right, top):
    """Official-grid (row_off, col_off, height, width) covering metric bounds."""
    a, _, c, _, e, f = GRID_TRANSFORM
    c0 = int(np.floor((left - c) / a)) - 1
    c1 = int(np.ceil((right - c) / a)) + 1
    r0 = int(np.floor((f - top) / -e)) - 1
    r1 = int(np.ceil((f - bottom) / -e)) + 1
    r0, c0 = max(r0, 0), max(c0, 0)
    r1, c1 = min(r1, GRID_SHAPE[0]), min(c1, GRID_SHAPE[1])
    if r1 <= r0 or c1 <= c0:
        return None
    return r0, c0, r1 - r0, c1 - c0


def aggregate(channels: dict, src_transform, src_crs):
    """Aggregate 2 m channels onto the official 100 m grid window."""
    import rasterio
    from rasterio.transform import Affine, array_bounds
    from rasterio.warp import reproject, Resampling, transform_bounds

    h, w = channels["valid"].shape
    bounds = array_bounds(h, w, src_transform)
    gb = transform_bounds(src_crs, GRID_CRS, *bounds, densify_pts=21)
    win = grid_window_for_bounds(*gb)
    if win is None:
        return None
    r0, c0, hh, ww = win
    a, b, c, d, e, f = GRID_TRANSFORM
    dst_t = Affine(a, b, c + c0 * a, d, e, f + r0 * e)
    res = {}
    rs = {"max": Resampling.max, "min": Resampling.min, "average": Resampling.average}
    for name, how, _ in CHANNELS:
        dst = np.full((hh, ww), np.nan, np.float32)
        src = channels[name]
        if name == "valid":  # fraction of footprint with lidar; 0 outside tile
            src = np.where(np.isfinite(src), src, 0).astype(np.float32)
        reproject(src, dst, src_transform=src_transform, src_crs=src_crs,
                  src_nodata=np.nan, dst_transform=dst_t, dst_crs=GRID_CRS,
                  dst_nodata=np.nan, resampling=rs[how])
        res[name] = dst
    return (r0, c0, hh, ww), res


def process_tile(path_or_url: str) -> dict:
    import rasterio
    from rasterio.enums import Resampling

    with rasterio.open(path_or_url) as src:
        if src.crs is None or not src.crs.is_projected:
            raise ValueError("expected projected DEM")
        fac = WORK_RES / abs(src.res[0])
        oh, ow = int(round(src.height / fac)), int(round(src.width / fac))
        z = src.read(1, out_shape=(oh, ow), resampling=Resampling.average, masked=True)
        valid = ~np.ma.getmaskarray(z) & np.isfinite(z.data) & (z.data > -1000) & (z.data < 9000)
        t = src.transform * src.transform.scale(src.width / ow, src.height / oh)
        info = dict(crs=str(src.crs), native_res=list(src.res), shape=[src.height, src.width],
                    work_shape=[oh, ow], overviews=src.overviews(1), dtype=src.dtypes[0])
        ch = scarp_channels(z.data.astype(np.float32), valid, WORK_RES)
        agg = aggregate(ch, t, src.crs)
    return info, agg


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", default="knowledge/dem_tiles.json")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--out", default="scratch/dem")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workdir", default="/tmp/dem")
    args = ap.parse_args(argv)
    recs = json.loads(Path(args.tiles).read_text())["records"]
    mine = [r for i, r in enumerate(recs) if i % args.nshards == args.shard]
    if args.limit:
        mine = mine[: args.limit]
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    work = Path(args.workdir); work.mkdir(parents=True, exist_ok=True)
    log = []
    for r in mine:
        t0 = time.time()
        stem = Path(r["filename"]).stem
        local = work / r["filename"]
        entry = dict(tile=stem, url=r["url"])
        try:
            if not r["url"].startswith("https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/"):
                raise ValueError("URL is not in the official USGS 3DEP 1 m bucket")
            subprocess.run(["curl", "-fsSL", "--retry", "4", "--retry-delay", "3",
                            "--connect-timeout", "30", "-o", str(local), r["url"]], check=True)
            entry["bytes"] = local.stat().st_size
            h = hashlib.sha256()
            with open(local, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 22), b""):
                    h.update(chunk)
            entry["sha256"] = h.hexdigest()
            info, agg = process_tile(str(local))
            entry.update(info)
            if agg is None:
                entry["status"] = "outside_grid"
            else:
                (r0, c0, hh, ww), arrs = agg
                np.savez_compressed(out / f"{stem}.npz", window=np.array([r0, c0, hh, ww]),
                                    **{k: v.astype(np.float32) for k, v in arrs.items()})
                entry.update(status="ok", window=[r0, c0, hh, ww],
                             valid_cells=int(np.nansum(arrs["valid"] > 0.5)))
        except Exception as exc:  # recorded, never silently treated as success
            entry.update(status="failed", error=f"{type(exc).__name__}: {str(exc)[:300]}")
        finally:
            if local.exists():
                local.unlink()
        entry["seconds"] = round(time.time() - t0, 1)
        log.append(entry)
        print(json.dumps({k: entry.get(k) for k in ("tile", "status", "seconds", "bytes", "error")}), flush=True)
    (out / f"shard_{args.shard:03d}.json").write_text(json.dumps(log, indent=1))
    ok = sum(e["status"] == "ok" for e in log)
    print(f"shard {args.shard}: {ok}/{len(log)} tiles ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
