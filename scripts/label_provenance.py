"""What do the shipped labels actually contain, and what is left to predict? (H12 audit)

Session 8 measured the provenance of the competition's training raster against
the official regional compilations and against the USGS Quaternary Fault and
Fold Database raster this repository already builds. The result is a hard
constraint on strategy, so it is re-measured here from committed artifacts
rather than quoted from a workflow log:

* the shipped ``existing_faults.tif`` contains 60,988 label pixels inside the
  competition footprint;
* **every** shipped label pixel is within 1 px of an INGENIOUS v2 trace
  (``labels_within_1px_of_v2 == 1.0``) and within 1 px of an INGENIOUS v1 trace;
* **inside the footprint the compilation adds nothing**: of the 169,207 v2 trace
  pixels in the grid, only a handful are farther than 1 px from a shipped label;
* the remaining ~108 k compilation pixels lie *outside* the competition
  footprint, which is a property of the study-area boundary, not a hidden label
  source;
* therefore the labels the prize actually scores ("a privately withheld subset of
  the original new fault dataset", rules §1.1) cannot be a repackaging of the
  published record. They are structures that are absent from the published
  catalogues by construction, and the only way to reach them is detection in the
  supplied geophysics/lidar.

Consequences enforced by this audit:

1. Any candidate that copies published compilation geometry **inside the
   footprint** is retired automatically -- the residual is a few pixels.
2. Emission exactly on a shipped label pixel is guaranteed false positive; the
   H1 lidar candidate already excludes them (``scored_dom = valid & ~known``).
3. A future "published faults we overlooked" claim must come with a
   footprint-restricted residual count, not a grid-wide one (the grid-wide
   number was 108,131 px and was 99.99 % outside the scored region).

Usage: .venv/bin/python scripts/label_provenance.py [--out knowledge/session8/label_provenance.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import paths

ROOT = Path(__file__).resolve().parents[1]
INGENIOUS = ROOT / "external" / "ingenious" / "ingenious_faults_u8.tif"
INGENIOUS_MAN = ROOT / "external" / "ingenious" / "ingenious_faults.json"
QFAULTS = ROOT / "external" / "qfaults" / "qfaults_prior_u8.tif"
MIN_PACKAGEABLE_PX = 20000


def audit() -> dict:
    import rasterio
    from scipy.ndimage import distance_transform_edt

    man = json.loads(INGENIOUS_MAN.read_text())
    with rasterio.open(paths.LABELS_TIF) as s:
        lab = s.read(1)
    foot = lab >= 0
    known = lab == 1
    out = {
        "question": "does the shipped training raster exhaust the published fault record inside the "
                    "competition footprint?",
        "labels_tif": str(paths.LABELS_TIF),
        "shipped_labels_px": int(known.sum()),
        "footprint_px": int(foot.sum()),
        "sources": {},
    }
    with rasterio.open(INGENIOUS) as s:
        names = list(s.descriptions)
        ii = {n: i + 1 for i, n in enumerate(names)}
        for band in ("v1_trace", "v2_trace", "v2_not_in_labels"):
            m = s.read(ii[band]) > 0
            d = distance_transform_edt(~m)
            out["sources"][f"ingenious_{band}"] = {
                "px_grid": int(m.sum()),
                "px_in_footprint": int((m & foot).sum()),
                "px_in_footprint_far_from_labels": int((m & foot & (distance_transform_edt(~known) > 1.01)).sum()),
                "labels_within_1px": round(float((d[known] <= 1.01).mean()), 4),
            }
    if QFAULTS.exists():
        with rasterio.open(QFAULTS) as s:
            names = list(s.descriptions)
            ii = {n: i + 1 for i, n in enumerate(names)}
            m = np.zeros(lab.shape, bool)
            for n in names:
                m |= s.read(ii[n]) > 0
            d = distance_transform_edt(~m)
            out["sources"]["qfaults_any_band"] = {
                "px_grid": int(m.sum()),
                "px_in_footprint": int((m & foot).sum()),
                "labels_within_1px": round(float((d[known] <= 1.01).mean()), 4),
            }
    prog = out["sources"]["ingenious_v2_not_in_labels"]
    out["packaged"] = prog["px_in_footprint_far_from_labels"] >= MIN_PACKAGEABLE_PX
    out["conclusion"] = (
        "the compilation adds "
        f"{prog['px_in_footprint_far_from_labels']} pixels inside the footprint that the shipped labels do not "
        f"already mark; the grid-wide residual of {prog['px_grid']} pixels is "
        f"{100 * (1 - prog['px_in_footprint'] / max(prog['px_grid'], 1)):.2f}% outside the scored region"
    )
    out["effect"] = ("no 'published faults we overlooked' candidate can be packaged" if not out["packaged"]
                     else "a residual candidate is available; re-run the packaging path")
    return out


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "knowledge" / "session8" / "label_provenance.json"))
    args = ap.parse_args(argv)
    rep = audit()
    Path(args.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    main()
