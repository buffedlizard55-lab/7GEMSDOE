"""Enumerate official USGS 3DEP 1 m DEM tiles that can fill lidar coverage gaps.

Why this exists
---------------
``external/dem/lidar_scarp_features_u8.tif`` covers 3,894,460 of the 5,167,373
in-footprint cells (24.63% gap).  That gap caps the recall of every lidar-based
arm, and 20.5% of the published fault catalogue sits inside it.  The session-7
next-step list therefore makes "gap-first lidar: enumerate additional official
3DEP projects/tiles for the 24.6% product gap" priority #1.

The tile list currently in the repository comes from an OCR pass over the
competition's scanned DEM-links PDF and its own provenance note says it covers
only ~78.5% of the template footprint.  This script does **not** trust that
list: it asks the authoritative USGS 3DEP public bucket
(``prd-tnm.s3.amazonaws.com``, ``StagedProducts/Elevation/1m/Projects/``) which
tiles exist for projects in the region, converts each tile identifier to its
true UTM footprint, and keeps only tiles that intersect cells with no lidar.

Evidence produced
-----------------
* ``--out``  JSON record list in the same schema ``scripts/dem_features.py``
  already consumes (``filename``, ``url``, ``tile``, ``project``, plus measured
  bucket ``bytes`` and the computed ``window`` / ``gap_cells``).
* ``--log``  per-project listing log (HTTP status, key counts, page counts) so a
  human can audit exactly which authoritative listing produced each tile.

Irregularities are recorded, never silently dropped: projects whose listings
could not be read, tile identifiers that do not parse, and tiles that already
appear in the processed list are all reported.  Nothing here is a claim that a
tile contains usable data -- that is only known after the extract stage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

# Imported for the grid definition and the shared window helper only.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dem_features as DF  # noqa: E402

BUCKET = "https://prd-tnm.s3.amazonaws.com"
PROJECT_PREFIX = "StagedProducts/Elevation/1m/Projects/"
# Region keywords. The competition footprint is NW Nevada + adjacent E California;
# tile identifiers carry the UTM zone and 10 km cell, so the keyword filter only
# decides which project listings are read -- geometry decides what is kept.
REGION_KEYWORDS = ("NV", "CA", "Sierra", "Tahoe", "GreatBasin", "Humboldt", "Walker",
                   "Pyramid", "EarthMRI", "Lassen", "Carson")
TILE_RE = re.compile(r"^USGS_1M_(\d{2})_x(\d+)y(\d+)_(.+)$")
# 3DEP 1 m project tiles are distributed in NAD83 UTM (EPSG:269xx); the naming
# does not encode the datum. A 1-2 m datum offset is irrelevant at 100 m cells,
# and the extract stage reprojects with the tile's real CRS anyway.
ZONE_CRS = {10: "EPSG:26910", 11: "EPSG:26911", 12: "EPSG:26912"}


def http_get(url: str, tries: int = 4, timeout: int = 60) -> bytes:
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001 - recorded by the caller
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url}: {last}")


def list_prefix(prefix: str, delimiter: str | None = None, max_pages: int = 40) -> dict:
    """List one S3 prefix, returning keys, common prefixes and sizes."""
    keys, prefixes, pages, truncated = [], [], 0, True
    token = None
    while truncated and pages < max_pages:
        url = f"{BUCKET}/?list-type=2&prefix={prefix}&max-keys=1000"
        if delimiter:
            url += f"&delimiter={delimiter}"
        if token:
            url += f"&continuation-token={token}"
        body = http_get(url)
        pages += 1
        import xml.etree.ElementTree as ET

        root = ET.fromstring(body)
        ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        for c in root.findall("s3:Contents", ns):
            keys.append((c.findtext("s3:Key", default="", namespaces=ns),
                         int(c.findtext("s3:Size", default="0", namespaces=ns))))
        for p in root.findall("s3:CommonPrefixes", ns):
            prefixes.append(p.findtext("s3:Prefix", default="", namespaces=ns))
        truncated = (root.findtext("s3:IsTruncated", default="false", namespaces=ns) == "true")
        tok = root.find("s3:NextContinuationToken", ns)
        token = tok.text if tok is not None else None
        if token is None:
            truncated = False
    return {"keys": keys, "prefixes": prefixes, "pages": pages, "truncated": truncated}


def parse_tile(stem: str):
    """USGS_1M_11_x45y443_NV_EastCentral_2021_D21 -> (zone, x, y, project).

    ``x`` and ``y`` are the 10 km indices in the tile identifier, *not* both
    lower-left UTM coordinates.  Measured against the 706 windows recorded in
    ``external/dem/lidar_tile_log.json``: the tile spans
    easting ``[x*10km, (x+1)*10km]`` and northing ``[y*10km - 10km, y*10km]``.
    Reversing that convention shifts a tile by a full 10 km cell, so the mapping
    is pinned by ``tests/test_dem_gap.py`` against every recorded window.
    """
    m = TILE_RE.match(stem)
    if not m:
        return None
    zone = int(m.group(1))
    if zone not in ZONE_CRS:
        return None
    return zone, int(m.group(2)), int(m.group(3)), m.group(4)


def tile_bounds_utm(stem: str):
    """(crs, left, bottom, right, top) in the tile's own UTM zone, or None."""
    parsed = parse_tile(stem)
    if parsed is None:
        return None
    zone, x, y, _ = parsed
    return ZONE_CRS[zone], x * 10000.0, (y - 1) * 10000.0, (x + 1) * 10000.0, y * 10000.0


def tile_window(stem: str, margin_cells: int = 2):
    """Official-grid window (r0, c0, h, w) a 10 km UTM tile can touch, or None.

    ``margin_cells`` absorbs the datum/zone-rotation shift of the bounding box
    when a tile is filed in a UTM zone other than the grid's (measured worst case
    over the committed log: 1 cell at 100 m, i.e. 100 m).
    """
    parsed = tile_bounds_utm(stem)
    if parsed is None:
        return None
    crs, left, bottom, right, top = parsed
    from rasterio.transform import Affine
    from rasterio.warp import transform_bounds

    b = transform_bounds(crs, DF.GRID_CRS, left, bottom, right, top, densify_pts=25)
    m = margin_cells * 100.0
    return DF.grid_window_for_bounds(b[0] - m, b[1] - m, b[2] + m, b[3] + m)


def gap_mask(base_path: str, footprint_path: str) -> np.ndarray:
    """Cells inside the footprint that carry no lidar in the current product."""
    import rasterio

    with rasterio.open(footprint_path) as s:
        fp = s.read(1)
    with rasterio.open(base_path) as s:
        base = s.read()
        valid = s.descriptions.index("valid") if "valid" in (s.descriptions or ()) else s.count - 1
        have = base[valid] > 0
    if fp.shape != have.shape:
        raise ValueError(f"shape mismatch: footprint {fp.shape} vs base {have.shape}")
    return (fp >= 0) & ~have


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="external/dem/lidar_scarp_features_u8.tif")
    ap.add_argument("--footprint", default="downloads/submission.tif")
    ap.add_argument("--processed", default="knowledge/dem_tiles.json")
    ap.add_argument("--out", default="knowledge/dem_tiles_gap.json")
    ap.add_argument("--log", default="external/dem/s3_listing_log.json")
    ap.add_argument("--max-records", type=int, default=0, help="0 = no cap")
    args = ap.parse_args(argv)

    t0 = time.time()
    gap = gap_mask(args.base, args.footprint)
    footprint_px = int((gap | np.zeros_like(gap)).sum())  # kept for symmetry in the log
    gap_px = int(gap.sum())
    print(json.dumps({"stage": "gap", "gap_px": gap_px, "seconds": round(time.time() - t0, 1)}))

    processed = set()
    try:
        for r in json.loads(Path(args.processed).read_text()).get("records", []):
            processed.add(Path(r.get("filename") or r.get("tile", "")).stem)
    except FileNotFoundError:
        pass

    log: dict = {"bucket": BUCKET, "prefix": PROJECT_PREFIX, "region_keywords": list(REGION_KEYWORDS),
                 "gap_cells": gap_px, "footprint_cells": footprint_px, "projects": [], "problems": []}

    recs, seen = [], set()
    # 1. Which projects exist at all?
    top = list_prefix(PROJECT_PREFIX, delimiter="/")
    all_projects = [p[len(PROJECT_PREFIX):].rstrip("/") for p in top["prefixes"]]
    log["projects_total_in_bucket"] = len(all_projects)
    log["project_listing_pages"] = top["pages"]
    log["project_listing_truncated"] = bool(top["truncated"])
    candidates = [p for p in all_projects if any(k.lower() in p.lower() for k in REGION_KEYWORDS)]
    log["candidate_projects"] = len(candidates)
    log["skipped_projects"] = sorted(set(all_projects) - set(candidates))

    for proj in sorted(candidates):
        entry = {"project": proj}
        try:
            listing = list_prefix(f"{PROJECT_PREFIX}{proj}/TIFF/")
            entry["keys"] = len(listing["keys"])
            entry["pages"] = listing["pages"]
            entry["truncated"] = bool(listing["truncated"])
            for key, size in listing["keys"]:
                if not key.lower().endswith(".tif"):
                    continue
                stem = Path(key).stem
                if stem in seen:
                    continue
                win = tile_window(stem)
                if win is None:
                    entry.setdefault("unparsed", []).append(stem)
                    continue
                r0, c0, h, w = win
                g = int(gap[r0:r0 + h, c0:c0 + w].sum())
                if g <= 0:
                    continue
                seen.add(stem)
                recs.append({"tile": stem, "filename": Path(key).name,
                             "url": f"{BUCKET}/{key}", "bytes": size, "project": proj,
                             "window": [r0, c0, h, w], "gap_cells": g,
                             "already_processed": stem in processed})
        except Exception as exc:  # noqa: BLE001
            entry["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            log["problems"].append({"project": proj, "error": entry["error"]})
        log["projects"].append(entry)

    recs.sort(key=lambda r: (-r["gap_cells"], r["tile"]))
    log["tiles_touching_gap"] = len(recs)
    log["tiles_touching_gap_not_processed"] = sum(1 for r in recs if not r["already_processed"])
    log["new_gap_cells_covered"] = int(sum(r["gap_cells"] for r in recs if not r["already_processed"]))
    if args.max_records:
        keep = [r for r in recs if not r["already_processed"]][: args.max_records]
        keep += [r for r in recs if r["already_processed"]]
        recs = keep
    out = {
        "description": ("Additional official USGS 3DEP 1 m DEM tiles that intersect cells which have no "
                        "lidar in external/dem/lidar_scarp_features_u8.tif. Produced by scripts/dem_enumerate.py "
                        "from the authoritative USGS 3DEP public bucket listing (ListObjectsV2)."),
        "method": "ListObjectsV2 project listing -> tile id -> UTM footprint -> official grid window -> gap intersection",
        "bucket": BUCKET,
        "datum_assumption": ("tile naming encodes zone only; NAD83 UTM (EPSG:269xx) assumed for the footprint "
                             "test, the extract stage reprojects with each tile's real CRS"),
        "gap_cells_before": gap_px,
        "n_records": len(recs),
        "elapsed_seconds": round(time.time() - t0, 1),
        "records": recs,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    Path(args.log).parent.mkdir(parents=True, exist_ok=True)
    Path(args.log).write_text(json.dumps(log, indent=1))
    print(json.dumps({k: out[k] for k in ("n_records", "gap_cells_before", "elapsed_seconds")}))
    print(json.dumps({k: log[k] for k in ("projects_total_in_bucket", "candidate_projects",
                                          "tiles_touching_gap", "tiles_touching_gap_not_processed",
                                          "new_gap_cells_covered", "problems")})[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
