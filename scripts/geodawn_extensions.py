"""Build overlooked official GeoDAWN ratio/upward-continuation channels.

The official Area 1/2 GeoTIFF archives already used for K/Th/U/total count also
contain contractor-computed Th/K, U/K and U/Th ratio grids and magnetic TMI
upward-continued to 150 m. These four grids are absent from the supplied
19-band descriptions and from ``geodawn_rad_u8.tif``.

The ratio products are scientifically preferable to calculating ratios from
our independently quantised K/Th/U bytes: the GeoDAWN ReadMe defines the source
profile channels and the contractor generated these grids from physical source
measurements. This script still stores robust uint8 ranks for compact modelling;
it does not claim the stored bytes retain physical ratio units.

Source: USGS GeoDAWN DOI 10.5066/P93LGLVQ, ScienceBase item
657e1d85d34e23d3533209f7. The runner verifies ScienceBase-listed archive sizes
and MD5 checksums, safe-lists members, requires exact observed member names,
warps Area 2 then higher-resolution Area 1 onto the competition grid, and logs
all source/output hashes. No submission file is generated.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

import geodawn_rad as GD

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "external" / "geodawn_extensions"
CHANNELS = ("ThK", "UK", "UTh", "TMI_up150")
MEMBER_STEMS = {
    "ThK": "thk",
    "UK": "uk",
    "UTh": "uth",
    "TMI_up150": "upcont_tmi150",
}


def select_extension_members(members: list[dict], area: int) -> dict[str, dict]:
    """Select exact contractor TIFF names; fail on absent/duplicate members."""
    if area not in (1, 2):
        raise ValueError(f"unsupported GeoDAWN area: {area}")
    selected = {}
    observed = [str(member.get("name", "")) for member in members]
    for channel, stem in MEMBER_STEMS.items():
        expected = f"22103_{stem}_a{area}.tif"
        matches = [member for member in members
                   if Path(str(member.get("name", "")).replace("\\", "/")).name.casefold()
                   == expected.casefold()]
        if len(matches) != 1:
            raise ValueError(
                f"expected one exact {expected} for {channel}; found {len(matches)}; "
                f"observed {sorted(observed)[:40]}")
        selected[channel] = matches[0]
    identities = [str(member["name"]).casefold() for member in selected.values()]
    if len(set(identities)) != len(identities):
        raise ValueError("one GeoDAWN member matched multiple extension channels")
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"querying {GD.SCIENCEBASE_API}", flush=True)
    item = json.loads(GD.fetch_bytes(GD.SCIENCEBASE_API).decode("utf-8"))
    files = [{
        "name": source.get("name", ""),
        "size": source.get("size", 0),
        "url": source.get("url", "") or (
            GD.SCIENCEBASE_FILE + "?name=" + source.get("name", "")),
        "md5": (source.get("checksum") or {}).get("value", ""),
    } for source in item.get("files", [])]
    archives = GD.select_tiff_archives(files)
    shape, transform, crs, template = GD.official_grid()
    footprint = np.isfinite(template)
    mosaics = {channel: np.zeros(shape, np.float32) for channel in CHANNELS}
    masks = {channel: np.zeros(shape, bool) for channel in CHANNELS}
    archive_records = {}
    observed_members = {}
    selected_records = {channel: [] for channel in CHANNELS}

    try:
        with tempfile.TemporaryDirectory(prefix="geodawn-ext-", dir=args.out) as td:
            temp_root = Path(td)
            for area in (2, 1):
                source = archives[area]
                archive_path = temp_root / GD._safe_basename(source["name"])
                print(f"downloading Area {area} TIFF archive ({source['size']} B)",
                      flush=True)
                hashes = GD.download_to(source["url"], archive_path,
                                        source.get("size", 0), source.get("md5", ""))
                archive_records[area] = {"name": source["name"], **hashes}
                with zipfile.ZipFile(archive_path) as archive:
                    members = GD.inspect_tiff_zip(archive)
                    observed_members[area] = [
                        {"name": member["name"], "size": member["size"]}
                        for member in members
                    ]
                    chosen = select_extension_members(members, area)
                    for channel, member in chosen.items():
                        info = member["_zip_info"]
                        raster_path = temp_root / (
                            f"area{area}_{channel}_{GD._safe_basename(info.filename)}")
                        with archive.open(info) as source_stream, raster_path.open("wb") as target:
                            while True:
                                chunk = source_stream.read(1 << 20)
                                if not chunk:
                                    break
                                target.write(chunk)
                        values, valid, source_grid = GD.warp_to_grid(
                            raster_path, shape, transform, crs)
                        mosaics[channel][valid] = values[valid]
                        masks[channel] |= valid
                        selected_records[channel].append({
                            "area": area,
                            "archive": source["name"],
                            "member": info.filename,
                            "member_size": info.file_size,
                            "source_grid": source_grid,
                            "valid_px": int(valid.sum()),
                        })
                        raster_path.unlink()
    except Exception as exc:
        diagnostic = {
            "status": "review_required",
            "item": GD.SCIENCEBASE_ITEM,
            "doi": GD.DOI,
            "error": f"{type(exc).__name__}: {exc}",
            "observed_files": [
                {"name": str(source.get("name", "")),
                 "size": int(source.get("size", 0) or 0)} for source in files
            ],
            "observed_tiff_members": observed_members,
            "archive_hashes": archive_records,
        }
        (args.out / "observed_files.json").write_text(
            json.dumps(diagnostic, indent=1, ensure_ascii=False) + "\n")
        raise SystemExit(f"FAIL CLOSED: {type(exc).__name__}: {exc}") from exc

    bands = []
    product_files = {}
    for channel in CHANNELS:
        valid = masks[channel] & footprint & np.isfinite(mosaics[channel])
        bands.append(GD.quantise(mosaics[channel], valid))
        values = mosaics[channel][valid]
        product_files[channel] = {
            "sources": selected_records[channel],
            "valid_px": int(valid.sum()),
            "source_value_min": float(values.min()) if values.size else None,
            "source_value_max": float(values.max()) if values.size else None,
        }
    array = np.stack(bands).astype(np.uint8)
    out_tif = args.out / "geodawn_extensions_u8.tif"
    with rasterio.open(out_tif, "w", driver="GTiff", height=shape[0], width=shape[1],
                       count=len(CHANNELS), dtype="uint8", crs=crs,
                       transform=transform, compress="lzw", nodata=0) as target:
        target.descriptions = CHANNELS
        target.write(array)

    manifest = {
        "product": "external/geodawn_extensions/geodawn_extensions_u8.tif",
        "product_sha256": GD.sha256_file(out_tif),
        "grid": {
            "width": shape[1], "height": shape[0], "crs": crs,
            "transform": list(transform)[:6], "dtype": "uint8", "nodata": 0,
        },
        "channels": list(CHANNELS),
        "channel_semantics": {
            "ThK": "contractor Thorium/Potassium ratio grid",
            "UK": "contractor Uranium/Potassium ratio grid",
            "UTh": "contractor Uranium/Thorium ratio grid",
            "TMI_up150": "contractor total magnetic intensity upward-continued to 150 m grid",
        },
        "doi": GD.DOI,
        "sciencebase_item": GD.SCIENCEBASE_ITEM,
        "readme": (GD.SCIENCEBASE_FILE + "?name=GeoDAWN_ReadMe.pdf"),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "archives": archive_records,
        "archive_member_listing": observed_members,
        "priority_rule": (
            "Area 1 overrides Area 2 where they overlap; Area 1 is 50 m and "
            "Area 2 100 m per the official ReadMe."),
        "quantisation": (
            "uint8 1..255 over each mosaicked source channel's finite in-footprint "
            "1st..99th percentiles; 0=nodata. Bytes are ranks, not physical units."),
        "rights": (
            "USGS data release; retain citation/attribution and verify per-asset "
            "terms before redistribution."),
        "caveats": [
            "Ratio grids are contractor products from physical channels; this compact output does not preserve physical units.",
            "Upward continuation is a smoothed transform of TMI, not an independent sensor.",
            "Area/acquisition specifications differ; block-aware validation remains required.",
            "These are feature channels, not a fault map or competition submission.",
        ],
        "files": product_files,
    }
    (args.out / "geodawn_extensions.json").write_text(
        json.dumps(manifest, indent=1, allow_nan=False) + "\n")
    (args.out / "observed_files.json").write_text(json.dumps({
        "status": "archives_inspected",
        "item": GD.SCIENCEBASE_ITEM,
        "doi": GD.DOI,
        "observed_files": [
            {"name": str(source.get("name", "")),
             "size": int(source.get("size", 0) or 0)} for source in files
        ],
        "observed_tiff_members": observed_members,
    }, indent=1) + "\n")
    print(json.dumps(manifest, indent=1))
    return manifest


if __name__ == "__main__":
    main()
