"""Audit whether GeoDAWN 'extension' channels duplicate supplied features."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio

import geodawn_rad as GD
import paths

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "external" / "geodawn_extensions" / "geodawn_extensions_u8.tif"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=(
        ROOT / "knowledge" / "session7" / "extension_overlap.json"))
    args = parser.parse_args(argv)
    paths.ensure_data()
    with rasterio.open(paths.FEATURES_TIF) as source:
        description = source.descriptions[13]
        supplied_tmi = source.read(14)
    with rasterio.open(paths.TEMPLATE_TIF) as source:
        footprint = np.isfinite(source.read(1))
    with rasterio.open(EXT) as source:
        if tuple(source.descriptions) != ("ThK", "UK", "UTh", "TMI_up150"):
            raise ValueError(f"unexpected extension channels: {source.descriptions}")
        up150 = source.read(4)
    valid = footprint & np.isfinite(supplied_tmi) & (supplied_tmi > -1e30)
    supplied_rank = GD.quantise(supplied_tmi, valid)
    common = valid & (up150 > 0)
    a = supplied_rank[common].astype(np.float64)
    b = up150[common].astype(np.float64)
    report = {
        "status": "measured_overlap_diagnostic",
        "comparison": "supplied band 14 versus official TMI_up150 compact ranks",
        "supplied_band": 14,
        "supplied_description": description,
        "common_px": int(common.sum()),
        "exact_byte_fraction": float(np.mean(a == b)),
        "mean_absolute_byte_difference": float(np.mean(np.abs(a - b))),
        "pearson_rank_correlation": float(np.corrcoef(a, b)[0, 1]),
        "input_sha256": {
            "training_features": GD.sha256_file(paths.FEATURES_TIF),
            "extension_product": GD.sha256_file(EXT),
        },
        "interpretation": (
            "TMI_up150 is nearly redundant with supplied TMI after each is robustly "
            "quantised; it is a transformed same-sensor diagnostic, not an independent channel."),
        "caveat": (
            "Correlation/equality are between compact rank encodings, not source physical values."),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, allow_nan=False) + "\n")
    print(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    main()
