"""Do the group's public scores track local (catalogue) skill? -- decisive check.

Why this exists
---------------
The official rules say the scored label set is *newly created fault labels*
(expert-identified faults that are NOT in the INGENIOUS compilation shipped as
`existing_faults.tif`).  Every local experiment in this repo therefore measures
a proxy, and the only way to know whether the proxy is usable is to compare it
with the eight known public scores.

This script recomputes, for each vendored scored file, the exact official
distance-weighted Tversky index (DTI) against the supplied catalogue labels and
correlates it with the public leaderboard score.  A high correlation means the
catalogue is a workable surrogate; a low correlation means every local number in
this repo must be read as a *within-catalogue ordering diagnostic only*.

Output: knowledge/session8/transfer_forensics.json (no plots, no dependencies
beyond numpy/rasterio/scipy already pinned in requirements-repro.txt).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import paths
from metric import dtvi_components

ROOT = Path(__file__).resolve().parents[1]
SCORED = ROOT / "external" / "scored"


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    den = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / den) if den else float("nan")


def main(argv=None):
    import rasterio
    from scipy.ndimage import distance_transform_edt

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "knowledge" / "session8" / "transfer_forensics.json"))
    args = ap.parse_args(argv)

    man = json.loads((SCORED / "manifest.json").read_text())
    with rasterio.open(paths.LABELS_TIF) as s:
        lab = s.read(1)
    with rasterio.open(paths.TEMPLATE_TIF) as s:
        foot = np.isfinite(s.read(1))
    truth = (lab == 1) & foot
    n_truth = int(truth.sum())
    dist_to_truth = distance_transform_edt(~truth).astype(np.float32)

    rows = []
    for entry in man["files"]:
        path = SCORED / entry["file"]
        with rasterio.open(path) as s:
            pred = s.read(1)
        p = np.where(np.isfinite(pred), pred, 0.0).astype(np.float64)
        p = np.clip(p, 0.0, 1.0)
        emit = p > 0
        comp = dtvi_components(p, truth)
        dti = comp["TP_w"] / (comp["TP_w"] + 0.2 * comp["FP_w"] + 0.8 * comp["FN_w"] + 1e-9)
        n_emit = int(emit.sum())
        # catalogue-fill by distance ring, and the same statistic recomputed for
        # the H1 candidate in lidar_candidate.json (kept comparable)
        rows.append(dict(
            file=entry["file"], account=entry.get("account"), public_score=entry.get("public_score"),
            density=round(n_emit / max(int(foot.sum()), 1), 6), emitted=n_emit,
            dti_catalogue=round(float(dti), 6), tp_w=round(comp["TP_w"], 1),
            fp_w=round(comp["FP_w"], 1), fn_w=round(comp["FN_w"], 1),
            catalogue_coverage=round(comp["TP_w"] / n_truth, 4),
            median_distance_to_catalogue=round(float(np.median(dist_to_truth[emit])), 2) if n_emit else None,
            share_within_1px=round(float((emit & (dist_to_truth <= 1.01)).sum() / max(n_emit, 1)), 4),
            share_within_3px=round(float((emit & (dist_to_truth <= 3.01)).sum() / max(n_emit, 1)), 4),
        ))
        print(json.dumps(rows[-1]), flush=True)

    scored = [r for r in rows if r["public_score"] is not None]
    pub = np.array([r["public_score"] for r in scored], float)
    loc = np.array([r["dti_catalogue"] for r in scored], float)
    dens = np.array([r["density"] for r in scored], float)
    cov = np.array([r["catalogue_coverage"] for r in scored], float)
    out = dict(
        question="does the supplied (INGENIOUS) catalogue order the eight known public scores?",
        n_files=len(scored), files=rows,
        spearman_dti_vs_public=round(spearman(loc, pub), 4),
        spearman_coverage_vs_public=round(spearman(cov, pub), 4),
        spearman_density_vs_public=round(spearman(dens, pub), 4),
        pearson_dti_vs_public=round(float(np.corrcoef(loc, pub)[0, 1]), 4),
        mean_public_over_local=round(float(np.mean(pub / np.maximum(loc, 1e-9))), 4),
        mean_local_over_public=round(float(np.mean(loc / np.maximum(pub, 1e-9))), 4),
        rank_table=sorted([(r["file"], r["public_score"], r["dti_catalogue"]) for r in scored],
                          key=lambda t: -t[1]) if False else
        [[r["file"], r["public_score"], r["dti_catalogue"]] for r in
         sorted(scored, key=lambda r: -r["public_score"])],
        caveats=[
            "Public scores are group-reported / leaderboard observations, one account pairing is unverified.",
            "The scored truth is the organizers' *newly created* fault labels; the catalogue is a different set.",
            "n is small (7 scored files); treat correlation coefficients as descriptions, not statistics.",
        ],
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k.startswith(('spearman', 'pearson', 'mean'))}, indent=1))
    return out


if __name__ == "__main__":
    main()
