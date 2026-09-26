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
  2. verifies and downloads the official Area 1/Area 2 GeoTIFF ZIPs by
     recorded size and ScienceBase MD5; safe-lists ZIP members and selects
     K / Th / U / total-count GeoTIFFs, failing closed on ambiguity,
  3. reprojects both areas to the official grid (bilinear), with higher-
     resolution Area 1 taking precedence in overlap, and
  4. writes external/geodawn_rad/geodawn_rad_u8.tif (uint8, four bands) +
     a manifest with archive hashes, member names, source/output grid,
     output SHA-256 and rights/caveat notes.

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
import stat
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

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
    "K": [r"k_?pct", r"potassium", r"(^|[_/\\])k([_.-]|$)", r"k40"],
    "Th": [r"eth", r"thorium", r"(^|[_/\\])th([_.-]|$)"],
    "U": [r"eu\b", r"uranium", r"(^|[_/\\])u([_.-]|$)"],
    "TC": [r"total_?count", r"(^|[_/\\])tc([_.-]|$)", r"dose"],
}
GRID_EXTS = (".tif", ".tiff", ".grd", ".gxf")


def select_rad_files(files: list[dict]) -> dict:
    """Select one unambiguous grid per radiometric channel from ScienceBase.

    Filename patterns are preference-ordered. Multiple candidates at the
    winning preference level are an irregularity, not an invitation to depend
    on API listing order, so the caller fails closed and records the listing.
    """
    chosen: dict[str, dict] = {}
    missing: list[str] = []
    for channel, patterns in CHANNEL_PATTERNS.items():
        hit = None
        for pat in patterns:
            matches = [f for f in files
                       if str(f.get("name", "")).lower().endswith(GRID_EXTS)
                       and re.search(pat, str(f.get("name", "")), re.IGNORECASE)]
            if len(matches) > 1:
                names = sorted(str(f.get("name", "?")) for f in matches)
                raise ValueError(f"ambiguous {channel} candidates for {pat!r}: {names}")
            if matches:
                hit = matches[0]
                break
        if hit is None:
            missing.append(channel)
        else:
            chosen[channel] = hit
    if missing:
        observed = sorted(f.get("name", "?") for f in files)
        raise ValueError(f"no radiometric grid matched channels {missing}; "
                         f"observed {len(observed)} files: {observed[:40]}")
    identities = [(str(item.get("url", "")), str(item.get("name", "")))
                  for item in chosen.values()]
    if len(set(identities)) != len(identities):
        raise ValueError("one source grid matched multiple radiometric channels")
    return chosen


def select_tiff_archives(files: list[dict]) -> dict[int, dict]:
    """Select the official Area 1/2 GeoTIFF package zips, failing on ambiguity."""
    chosen = {}
    for area in (1, 2):
        expected = f"22103_area{area}_tiffs.zip"
        matches = [f for f in files
                   if str(f.get("name", "")).strip().casefold() == expected.casefold()]
        if len(matches) != 1:
            names = sorted(str(f.get("name", "?")) for f in files)
            raise ValueError(
                f"expected one {expected}; found {len(matches)}; observed {names[:40]}")
        chosen[area] = matches[0]
    return chosen


def inspect_tiff_zip(archive: zipfile.ZipFile, max_uncompressed: int = 8 << 30) -> list[dict]:
    """List safe TIFF members without extracting untrusted archive paths."""
    infos = archive.infolist()
    seen = set()
    total = 0
    rasters = []
    for info in infos:
        posix, windows = PurePosixPath(info.filename), PureWindowsPath(info.filename)
        if (posix.is_absolute() or windows.is_absolute() or windows.drive
                or ".." in posix.parts or ".." in windows.parts):
            raise ValueError(f"unsafe GeoDAWN archive path: {info.filename!r}")
        normalized = posix.as_posix().casefold()
        if normalized in seen:
            raise ValueError(f"duplicate GeoDAWN archive path: {info.filename!r}")
        seen.add(normalized)
        if stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError(f"symbolic link not allowed in GeoDAWN archive: {info.filename!r}")
        total += info.file_size
        if total > max_uncompressed:
            raise ValueError(f"GeoDAWN archive expands beyond {max_uncompressed} bytes")
        if not info.is_dir() and info.filename.lower().endswith((".tif", ".tiff")):
            rasters.append({"name": info.filename, "size": info.file_size,
                            "_zip_info": info})
    return rasters


def download_to(url: str, destination: Path, expected_size: int = 0,
                expected_md5: str = "", timeout: int = 300) -> dict:
    """Stream an official file to disk and verify item size/MD5 when supplied."""
    import hashlib

    req = urllib.request.Request(url, headers={"User-Agent": "7GEMSDOE-rad/1.0"})
    md5, sha256, size = hashlib.md5(), hashlib.sha256(), 0
    with urllib.request.urlopen(req, timeout=timeout) as response, destination.open("wb") as out:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            md5.update(chunk)
            sha256.update(chunk)
            out.write(chunk)
    if expected_size and size != int(expected_size):
        raise ValueError(f"download size mismatch: expected {expected_size}, got {size}")
    if expected_md5 and md5.hexdigest().lower() != expected_md5.lower():
        raise ValueError("download MD5 does not match official ScienceBase item checksum")
    return {"size": size, "md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def _safe_basename(name: str) -> str:
    basename = str(name).replace("\\", "/").rsplit("/", 1)[-1]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", basename)
    if safe in {"", ".", ".."}:
        raise ValueError(f"unsafe source filename: {name!r}")
    return safe


def warp_to_grid(path: Path, shape, transform, crs):
    """Bilinear data + nearest mask to the official competition grid."""
    with rasterio.open(path) as src:
        if src.crs is None:
            raise ValueError(f"radiometric grid has no CRS: {path.name}")
        source_grid = {
            "width": src.width,
            "height": src.height,
            "crs": str(src.crs),
            "resolution": list(src.res),
            "transform": list(src.transform)[:6],
            "dtype": src.dtypes[0],
            "nodata": src.nodata,
        }
        src_arr = src.read(1)
        src_mask = src.read_masks(1) > 0
        dst = np.zeros(shape, np.float32)
        dst_mask = np.zeros(shape, np.uint8)
        reproject(src_arr, dst, src_transform=src.transform, src_crs=src.crs,
                  src_nodata=src.nodata, dst_transform=transform, dst_crs=crs,
                  dst_nodata=np.nan, resampling=Resampling.bilinear)
        reproject(src_mask.astype(np.uint8), dst_mask,
                  src_transform=src.transform, src_crs=src.crs,
                  dst_transform=transform, dst_crs=crs,
                  resampling=Resampling.nearest)
    valid = (dst_mask > 0) & np.isfinite(dst)
    return dst, valid, source_grid


def quantise(x: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Robust uint8: 1..255 over finite valid pixels' 1st..99th percentiles."""
    x = np.asarray(x)
    mask = np.asarray(mask, dtype=bool)
    if x.ndim != 2 or mask.shape != x.shape:
        raise ValueError("aligned 2D data and boolean mask required")
    finite = mask & np.isfinite(x)
    q = np.zeros(x.shape, np.uint8)
    v = x[finite]
    if v.size == 0:
        return q
    lo, hi = np.percentile(v, (1.0, 99.0))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return q
    t = np.clip((x[finite] - lo) / (hi - lo), 0, 1)
    q[finite] = (1 + np.round(254 * t)).astype(np.uint8)
    return q


def official_grid():
    with rasterio.open(TEMPLATE_TIF) as src:
        return src.shape, src.transform, str(src.crs), src.read(1)


def fetch_bytes(url: str, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "7GEMSDOE-rad/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"querying {SCIENCEBASE_API}", flush=True)
    item = json.loads(fetch_bytes(SCIENCEBASE_API).decode("utf-8"))
    files = [{
        "name": f.get("name", ""),
        "size": f.get("size", 0),
        "url": f.get("url", "") or (SCIENCEBASE_FILE + "?name=" + f.get("name", "")),
        "md5": (f.get("checksum") or {}).get("value", ""),
    } for f in item.get("files", [])]
    print(f"observed {len(files)} files", flush=True)
    shape, transform, crs, template = official_grid()
    footprint = np.isfinite(template)
    observed_members = {}
    archive_records = {}
    selected_records = {}
    mosaics = {channel: np.zeros(shape, np.float32) for channel in CHANNEL_PATTERNS}
    mosaic_masks = {channel: np.zeros(shape, bool) for channel in CHANNEL_PATTERNS}

    try:
        top_level_grids = [f for f in files
                           if str(f.get("name", "")).lower().endswith(GRID_EXTS)]
        if top_level_grids:
            # Retain support for a future ScienceBase layout with direct grids.
            chosen = select_rad_files(top_level_grids)
            for channel, source in chosen.items():
                with tempfile.TemporaryDirectory(prefix="geodawn-rad-", dir=args.out) as td:
                    path = Path(td) / _safe_basename(source["name"])
                    hashes = download_to(source["url"], path, source.get("size", 0),
                                         source.get("md5", ""))
                    values, mask, source_grid = warp_to_grid(path, shape, transform, crs)
                mosaics[channel][mask] = values[mask]
                mosaic_masks[channel] |= mask
                selected_records[channel] = [{
                    "area": "item",
                    "name": source["name"],
                    "sha256": hashes["sha256"],
                    "source_grid": source_grid,
                    "valid_px": int(mask.sum()),
                }]
        else:
            archives = select_tiff_archives(files)
            with tempfile.TemporaryDirectory(prefix="geodawn-rad-", dir=args.out) as td:
                temp_root = Path(td)
                for area in (2, 1):  # lower-resolution area first; Area 1 wins overlap
                    source = archives[area]
                    archive_path = temp_root / source["name"]
                    print(f"downloading Area {area} TIFF archive ({source['size']} B)",
                          flush=True)
                    hashes = download_to(source["url"], archive_path,
                                         source.get("size", 0), source.get("md5", ""))
                    archive_records[area] = {"name": source["name"], **hashes}
                    with zipfile.ZipFile(archive_path) as archive:
                        members = inspect_tiff_zip(archive)
                        observed_members[area] = [
                            {"name": member["name"], "size": member["size"]}
                            for member in members
                        ]
                        diagnostic = {
                            "status": "archives_inspected",
                            "item": SCIENCEBASE_ITEM,
                            "doi": DOI,
                            "observed_files": [
                                {"name": str(f.get("name", "")),
                                 "size": int(f.get("size", 0) or 0)} for f in files
                            ],
                            "observed_tiff_members": observed_members,
                        }
                        (args.out / "observed_files.json").write_text(
                            json.dumps(diagnostic, indent=1, ensure_ascii=False) + "\n")
                        chosen = select_rad_files(members)
                        for channel, member in chosen.items():
                            info = member["_zip_info"]
                            raster_path = temp_root / f"area{area}_{channel}_{_safe_basename(info.filename)}"
                            with archive.open(info) as src, raster_path.open("wb") as dst:
                                while True:
                                    chunk = src.read(1 << 20)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
                            values, mask, source_grid = warp_to_grid(
                                raster_path, shape, transform, crs)
                            # Area 1 is higher resolution (50 m vs 100 m per the
                            # USGS readme) and intentionally overrides Area 2.
                            mosaics[channel][mask] = values[mask]
                            mosaic_masks[channel] |= mask
                            selected_records.setdefault(channel, []).append({
                                "area": area,
                                "archive": source["name"],
                                "member": info.filename,
                                "member_size": info.file_size,
                                "source_grid": source_grid,
                                "valid_px": int(mask.sum()),
                            })
                            raster_path.unlink()

    except Exception as exc:
        diagnostic = {
            "status": "review_required",
            "item": SCIENCEBASE_ITEM,
            "doi": DOI,
            "error": f"{type(exc).__name__}: {exc}",
            "observed_files": [
                {"name": str(f.get("name", "")),
                 "size": int(f.get("size", 0) or 0)} for f in files
            ],
            "observed_tiff_members": observed_members,
            "archive_hashes": archive_records,
        }
        (args.out / "observed_files.json").write_text(
            json.dumps(diagnostic, indent=1, ensure_ascii=False) + "\n")
        raise SystemExit(f"FAIL CLOSED: {type(exc).__name__}: {exc}") from exc

    bands, manifest_files = [], {}
    for channel in CHANNEL_PATTERNS:
        valid = mosaic_masks[channel] & footprint & np.isfinite(mosaics[channel])
        bands.append(quantise(mosaics[channel], valid))
        manifest_files[channel] = {
            "sources": selected_records[channel],
            "valid_px": int(valid.sum()),
        }
    arr = np.stack(bands).astype(np.uint8)
    out_tif = args.out / "geodawn_rad_u8.tif"
    with rasterio.open(out_tif, "w", driver="GTiff", height=shape[0],
                       width=shape[1], count=len(bands), dtype="uint8",
                       crs=crs, transform=transform, compress="lzw",
                       nodata=0) as dst:
        dst.descriptions = tuple(CHANNEL_PATTERNS.keys())
        dst.write(arr)
    manifest = {
        "product": "external/geodawn_rad/geodawn_rad_u8.tif",
        "product_sha256": sha256_file(out_tif),
        "grid": {
            "width": shape[1],
            "height": shape[0],
            "crs": crs,
            "transform": list(transform)[:6],
            "dtype": "uint8",
            "nodata": 0,
        },
        "channels": list(CHANNEL_PATTERNS.keys()),
        "doi": DOI,
        "sciencebase_item": SCIENCEBASE_ITEM,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "archives": archive_records,
        "archive_member_listing": observed_members,
        "priority_rule": "Area 1 overrides Area 2 where they overlap; Area 1 is 50 m and Area 2 100 m per USGS readme.",
        "rights": "USGS data release; retain USGS citation/attribution and verify terms for each downloaded asset before redistribution.",
        "quantisation": "uint8 1..255 over per-channel 1st..99th pct after area mosaic; 0=nodata",
        "caveats": [
            "gamma rays sample the top ~0.5-1 m; moisture/vegetation/altitude modulate response",
            "USGS item describes different flight specifications and acquisition blocks; spatial/block controls are needed",
            "lithology/alteration proxy, not a fault detector",
        ],
        "files": manifest_files,
    }
    (args.out / "geodawn_rad.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
