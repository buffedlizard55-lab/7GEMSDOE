"""Mosaic per-tile lidar scarp channels onto the official 100 m grid.

Overlapping tiles (6 m tile buffers and duplicate project coverage) are merged
by max for extreme-value channels and by valid-fraction-weighted mean for mean
channels. Derived channels: sqrt roughness, 100 m structure-tensor coherence,
dominant scarp strike (degrees east of grid north, 0-180), relief.

The committed product is uint8 (0 = no lidar) with documented monotone
quantisation so it stays small enough for Git. Float values can be recovered
approximately with ``dequantise``. Uncalibrated descriptors, not detections.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np

import dem_features as DF

# name: (xmax, transform) ; q = 1 + round(254 * t(min(x/xmax,1))) ; 0 = nodata
QUANT = {
    "ex_max": (1.5, "sqrt"), "ex_mean": (0.3, "sqrt"), "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"), "lappos_max": (0.05, "sqrt"),
    "downface_max": (1.0, "sqrt"), "upface_max": (1.0, "sqrt"), "cross_max": (1.0, "sqrt"),
    "relief": (300.0, "sqrt"), "coh100": (1.0, "linear"), "strike": (180.0, "linear"),
    "valid": (1.0, "linear"),
}
BANDS = list(QUANT)


def quantise(name, x):
    xmax, how = QUANT[name]
    u = np.clip(np.where(np.isfinite(x), x, 0) / xmax, 0, 1)
    if how == "sqrt":
        u = np.sqrt(u)
    q = (1 + np.round(254 * u)).astype(np.uint8)
    q[~np.isfinite(x)] = 0
    return q


def dequantise(name, q):
    xmax, how = QUANT[name]
    u = (q.astype(np.float32) - 1) / 254
    x = (u ** 2 if how == "sqrt" else u) * xmax
    return np.where(q == 0, np.nan, x).astype(np.float32)


def mosaic(files):
    H, W = DF.GRID_SHAPE
    maxc = [n for n, how, _ in DF.CHANNELS if how == "max"]
    minc = [n for n, how, _ in DF.CHANNELS if how == "min"]
    avgc = [n for n, how, _ in DF.CHANNELS if how == "average" and n != "valid"]
    acc = {n: np.full((H, W), -np.inf, np.float32) for n in maxc}
    acc.update({n: np.full((H, W), np.inf, np.float32) for n in minc})
    sums = {n: np.zeros((H, W), np.float64) for n in avgc}
    wsum = np.zeros((H, W), np.float64)
    vsum = np.zeros((H, W), np.float32)
    for f in files:
        d = np.load(f)
        r0, c0, h, w = [int(v) for v in d["window"]]
        sl = (slice(r0, r0 + h), slice(c0, c0 + w))
        v = np.nan_to_num(d["valid"], nan=0.0)
        vsum[sl] += v
        for n in maxc:
            a = d[n]; ok = np.isfinite(a)
            acc[n][sl][ok] = np.maximum(acc[n][sl][ok], a[ok])
        for n in minc:
            a = d[n]; ok = np.isfinite(a)
            acc[n][sl][ok] = np.minimum(acc[n][sl][ok], a[ok])
        for n in avgc:
            a = d[n]; ok = np.isfinite(a) & (v > 0)
            sums[n][sl][ok] += a[ok] * v[ok]
        okw = np.isfinite(d["jtrace"]) & (v > 0)
        wsum[sl][okw] += v[okw]
    out = {}
    for n in maxc + minc:
        a = acc[n]; a[~np.isfinite(a)] = np.nan; out[n] = a
    with np.errstate(invalid="ignore", divide="ignore"):
        for n in avgc:
            out[n] = np.where(wsum > 0, sums[n] / wsum, np.nan).astype(np.float32)
    out["valid"] = np.where(vsum > 0, np.minimum(vsum, 1), np.nan).astype(np.float32)
    return out


def derive(raw):
    with np.errstate(invalid="ignore", divide="ignore"):
        coh = np.hypot(raw["jxx_m_jyy"], raw["j2xy"]) / raw["jtrace"]
        # gradient azimuth doubled-angle -> strike is perpendicular to gradient.
        # array x = east, array y = row (south), so north-up angle uses -gy.
        grad_dir = 0.5 * np.degrees(np.arctan2(-raw["j2xy"], raw["jxx_m_jyy"]))  # from +x (east), CCW
        strike_from_east = grad_dir + 90.0
        strike = np.mod(90.0 - strike_from_east, 180.0)  # azimuth clockwise from north
    out = {n: raw[n] for n in ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
                                "downface_max", "upface_max", "cross_max") if n in raw}
    out.update({"relief": raw["zmax"] - raw["zmin"], "coh100": np.clip(coh, 0, 1),
                "strike": strike, "valid": raw["valid"]})
    return out


def main(argv=None):
    import rasterio
    from rasterio.transform import Affine
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", default="scratch/dem")
    ap.add_argument("--out", default="external/dem")
    ap.add_argument("--float-out", default="")
    ap.add_argument("--footprint", default="",
                    help="GeoTIFF on the official grid whose NaN cells are outside the footprint "
                         "(e.g. a committed submission); those cells are stored as nodata")
    args = ap.parse_args(argv)
    files = sorted(glob.glob(f"{args.inp}/**/*.npz", recursive=True))
    logs = []
    for j in sorted(glob.glob(f"{args.inp}/**/shard_*.json", recursive=True)):
        logs += json.loads(Path(j).read_text())
    if not files:
        raise SystemExit("no tile outputs found")
    der = derive(mosaic(files))
    if args.footprint:
        with rasterio.open(args.footprint) as fp:
            if fp.shape != DF.GRID_SHAPE or tuple(fp.transform)[:6] != DF.GRID_TRANSFORM:
                raise SystemExit("footprint raster is not on the official grid")
            outside = ~np.isfinite(fp.read(1))
        for n in der:
            der[n] = np.where(outside, np.nan, der[n]).astype(np.float32)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    prof = dict(driver="GTiff", width=DF.GRID_SHAPE[1], height=DF.GRID_SHAPE[0],
                crs=DF.GRID_CRS, transform=Affine(*DF.GRID_TRANSFORM), tiled=True,
                blockxsize=512, blockysize=512, compress="deflate", zlevel=9, predictor=2)
    tif = out / "lidar_scarp_features_u8.tif"
    with rasterio.open(tif, "w", count=len(BANDS), dtype="uint8", nodata=0, **prof) as dst:
        for i, n in enumerate(BANDS, 1):
            dst.write(quantise(n, der[n]), i)
            dst.set_band_description(i, n)
    if args.float_out:
        with rasterio.open(args.float_out, "w", count=len(BANDS), dtype="float32",
                           nodata=np.nan, **prof) as dst:
            for i, n in enumerate(BANDS, 1):
                dst.write(der[n].astype(np.float32), i)
                dst.set_band_description(i, n)
    status = {}
    for e in logs:
        status[e.get("status", "?")] = status.get(e.get("status", "?"), 0) + 1
    report = dict(
        product=str(tif), bands=BANDS, quantisation=QUANT,
        quantisation_rule="q = 1 + round(254 * t(clip(x/xmax,0,1))), t in {sqrt, linear}; 0 = no lidar",
        channels_2m=[dict(name=n, aggregation=a, meaning=m) for n, a, m in DF.CHANNELS],
        work_resolution_m=DF.WORK_RES, tiles_total=len(logs), tile_status=status,
        grid_cells_with_lidar=int(np.sum(np.nan_to_num(der["valid"]) > 0.5)),
        source="USGS 3DEP 1 m DEM tiles listed in knowledge/dem_tiles.json (official bucket URLs)",
        rights="USGS 3DEP products are available without use restrictions; acknowledge 'Map services and data available from U.S. Geological Survey, National Geospatial Program.'",
        caveats=["uncalibrated terrain descriptors, not fault detections",
                 "roads, channels, terrace risers, paleo-shorelines, landslides and mines also create steps",
                 "tile list is an OCR-recovered inventory of the competition PDF, not the login-walled CSV",
                 "NAD83(2011) UTM tiles aggregated onto WGS84 UTM 11N; ~1-2 m datum offset is negligible at 100 m"],
    )
    (out / "lidar_scarp_features.json").write_text(json.dumps(report, indent=1))
    slim = [{k: e.get(k) for k in ("tile", "status", "bytes", "sha256", "crs", "native_res",
                                   "overviews", "window", "valid_cells", "seconds", "error")} for e in logs]
    (out / "lidar_tile_log.json").write_text(json.dumps(slim, indent=0))
    print(json.dumps({k: report[k] for k in ("tiles_total", "tile_status", "grid_cells_with_lidar")}))


if __name__ == "__main__":
    main()
