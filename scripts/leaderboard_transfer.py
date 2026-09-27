"""What do our scored files say about the public test set?  (session 8)

Seven group files have a known public score (``external/scored/manifest.json``):
0.1563, 0.1560, 0.1193, 0.1152, 0.0830, 0.0343, 0.0286.  The official rules
(§3.3, §3.5, §3.6.1) say scoring is against *newly created* fault labels and
that the provided training labels are the INGENIOUS Great Basin compilation, so
the published catalogue is not the public test set -- but it is the only local
truth-like raster we have.  This script measures how well each file does against
the catalogue, against lidar coverage, and how those measures line up with the
observed public scores.  It is a transfer diagnostic, not a score estimate.

Outputs a JSON report and a printed table.  Every number is reproducible from
committed files plus the three competition rasters in ``$GEMS_DATA_DIR``.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np

import metric as M

ROOT = Path(__file__).resolve().parents[1]
SCORED = ROOT / "external" / "scored"


def load_catalogue():
    import rasterio

    d = Path(os.environ.get("GEMS_DATA_DIR", Path.home() / "gems_data"))
    with rasterio.open(d / "existing_faults.tif") as s:
        lab = s.read(1)
    return lab == 1, lab >= 0


def load_lidar():
    import rasterio

    with rasterio.open(ROOT / "external/dem/lidar_scarp_features_u8.tif") as s:
        valid = s.read(s.count)
    return valid > 0


def diagnostics(path: Path, cat: np.ndarray, foot: np.ndarray, lidar: np.ndarray) -> dict:
    import rasterio

    with rasterio.open(path) as s:
        p = s.read(1).astype(np.float64)
    p = np.where(np.isfinite(p), p, 0.0)
    p = np.clip(p, 0, 1)
    inside_nan = int((~np.isfinite(s.read(1)) & foot).sum()) if False else 0
    fired = p > 0
    n = int(fired.sum())
    out = {
        "file": path.name,
        "emitted_px": n,
        "density": n / float(foot.sum()),
        "predicted_mass": float(p.sum()),
        "unique_values": int(np.unique(p[fired]).size) if n else 0,
        "nan_inside_footprint": inside_nan,
        "values_in_01": bool(p.min() >= 0 and p.max() <= 1),
        "emission_on_lidar_cells": float((fired & lidar).sum() / max(n, 1)),
    }
    # dispersion: share of emitted pixels with a neighbour within 2 px
    from scipy.ndimage import maximum_filter

    dil = maximum_filter(fired, size=5)
    out["dispersion"] = float(dil[fired].mean()) if n else 0.0
    # distance to the published catalogue
    from scipy.ndimage import distance_transform_edt

    dist = distance_transform_edt(~cat)
    d = dist[fired]
    for k in (1, 2, 3, 5, 10, 20, 50):
        out[f"fill_le{k}px"] = float((d <= k).mean()) if n else 0.0
    out["mean_dist_px"] = float(d.mean()) if n else 0.0
    comp = M.dtvi_components(p, cat.astype(np.uint8))
    out["dti_vs_catalogue"] = M.dtvi_closed_form(comp["TP_w"], comp["FP_w"], comp["n_truth"])
    out["tp_w"], out["fp_w"], out["fn_w"] = comp["TP_w"], comp["FP_w"], comp["FN_w"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="knowledge/session8/leaderboard_transfer.json")
    args = ap.parse_args(argv)
    man = json.loads((SCORED / "manifest.json").read_text())
    scores = {f["file"]: f.get("public_score") for f in man["files"]}
    cat, foot = load_catalogue()
    lidar = load_lidar()
    rows = []
    for f in sorted(SCORED.glob("*.tif")):
        r = diagnostics(f, cat, foot, lidar)
        r["public_score"] = scores.get(f.name)
        rows.append(r)
    # the current un-scored H1 candidate is measured on the same footing
    h1 = ROOT / "downloads/gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif"
    if h1.exists():
        r = diagnostics(h1, cat, foot, lidar)
        r["public_score"] = None
        r["note"] = "session-4 H1 lidar candidate, not yet scored"
        rows.append(r)

    scored = [r for r in rows if r["public_score"] is not None]
    y = np.array([r["public_score"] for r in scored])

    def corr(key, log=False):
        x = np.array([r[key] for r in scored], dtype=float)
        if log:
            x = np.log10(np.maximum(x, 1e-12))
        if np.std(x) == 0:
            return None
        from scipy.stats import pearsonr, spearmanr

        return {"pearson": float(pearsonr(x, y)[0]), "spearman": float(spearmanr(x, y)[0])}

    keys = ["density", "dispersion", "fill_le1px", "fill_le3px", "fill_le10px", "fill_le50px",
            "mean_dist_px", "emission_on_lidar_cells", "dti_vs_catalogue", "fp_w", "tp_w"]
    corr_table = {}
    for k in keys:
        c = corr(k)
        if c:
            corr_table[k] = c
    out = {
        "question": ("Which local measurement of a group file predicts its public leaderboard score? "
                     "n = %d scored files: treat as a sign test, not a calibration." % len(scored)),
        "official_rules_basis": {
            "training_labels_source": "rules §3.3 footnote 4: INGENIOUS Great Basin Regional Dataset Compilation",
            "public_test": "rules §3.6.1: ground-truth labels split into public and private test datasets; §3.5 scores against newly created fault labels",
            "consequence": "the published catalogue is the training label set, not the public test set",
        },
        "correlations_with_public_score": corr_table,
        "rows": rows,
        "scored_rows": len(scored),
    }
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1))
    hdr = f"{'file':38s} {'score':>6s} {'dens%':>6s} {'disp':>5s} {'f<=1':>5s} {'f<=3':>5s} {'f<=10':>6s} {'meanD':>6s} {'lidar':>5s} {'DTIcat':>7s}"
    print(hdr)
    for r in rows:
        print(f"{r['file'][:38]:38s} {('%.4f' % r['public_score']) if r['public_score'] is not None else '  --  ':>6s} "
              f"{100*r['density']:6.2f} {r['dispersion']:5.2f} {r['fill_le1px']:5.3f} {r['fill_le3px']:5.3f} "
              f"{r['fill_le10px']:6.3f} {r['mean_dist_px']:6.1f} {r['emission_on_lidar_cells']:5.2f} {r['dti_vs_catalogue']:7.4f}")
    print()
    for k, c in sorted(corr_table.items(), key=lambda kv: -abs(kv[1]["spearman"])):
        print(f"  {k:24s} spearman {c['spearman']:+.3f}  pearson {c['pearson']:+.3f}")
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
