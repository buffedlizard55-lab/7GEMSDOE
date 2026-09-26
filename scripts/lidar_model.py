"""H4b: does region-scale lidar scarp evidence localise faults better than the 19 bands?

Pre-registered comparison (written before the lidar product existed):
* arms: ``bands19`` (supplied 19 bands), ``lidar`` (lidar descriptors + context),
  ``both`` (19 bands + lidar). Same learner, same samples, same folds.
* folds: 5x5 geographic blocks assigned to 5 folds; training pixels within
  1 km (10 px) of a test block are dropped (buffer).
* truth for this diagnostic: held-out *known* fault pixels. This measures
  localisation of faults with the same kinds of expression, not the hidden
  new-fault truth. It is not a leaderboard estimate.
* primary statistic: skill multiple = coverage(model top-f) / coverage(random)
  at emission densities f in {0.5%, 1%, 2%, 3%} of held-out valid pixels, using the
  official kernel (scripts/metric.py) and the exact random baseline
  (scripts/random_baseline.py). Secondary: ROC AUC.
Promotion rule: ``both`` must beat ``bands19`` on the pooled skill multiple at
f=1% and 2% AND in >= 4 of 5 folds, else lidar stays a research signal.
Secondary (emission policy, same pixel budget): top-f of the raw score vs top-f
restricted to 1 px ridge pixels (scripts/emission.py ridge_nms), per arm.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import emission as EM
import paths
import random_baseline as RB
from metric import dtvi_components

ROOT = Path(__file__).resolve().parents[1]
import os
LIDAR = Path(os.environ.get("GEMS_LIDAR_PATH", ROOT / "external" / "dem" / "lidar_scarp_features_u8.tif"))
DENSITIES = (0.005, 0.01, 0.02, 0.03)
SEED = 20260926


def load_stack():
    import rasterio
    import dem_merge as DM
    d = paths.DATA_DIR
    with rasterio.open(d / "training_features.tif") as s:
        bands = s.read().astype(np.float32)
        bands[bands < -1e30] = np.nan
    with rasterio.open(d / "existing_faults.tif") as s:
        lab = s.read(1)
    with rasterio.open(d / "example_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(LIDAR) as s:
        names = list(s.descriptions)
        lid = {n: DM.dequantise(n, s.read(i + 1)).astype(np.float16) for i, n in enumerate(names)}  # uint8 source: f16 loses nothing material
    return bands, lab, foot, lid


PREFERRED = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
             "upface_max", "cross_max", "s1_max", "rough", "relief", "coh100", "valid"]
CONTEXT = ["ex_max", "step_max", "lapneg_max", "upface_max", "downface_max"]


def lidar_feature_block(lid, exclude=()):
    """Lidar descriptors plus small-neighbourhood context (max/mean filters)."""
    from scipy.ndimage import maximum_filter, uniform_filter
    feats, names = [], []
    base = [n for n in PREFERRED if n in lid and n not in exclude]
    for n in base:
        feats.append(lid[n]); names.append(n)
    # strike as doubled-angle unit vector weighted by coherence (orientation-aware, no wrap)
    th = np.radians(lid["strike"].astype(np.float32)) * 2
    coh = lid["coh100"].astype(np.float32)
    feats += [(np.cos(th) * coh).astype(np.float16), (np.sin(th) * coh).astype(np.float16)]
    names += ["strike_c2", "strike_s2"]
    del th, coh
    for n in [c for c in CONTEXT if c in base]:
        a = np.nan_to_num(lid[n].astype(np.float32), nan=0.0)
        for k in (3, 7):
            feats.append(maximum_filter(a, size=k).astype(np.float16)); names.append(f"{n}_max{k}")
        feats.append(uniform_filter(a, size=9).astype(np.float16)); names.append(f"{n}_mean9")
        # contrast: local value relative to its 1.5 km neighbourhood (linear anomaly)
        feats.append((a - uniform_filter(a, size=15)).astype(np.float16)); names.append(f"{n}_anom15")
        del a
    return feats, names


def block_folds(shape, nb=5, k=5, seed=SEED):
    h, w = shape
    rng = np.random.default_rng(seed)
    ids = rng.permutation(np.arange(nb * nb) % k)
    rb = np.minimum((np.arange(h) * nb) // h, nb - 1)
    cb = np.minimum((np.arange(w) * nb) // w, nb - 1)
    return ids[(rb[:, None] * nb + cb[None, :])].astype(np.int8)


def coverage_at_density(score, truth, test_mask, f, cand=None):
    """Emit top-f (of all test pixels) among candidates; return coverage + components."""
    import emission as EM
    k = max(1, int(round(f * int(test_mask.sum()))))
    pred = EM.top_k_mask(score, test_mask if cand is None else (cand & test_mask), k).astype(np.float64)
    t = np.where(test_mask, truth, 0).astype(np.int8)
    c = dtvi_components(np.where(test_mask, pred, np.nan), np.where(test_mask, t, 0))
    cov = c["TP_w"] / max(c["n_truth"], 1)
    return cov, c


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "knowledge" / "session4" / "lidar_experiment.json"))
    ap.add_argument("--n-neg", type=int, default=120000)
    ap.add_argument("--n-pos", type=int, default=40000)
    ap.add_argument("--rounds", type=int, default=300)
    ap.add_argument("--exclude", default="", help="comma-separated lidar channels to leave out")
    args = ap.parse_args(argv)
    import lightgbm as lgb
    from scipy.ndimage import binary_dilation
    from sklearn.metrics import roc_auc_score

    t0 = time.time()
    bands, lab, foot, lid = load_stack()
    H, W = lab.shape
    valid = foot & np.all(np.isfinite(bands), axis=0)
    lidok = np.nan_to_num(lid["valid"]) > 0.5
    pos = (lab == 1) & valid
    lfe, lnames = lidar_feature_block(lid, exclude=[e for e in args.exclude.split(",") if e])
    arms = {
        "bands19": ([bands[i] for i in range(bands.shape[0])], [f"b{i+1}" for i in range(bands.shape[0])]),
        "lidar": (lfe, lnames),
    }
    arms["both"] = (arms["bands19"][0] + lfe, arms["bands19"][1] + lnames)
    folds = block_folds((H, W))
    # restrict the diagnostic to pixels with lidar so every arm sees the same pixels
    universe = valid & lidok
    near = binary_dilation(pos, iterations=2)
    rng = np.random.default_rng(SEED)
    report = dict(pre_registration=__doc__.strip().splitlines(), lidar_product=str(LIDAR),
                  lidar_features=lnames, universe_px=int(universe.sum()),
                  positives_in_universe=int((pos & universe).sum()), densities=DENSITIES,
                  random_coverage={str(f): RB.coverage_random(f) for f in DENSITIES}, folds={})
    pooled = {a: {str(f): [0.0, 0] for f in DENSITIES} for a in arms}
    pooled_nms = {a: {str(f): [0.0, 0] for f in DENSITIES} for a in arms}
    importances = {}
    for k in range(5):
        test = universe & (folds == k)
        buf = binary_dilation(folds == k, iterations=10)
        train = universe & ~buf
        ptr = np.flatnonzero((pos & train).ravel())
        ntr = np.flatnonzero((train & ~near).ravel())
        ptr = rng.choice(ptr, min(args.n_pos, ptr.size), replace=False)
        ntr = rng.choice(ntr, min(args.n_neg, ntr.size), replace=False)
        idx = np.concatenate([ptr, ntr]); y = np.r_[np.ones(ptr.size), np.zeros(ntr.size)]
        te_idx = np.flatnonzero(test.ravel())
        fold_rep = dict(test_px=int(test.sum()), test_pos=int((pos & test).sum()),
                        train_pos=int(ptr.size), train_neg=int(ntr.size), arms={})
        for a, (fl, fn) in arms.items():
            X = np.stack([f.ravel()[idx] for f in fl], 1)
            m = lgb.LGBMClassifier(n_estimators=args.rounds, learning_rate=0.05, num_leaves=63,
                                   min_child_samples=100, subsample=0.8, subsample_freq=1,
                                   colsample_bytree=0.8, reg_lambda=5.0, random_state=SEED,
                                   n_jobs=2, verbose=-1)
            m.fit(X, y)
            score = np.full(H * W, -np.inf, np.float32)
            for s in range(0, te_idx.size, 400000):
                ch = te_idx[s:s + 400000]
                score[ch] = m.predict_proba(np.stack([f.ravel()[ch] for f in fl], 1))[:, 1]
            score = score.reshape(H, W)
            auc = roc_auc_score(pos[test], score[test])
            ar = dict(auc=round(float(auc), 4), skill={}, skill_nms={})
            ridge = EM.ridge_nms(np.where(test, score, 0), test)
            for f in DENSITIES:
                cov, c = coverage_at_density(score, pos.astype(np.int8), test, f)
                ar["skill"][str(f)] = dict(coverage=round(cov, 4),
                                           multiple=round(cov / RB.coverage_random(f), 3),
                                           dti_known=round(c["TP_w"] / (c["TP_w"] + 0.2 * c["FP_w"] + 0.8 * c["FN_w"] + 1e-9), 4))
                pooled[a][str(f)][0] += c["TP_w"]; pooled[a][str(f)][1] += c["n_truth"]
                cov2, c2 = coverage_at_density(score, pos.astype(np.int8), test, f, cand=ridge)
                ar["skill_nms"][str(f)] = dict(coverage=round(cov2, 4),
                                               multiple=round(cov2 / RB.coverage_random(f), 3))
                pooled_nms[a][str(f)][0] += c2["TP_w"]; pooled_nms[a][str(f)][1] += c2["n_truth"]
            fold_rep["arms"][a] = ar
            if a == "both":
                imp = dict(zip(fn, m.booster_.feature_importance("gain").tolist()))
                for n, v in imp.items():
                    importances[n] = importances.get(n, 0) + v
            print(f"fold {k} {a:8s} auc={auc:.4f} " + " ".join(
                f"f{f}:x{ar['skill'][str(f)]['multiple']}/nms x{ar['skill_nms'][str(f)]['multiple']}"
                for f in DENSITIES), flush=True)
        report["folds"][str(k)] = fold_rep
    report["pooled"] = {a: {f: dict(coverage=round(v[0] / max(v[1], 1), 4),
                                    multiple=round(v[0] / max(v[1], 1) / RB.coverage_random(float(f)), 3))
                            for f, v in d.items()} for a, d in pooled.items()}
    report["pooled_nms"] = {a: {f: dict(coverage=round(v[0] / max(v[1], 1), 4),
                                        multiple=round(v[0] / max(v[1], 1) / RB.coverage_random(float(f)), 3))
                                for f, v in d.items()} for a, d in pooled_nms.items()}
    wins = {f: sum(report["folds"][str(k)]["arms"]["both"]["skill"][f]["multiple"] >
                   report["folds"][str(k)]["arms"]["bands19"]["skill"][f]["multiple"] for k in range(5))
            for f in map(str, DENSITIES)}
    report["both_beats_bands19_folds"] = wins
    report["promotion_rule_met"] = bool(
        all(report["pooled"]["both"][f]["multiple"] > report["pooled"]["bands19"][f]["multiple"]
            for f in ("0.01", "0.02")) and wins["0.01"] >= 4 and wins["0.02"] >= 4)
    tot = sum(importances.values()) or 1
    report["both_gain_share_top20"] = dict(sorted(((n, round(v / tot, 4)) for n, v in importances.items()),
                                                  key=lambda x: -x[1])[:20])
    report["seconds"] = round(time.time() - t0, 1)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(json.dumps({"pooled": report["pooled"], "pooled_nms": report["pooled_nms"]}, indent=1))
    print("promotion_rule_met", report["promotion_rule_met"])


if __name__ == "__main__":
    main()
