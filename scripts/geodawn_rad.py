"""GeoDAWN radiometric grids -> official-grid product (session 5, new H9).

H9 (radiometric lineament hypothesis): the GeoDAWN survey collected
high-resolution aeroradiometric data (K, Th, U, total count) that are NOT
in the 19-band training stack, but faults offset lithology, focus
alteration and juxtapose soils -- all of which modulate surface
gamma-ray response. Radiometric edges are therefore an independent,
official, competition-collected fault-localisation signal.

Source (verified): USGS data release DOI 10.5066/P93LGLVQ
(Glen & Earney 2024), ScienceBase item 657e1d85d34e23d3533209f7,
"GeoDAWN: Airborne magnetic and radiometric surveys of the northwestern
Great Basin, Nevada and California". The release holds magnetic AND
radiometric grids + line data + ternary map + contractor report.
GDR 1591 mirrors the landing record (CC BY 4.0 display; USGS source is
public domain -- verify asset terms on the runner and record them).

What this script does (runs on GitHub Actions; the sandbox cannot reach
ScienceBase):
  1. queries the ScienceBase JSON API for the item's file list,
  2. selects radiometric grid GeoTIFFs by filename pattern
     (K / Th / U / total-count / dose), FAILING CLOSED with the observed
     file list if nothing matches (names are NOT assumed),
  3. downloads, reprojects each grid to the official competition grid
     (EPSG:32611, 100 m, 3292x3730, bilinear), and
  4. writes external/geodawn_rad/geodawn_rad_u8.tif (uint8, <=4 bands) +
     external/geodawn_rad/geodawn_rad.json manifest with source URLs,
     sha256s, observed file list and rights notes.

Hermetic core (tested in tests/test_geodawn_rad.py): select_rad_files()
and quantise() are pure functions over a file-listing dict / numpy array.

Note: K/Th/U respond to the top ~0.5-1 m of soil/rock and to moisture,
vegetation and survey altitude -- they are lithology/alteration proxies,
not fault detectors. Any downstream use must carry altitude-mask and
acquisition-block controls (the release ships an altitude-reliability
mask for other surveys; check whether GeoDAWN does too).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from paths import TEMPLATE_TIF  # noqa: E402

SCIENCEBASE_ITEM = "657e1d85d34e23d3533209f7"
SCIENCEBASE_API = ("https://www.sciencebase.gov/catalog/item/"
                   + SCIENCEBASE_ITEM + "?format=json")
SCIENCEBASE_FILE = ("https://www.sciencebase.gov/catalog/file/get/"
                    + SCIENCEBASE_ITEM)
DOI = "10.5066/P93LGLVQ"
OUT_DIR = ROOT / "external" / "geodawn_rad"

# Filename patterns for radiometric grids. Ordered preference within each
# channel; matching is case-insensitive on the basename. Observed names are
# recorded in the manifest; if none match, the job fails closed.
CHANNEL_PATTERNS = {
    "K": [r"k_?pct", r"potassium", r"\bk\b.*\.tif$", r"k40"],
    "Th": [r"eth", r"thorium", r"\bth\b.*\.tif$"],
    "U": [r"eu\b", r"uranium"],
    "TC": [r"total_?count", r"\btc\b", r"dose"],
}
GRID_EXTS = (".tif", ".tiff", ".grd", ".gxf")


def select_rad_files(files: list[dict]) -> dict:
    """Pick one grid URL per radiometric channel from a ScienceBase listing.

    files: [{'name': str, 'url': str, 'size': int}]. Returns
    {channel: file_dict}. Raises ValueError with the observed names when a
    channel has no match (fail closed; caller logs the full listing).
    """
    chosen: dict[str, dict] = {}
    missing: list[str] = []
    for channel, patterns in CHANNEL_PATTERNS.items():
        hit = None
        for pat in patterns:
            for f in files:
                name = f.get("name", "")
                if not name.lower().endswith(GRID_EXTS):
                    continue
                if re.search(pat, name, re.IGNORECASE):
                    hit = f
                    break
            if hit is not None:
                break
        if hit is None:
            missing.append(channel)
        else:
            chosen[channel] = hit
    if missing:
        observed = sorted(f.get("name", "?") for f in files)
        raise ValueError(f"no radiometric grid matched channels {missing}; "
                         f"observed {len(observed)} files: {observed[:40]}")
    return chosen


def quantise(x: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Robust uint8: 1..255 over the 1st..99th percentile; 0 = nodata."""
    q = np.zeros(x.shape, np.uint8)
    v = x[mask]
    if v.size == 0:
        return q
    lo, hi = np.percentile(v, (1.0, 99.0))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return q
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    q[mask] = (1 + np.round(254 * t[mask])).astype(np.uint8)
    return q


def official_grid():
    with rasterio.open(TEMPLATE_TIF) as src:
        return src.shape, src.transform, str(src.crs), src.read(1)


def fetch_bytes(url: str, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "7GEMSDOE-rad/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"querying {SCIENCEBASE_API}", flush=True)
    item = json.loads(fetch_bytes(SCIENCEBASE_API).decode("utf-8"))
    files = [{"name": f.get("name", ""), "size": f.get("size", 0),
              "url": f.get("url", "") or (SCIENCEBASE_FILE + "?name=" + f.get("name", ""))}
             for f in item.get("files", [])]
    print(f"observed {len(files)} files", flush=True)
    try:
        chosen = select_rad_files(files)
    except ValueError as e:
        (args.out / "observed_files.json").write_text(
            json.dumps({"item": SCIENCEBASE_ITEM, "doi": DOI,
                        "files": sorted(f["name"] for f in files)}, indent=1))
        raise SystemExit(f"FAIL CLOSED: {e}")

    shape, transform, crs, template = official_grid()
    footprint = np.isfinite(template)
    bands, manifest_files = [], {}
    for channel, f in chosen.items():
        print(f"downloading {channel}: {f['name']} ({f['size']} B)", flush=True)
        raw = fetch_bytes(f["url"])
        sha = hashlib.sha256(raw).hexdigest()
        safe_name = f["name"].replace("/", "_")
        tmp = args.out / f"_dl_{channel}_{safe_name}"
        tmp.write_bytes(raw)
        with rasterio.open(tmp) as src:
            src_arr = src.read(1)
            src_mask = src.read_masks(1) > 0
            dst = np.zeros(shape, np.float32)
            dst_mask = np.zeros(shape, np.uint8)
            reproject(src_arr, dst, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=transform, dst_crs=crs,
                      resampling=Resampling.bilinear)
            reproject((src_mask).astype(np.uint8), dst_mask,
                      src_transform=src.transform, src_crs=src.crs,
                      dst_transform=transform, dst_crs=crs,
                      resampling=Resampling.nearest)
        tmp.unlink()
        valid = (dst_mask > 0) & footprint
        bands.append(quantise(dst, valid))
        manifest_files[channel] = {"name": f["name"], "url": f["url"],
                                   "sha256": sha, "valid_px": int(valid.sum())}
    arr = np.stack(bands).astype(np.uint8)
    out_tif = args.out / "geodawn_rad_u8.tif"
    with rasterio.open(out_tif, "w", driver="GTiff", height=shape[0],
                       width=shape[1], count=len(bands), dtype="uint8",
                       crs=crs, transform=transform, compress="lzw",
                       nodata=0) as dst:
        dst.descriptions = tuple(chosen.keys())
        dst.write(arr)
    manifest = {
        "product": "external/geodawn_rad/geodawn_rad_u8.tif",
        "channels": list(chosen.keys()),
        "doi": DOI,
        "sciencebase_item": SCIENCEBASE_ITEM,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "rights": "USGS data release (public domain); GDR mirror displays "
                  "CC BY 4.0 -- verify asset terms and retain attribution.",
        "quantisation": "uint8 1..255 over per-channel 1st..99th pct; 0=nodata",
        "caveats": [
            "gamma rays sample the top ~0.5-1 m; moisture/vegetation/altitude modulate response",
            "check the release for an altitude-reliability mask before modelling",
            "lithology/alteration proxy, not a fault detector",
        ],
        "files": manifest_files,
    }
    (args.out / "geodawn_rad.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
