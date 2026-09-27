"""Fold newly extracted gap tiles into the committed lidar product -- gap cells only.

Rule (checked by tests and by the merge job's own assert): a cell that already has
lidar (base ``valid`` > 0) is copied through bit-for-bit; only cells that are 0
(no lidar) may take a value from the new mosaic. For those cells the new value is
exact under the product's own aggregation rules, because a cell with ``valid`` = 0
contributed no samples to the original mosaic, so nothing is being averaged away.
Cells that were *partially* covered before keep their original value: mixing a
quantised historical value with new samples cannot reproduce the weighted mean,
so the conservative choice is to leave them untouched (reported in the manifest).

Inputs : ``--base`` (committed uint8 product), ``--shards`` (directory of .npz from
         ``scripts/dem_features.py``).
Output : rewritten ``--base`` (or ``--out``) + ``--manifest`` JSON with counts,
         SHA-256 of the old and new bytes and the tiles that contributed.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dem_merge as DM  # noqa: E402


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def merge_gap(base_path: str, shard_glob: str, out_path: str, manifest_path: str | None = None,
              tiles_meta: dict | None = None) -> dict:
    import rasterio

    files = sorted(glob.glob(shard_glob, recursive=True))
    if not files:
        raise SystemExit(f"no shard .npz files matched {shard_glob}")
    raw = DM.mosaic(files)
    derived = DM.derive(raw)
    new = {n: DM.quantise(n, derived[n]) for n in DM.BANDS}

    with rasterio.open(base_path) as src:
        profile = src.profile.copy()
        profile.update(count=len(DM.BANDS), dtype="uint8", compress="deflate", nodata=None)
        old = src.read()
        desc = list(src.descriptions) if src.descriptions else DM.BANDS
    if old.shape[0] != len(DM.BANDS):
        raise SystemExit(f"base has {old.shape[0]} bands, expected {len(DM.BANDS)}")
    if old.shape[1:] != new[DM.BANDS[0]].shape:
        raise SystemExit(f"shape mismatch: base {old.shape[1:]} vs mosaic {new[DM.BANDS[0]].shape}")

    gap_cell = old[DM.BANDS.index("valid")] == 0
    out = old.copy()
    filled = {}
    for i, n in enumerate(DM.BANDS):
        change = gap_cell & (new[n] > 0)
        out[i][change] = new[n][change]
        filled[n] = int(change.sum())
    # The whole point: nothing outside the previous gap may move.
    outside = ~gap_cell
    moved = int((out[:, outside] != old[:, outside]).sum())

    if profile.get("driver") and Path(out_path).parent:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(out)
        for i, n in enumerate(DM.BANDS):
            dst.set_band_description(i + 1, n)

    with rasterio.open(out_path) as s:
        reread = s.read()
    assert np.array_equal(reread, out), "written product does not read back identically"

    old_sha, new_sha = sha256(base_path), sha256(out_path)
    before = int((old[DM.BANDS.index("valid")] > 0).sum())
    after = int((out[DM.BANDS.index("valid")] > 0).sum())
    man = {
        "product": out_path,
        "operation": "gap-only fold of newly extracted 3DEP tiles",
        "rule": ("cells with previous valid > 0 are copied unchanged; cells with valid == 0 may be filled; "
                 "partially covered cells are left untouched (documented limitation)"),
        "shards": len(files),
        "tiles": sorted(Path(f).stem for f in files),
        "cells_with_lidar_before": before,
        "cells_with_lidar_after": after,
        "cells_filled": int((gap_cell & (out[DM.BANDS.index("valid")] > 0)).sum()),
        "per_channel_cells_filled": filled,
        "cells_changed_outside_previous_gap": moved,
        "sha256_before": old_sha,
        "sha256_after": new_sha,
        "quantisation_rule": "see scripts/dem_merge.py",
    }
    if tiles_meta:
        man.update(tiles_meta)
    if manifest_path:
        Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
        Path(manifest_path).write_text(json.dumps(man, indent=1))
    return man


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="external/dem/lidar_scarp_features_u8.tif")
    ap.add_argument("--shards", default="scratch/shards/**/*.npz")
    ap.add_argument("--out", default=None)
    ap.add_argument("--manifest", default="external/dem/lidar_gapfill.json")
    args = ap.parse_args(argv)
    out = args.out or args.base
    man = merge_gap(args.base, args.shards, out, args.manifest)
    print(json.dumps({k: man[k] for k in ("shards", "cells_with_lidar_before", "cells_with_lidar_after",
                                          "cells_filled", "cells_changed_outside_previous_gap",
                                          "sha256_after")}))
    if man["cells_changed_outside_previous_gap"] != 0:
        raise SystemExit(f"SAFETY: {man['cells_changed_outside_previous_gap']} cells changed outside the gap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
