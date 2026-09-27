"""Which emission policy actually maximises the official metric? (H14)

The competition metric is a distance-weighted Tversky index (DTI). With a fixed
support set S it is

    DTI(S) = TP_w / (0.2*TP_w + 0.2*FP_w + 0.8*N_truth)
    TP_w   = sum over truth pixels g of max_{x in S} p(x)*k(dist(x,g))
    FP_w   = sum over x in S of p(x) * (1 - k(dist(x, G)))

Two consequences are worth testing rather than assuming:

  1. **Scale up, do not hedge.** For a fixed S, scaling every p(x) by c>0 gives
     DTI(c) = c*T / (0.2*c*T + 0.2*c*F + 0.8*N), which is strictly increasing in c.
     Partial probabilities on a fixed support can only dilute the score; the
     optimal values are 1 on S and 0 elsewhere.
  2. **Match the kernel, not the pixels.** Treating each candidate pixel's
     expected contribution as the kernel-convolved score (p ⊛ k), the marginal
     gain and marginal false-positive cost are both linear in the decision, so the
     optimal support is a *threshold on the kernel-smoothed* score, not on the raw
     score. Ridge thinning (the policy this repository shipped for H1) optimises a
     different objective --- the dispersion index, which is a diagnostic, not the
     metric.

This experiment measures the three policies on real geography with the frozen
5-fold geographic protocol used elsewhere in the repository, using a transparent,
training-free fault-likelihood field: negative distance to the nearest *training*
catalogue fault (a proximity prior, the same family as the H3 prior). Truth is the
held-out catalogue faults of each fold, scored with the repository's own
implementation of the official metric. Nothing here is a leaderboard estimate:
the scored label set is the organisers' new faults, not this catalogue.

Usage: .venv/bin/python scripts/emission_policy_experiment.py [--out ...]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import emission as EM  # noqa: E402
import paths  # noqa: E402
import random_baseline as RB  # noqa: E402
from metric import dtvi_components  # noqa: E402

DENSITIES = (0.005, 0.01, 0.02, 0.03)
SEED = 20260926
R_PIXELS = 3.0


def metric_kernel(radius: float = R_PIXELS):
    """The metric's own kernel k(d) = max(1 - d/radius, 0) on a 2D stencil."""
    n = int(np.floor(radius))
    yy, xx = np.mgrid[-n:n + 1, -n:n + 1]
    d = np.sqrt(yy * yy + xx * xx)
    return np.maximum(1.0 - d / radius, 0.0).astype(np.float32)


def matched_filter(score: np.ndarray, valid: np.ndarray, radius: float = R_PIXELS) -> np.ndarray:
    """Convolve the score with the metric kernel, normalised by valid neighbours.

    Normalising by the in-window valid weight keeps the filtered score comparable
    across the footprint edge and the lidar gap, where whole stencil arms are
    missing; without it, edges would score lower for lack of data rather than for
    lack of evidence.
    """
    from scipy.ndimage import convolve
    k = metric_kernel(radius)
    s = np.where(valid, np.nan_to_num(score, nan=0.0), 0.0).astype(np.float32)
    num = convolve(s, k, mode="constant", cval=0.0)
    den = convolve(valid.astype(np.float32), k, mode="constant", cval=0.0)
    out = np.zeros_like(num)
    good = den > 0
    out[good] = num[good] / den[good]
    return out


def main(argv=None) -> dict:
    import rasterio
    from scipy.ndimage import binary_dilation, distance_transform_edt

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "knowledge" / "session8" / "emission_policy_experiment.json"))
    ap.add_argument("--radius", type=float, default=R_PIXELS)
    args = ap.parse_args(argv)
    t0 = time.time()

    with rasterio.open(paths.LABELS_TIF) as s:
        lab = s.read(1)
    with rasterio.open(paths.TEMPLATE_TIF) as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(ROOT / "external/dem/lidar_scarp_features_u8.tif") as s:
        names = list(s.descriptions)
        valid_lidar = s.read(names.index("valid") + 1) > 0
    H, W = lab.shape
    pos = (lab == 1) & foot
    universe = foot & valid_lidar
    folds = _folds((H, W))

    policies = ("raw", "ridge", "matched", "matched_raw")
    pooled = {p: {str(f): [0.0, 0.0, 0] for f in DENSITIES} for p in policies}
    report = {
        "question": "raw threshold vs ridge thinning vs metric-kernel-matched threshold, "
                    "same pixel budget, frozen 5-fold geographic protocol",
        "field": "negative Euclidean distance (px) to the nearest catalogue fault of the TRAINING folds",
        "kernel": metric_kernel(args.radius).tolist(),
        "densities": DENSITIES,
        "folds": {},
        "pre_registration_note": __doc__.strip().splitlines()[:12],
        "known_limitations": [
            "The field is a proximity prior (1/(1+distance to the nearest TRAINING-fold fault)) "
            "restricted to each held-out block, so its maximum sits along the block boundary, "
            "which is the least likely place for a held-out fault inside that block. The measured "
            "multiples below 1 are therefore a property of this deliberately simple field and of "
            "the block design, not a general statement about proximity features.",
            "The experiment compares emission POLICIES at equal pixel budget on one field; it does "
            "not compare fields. Policy is not the lever that the leaderboard responds to.",
        ],
    }
    for k in range(5):
        test = universe & (folds == k)
        buf = binary_dilation(folds == k, iterations=10)
        train = universe & ~buf
        truth_train = pos & train
        truth_test = (pos & test)
        if truth_train.sum() == 0 or truth_test.sum() == 0:
            continue
        dist = distance_transform_edt(~truth_train).astype(np.float32)
        # Positive, monotone-decreasing proximity field: `ridge_nms` requires a
        # positive score (it thresholds s > 0), and the kernel-matched arm needs
        # a field whose convolution is meaningful.
        pos = 1.0 / (1.0 + dist)
        score = np.where(test, pos, 0.0).astype(np.float32)
        matched = np.where(test, matched_filter(pos, test & universe, args.radius), 0.0).astype(np.float32)
        # a raw-score field smoothed with the same kernel but NOT renormalised,
        # to separate "the kernel" from "the edge renormalisation"
        from scipy.ndimage import convolve
        matched_raw = np.where(test, convolve(np.where(test, pos, 0.0), metric_kernel(args.radius),
                                              mode="constant", cval=0.0), 0.0).astype(np.float32)
        ridge = EM.ridge_nms(np.where(test, score, 0), test)
        fold = {"test_px": int(test.sum()), "truth_test_px": int(truth_test.sum()),
                "truth_train_px": int(truth_train.sum()), "policies": {}}
        for p, field in (("raw", score), ("ridge", score), ("matched", matched), ("matched_raw", matched_raw)):
            cand = ridge if p == "ridge" else test
            fold["policies"][p] = {}
            for f in DENSITIES:
                n = max(1, int(round(f * int(test.sum()))))
                emit = EM.top_k_mask(field, cand, n)
                pred = np.where(test, emit.astype(np.float64), np.nan)
                truth = np.where(test, truth_test.astype(np.int8), 0)
                c = dtvi_components(pred, truth)
                dti = c["TP_w"] / (c["TP_w"] + 0.2 * c["FP_w"] + 0.8 * c["FN_w"] + 1e-9)
                cov = c["TP_w"] / max(c["n_truth"], 1)
                fold["policies"][p][str(f)] = {
                    "coverage": round(float(cov), 4),
                    "multiple": round(float(cov / RB.coverage_random(f)), 3),
                    "dti_held_out": round(float(dti), 4),
                    "dispersion_index": round(float(EM.dispersion_index(emit, foot)) if emit.any() else float("nan"), 2),
                }
                pooled[p][str(f)][0] += float(c["TP_w"])
                pooled[p][str(f)][1] += float(c["n_truth"])
                pooled[p][str(f)][2] += 1
        report["folds"][str(k)] = fold
        print(f"fold {k}: " + "  ".join(
            f"{p}:x{fold['policies'][p][str(0.01)]['multiple']:.2f}/{fold['policies'][p][str(0.02)]['multiple']:.2f}"
            for p in policies), flush=True)

    def pooled_row(p, f):
        tp, n, _ = pooled[p][str(f)]
        cov = tp / max(n, 1)
        return dict(coverage=round(cov, 4), multiple=round(cov / RB.coverage_random(f), 3))

    report["pooled"] = {p: {str(f): pooled_row(p, f) for f in DENSITIES} for p in policies}
    report["wins_vs_raw"] = {p: {str(f): sum(
        report["folds"][k]["policies"][p][str(f)]["multiple"] > report["folds"][k]["policies"]["raw"][str(f)]["multiple"]
        for k in report["folds"]) for f in DENSITIES} for p in ("ridge", "matched", "matched_raw")}
    report["wins_matched_vs_ridge"] = {str(f): sum(
        report["folds"][k]["policies"]["matched"][str(f)]["multiple"] > report["folds"][k]["policies"]["ridge"][str(f)]["multiple"]
        for k in report["folds"]) for f in DENSITIES}
    report["seconds"] = round(time.time() - t0, 1)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(json.dumps(report["pooled"], indent=1))
    print("matched beats ridge in folds:", report["wins_matched_vs_ridge"])
    return report


def _folds(shape, nb=5, k=5, seed=SEED):
    """Same block-fold assignment as the frozen lidar experiment."""
    h, w = shape
    rng = np.random.default_rng(seed)
    ids = rng.permutation(np.arange(nb * nb) % k)
    rb = np.minimum((np.arange(h) * nb) // h, nb - 1)
    cb = np.minimum((np.arange(w) * nb) // w, nb - 1)
    return ids[(rb[:, None] * nb + cb[None, :])].astype(np.int8)


if __name__ == "__main__":
    main()
