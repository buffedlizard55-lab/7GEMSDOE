"""Lidar coverage-gap geography (session 5, backlog #1).

The region-wide lidar product covers ~75% of the scored footprint
(external/dem/lidar_scarp_features.json: grid_cells_with_lidar = 3,892,964).
The session-4 candidate emits nothing outside lidar coverage, so every new
fault in a gap is a guaranteed miss. This script measures, locally and
without any leaderboard feedback:

* footprint / covered / gap pixel counts (valid band of the lidar product
  vs the official template footprint),
* catalogue-fault density inside vs outside lidar (is the gap fault-poor?),
* distance-to-nearest-catalogue-fault histograms for gap vs covered pixels,
* per-quadrant gap fractions (where should new tiles go first?),
* verification that the session-4 candidate emits zero pixels in gaps.

Output: knowledge/session5/lidar_gaps.json (small, committed).
No thresholds are tuned here; nothing is selected on leaderboard scores.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
LIDAR = ROOT / "external" / "dem" / "lidar_scarp_features_u8.tif"
CANDIDATE = ROOT / "downloads" / "gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif"

import sys
sys.path.insert(0, str(ROOT / "scripts"))
from paths import LABELS_TIF, TEMPLATE_TIF, ensure_data  # noqa: E402


def read_band(path: Path, band: int = 1) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(band)


def main() -> None:
    ensure_data()
    with rasterio.open(TEMPLATE_TIF) as src:
        template = src.read(1)
    footprint = np.isfinite(template)
    with rasterio.open(LABELS_TIF) as src:
        lab, nodata = src.read(1), src.nodata
    truth = (lab != nodata) & (lab > 0)
    assert truth.shape == footprint.shape
    assert bool((truth & ~footprint).any()) is False

    with rasterio.open(LIDAR) as src:
        bands = src.descriptions or [None] * src.count
        # 'valid' is the last band per the product manifest; verify by name.
        names = [b or f"band{i+1}" for i, b in enumerate(bands)]
        if "valid" in names:
            valid_lidar = src.read(names.index("valid") + 1) > 0
        else:  # fall back to documented position (band 12)
            valid_lidar = src.read(12) > 0
    assert valid_lidar.shape == footprint.shape

    covered = footprint & valid_lidar
    gap = footprint & ~valid_lidar

    dist_fault = distance_transform_edt(~truth)
    bins = [0, 1, 2, 3, 5, 10, 20, 50, 1e9]
    labels = ["on", "1", "1-2", "2-3", "3-5", "5-10", "10-20", "20-50", ">50"]

    def hist(mask: np.ndarray) -> dict:
        d = dist_fault[mask]
        out = {}
        for lo, hi, name in zip(bins[:-1], bins[1:], labels):
            if name == "on":
                out[name] = int(((d == 0)).sum())
            else:
                out[name] = int(((d > lo) & (d <= hi)).sum())
        return out

    h, w = footprint.shape
    quadrants = {
        "NW": (slice(0, h // 2), slice(0, w // 2)),
        "NE": (slice(0, h // 2), slice(w // 2, w)),
        "SW": (slice(h // 2, h), slice(0, w // 2)),
        "SE": (slice(h // 2, h), slice(w // 2, w)),
    }
    quad_rows = {}
    for name, (ys, xs) in quadrants.items():
        fp = int(footprint[ys, xs].sum())
        gp = int(gap[ys, xs].sum())
        quad_rows[name] = {
            "footprint_px": fp,
            "gap_px": gp,
            "gap_fraction": round(gp / fp, 4) if fp else None,
            "catalogue_px": int(truth[ys, xs].sum()),
        }

    with rasterio.open(CANDIDATE) as src:
        cand = src.read(1)
    emitted = np.isfinite(cand) & (cand > 0)
    emitted_in_gap = int((emitted & gap).sum())

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "lidar_product": str(LIDAR.relative_to(ROOT)),
            "candidate": str(CANDIDATE.relative_to(ROOT)),
            "labels": "GEMS_DATA_DIR/existing_faults.tif (sha256-pinned)",
            "template": "GEMS_DATA_DIR/example_submission.tif (sha256-pinned)",
        },
        "footprint_px": int(footprint.sum()),
        "covered_px": int(covered.sum()),
        "gap_px": int(gap.sum()),
        "gap_fraction": round(float(gap.sum()) / float(footprint.sum()), 4),
        "catalogue_px_in_covered": int((truth & covered).sum()),
        "catalogue_px_in_gap": int((truth & gap).sum()),
        "catalogue_density_covered": round(
            float((truth & covered).sum()) / float(covered.sum()), 5),
        "catalogue_density_gap": round(
            float((truth & gap).sum()) / float(gap.sum()), 5) if gap.sum() else None,
        "gap_distance_to_catalogue_hist": hist(gap),
        "covered_distance_to_catalogue_hist": hist(covered),
        "quadrants": quad_rows,
        "candidate_emitted_px": int(emitted.sum()),
        "candidate_emitted_in_gap_px": emitted_in_gap,
        "interpretation": [
            "Gap pixels are guaranteed misses for any lidar-only emission policy.",
            "If catalogue density in gaps ~= covered, expect ~gap_fraction of new "
            "faults to fall outside lidar evidence (uniformity assumption).",
            "Quadrant gap fractions order the tile-fill priority for backlog #1.",
        ],
    }
    out = ROOT / "knowledge" / "session5" / "lidar_gaps.json"
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in (
        "footprint_px", "covered_px", "gap_px", "gap_fraction",
        "catalogue_px_in_gap", "catalogue_density_covered",
        "catalogue_density_gap", "candidate_emitted_in_gap_px")}, indent=1))
    print("quadrants:", json.dumps(quad_rows))


if __name__ == "__main__":
    main()
