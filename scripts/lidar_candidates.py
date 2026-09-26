"""Build lidar-informed submission candidates (binary, thin, format-gated).

Rules written before any leaderboard feedback on these files:
* model: LightGBM trained on every lidar-covered valid pixel (known faults vs
  pixels > 2 px from them). Pixels without lidar are not emitted (0.0).
* arm: the pre-written rule named the ``both`` arm. The pre-registered
  experiment (knowledge/session4/lidar_experiment.json) then showed ``lidar``
  beating ``both`` in 4/5 folds and pooled at every density, with the 19 bands
  below random across geography. DEVIATION (recorded): default arm = ``lidar``.
* emission: binary 1.0 on the top-k ridge pixels (1 px NMS), 0.0 elsewhere in the
  footprint, NaN outside; known-fault pixels are 0 (they are masked by the scorer).
* density: maximise expected DTI(f) = c(f) rho / (0.2 c rho + 0.2 f + 0.8 rho), with
  rho from the scored-file analysis and c(f) = c_rand(f) * (1 + tau (m(f) - 1)),
  m(f) the measured held-out ridge-NMS skill multiple on known faults, tau = 0.5
  (conservative transfer discount).
* guard: fill fraction within 1 px of known faults must stay <= 0.15 (the worst
  group upload concentrated 0.32-0.39 there); excess near-known pixels are
  replaced by the next-best far ridge pixels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import emission as EM
import lidar_model as LM
import paths
import random_baseline as RB

ROOT = Path(__file__).resolve().parents[1]
TAU = 0.5
NEAR_FILL_CAP = 0.15
SEED = 20260926


def percentile_rank(x: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros(x.shape, np.float32)
    v = x[mask]
    order = np.argsort(v, kind="stable")
    r = np.empty(v.size, np.float32)
    r[order] = (np.arange(v.size, dtype=np.float32) + 1) / v.size
    out[mask] = r
    return out


def choose_density(exp: dict, rho: float, arm: str = "lidar", key: str = "pooled_nms"):
    rows = []
    for f_s, v in exp[key][arm].items():
        f = float(f_s)
        m = v["multiple"]
        c = RB.coverage_random(f) * (1 + TAU * (m - 1))
        d = c * rho / (0.2 * c * rho + 0.2 * f + 0.8 * rho)
        rows.append(dict(f=f, measured_multiple=m, assumed_multiple=round(1 + TAU * (m - 1), 3),
                         expected_dti=round(d, 4)))
    best = max(rows, key=lambda r: r["expected_dti"])
    return best, rows


def train(X_idx, y, feats):
    import lightgbm as lgb
    X = np.stack([f.ravel()[X_idx] for f in feats], 1)
    m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                           subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=5.0,
                           random_state=SEED, n_jobs=2, verbose=-1)
    m.fit(X, y)
    return m


def predict(m, feats, idx):
    out = np.empty(idx.size, np.float32)
    for s in range(0, idx.size, 400000):
        ch = idx[s:s + 400000]
        out[s:s + ch.size] = m.predict_proba(np.stack([f.ravel()[ch] for f in feats], 1))[:, 1]
    return out


def main(argv=None):
    import rasterio
    from scipy.ndimage import binary_dilation, distance_transform_edt
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default=str(ROOT / "knowledge" / "session4" / "lidar_experiment.json"))
    ap.add_argument("--scored", default=str(ROOT / "knowledge" / "session4" / "scored_files_analysis.json"))
    ap.add_argument("--densities", default="", help="override: comma list of densities to build")
    ap.add_argument("--out", default=str(ROOT / "scratch" / "candidates"))
    ap.add_argument("--arm", default="lidar", choices=["lidar", "both"])
    args = ap.parse_args(argv)
    exp = json.loads(Path(args.experiment).read_text())
    rho = json.loads(Path(args.scored).read_text())["implied_truth_density"]
    best, table = choose_density(exp, rho, arm=args.arm)
    dens = [float(x) for x in args.densities.split(",") if x] or [best["f"]]

    bands, lab, foot, lid = LM.load_stack()
    H, W = lab.shape
    valid = foot & np.all(np.isfinite(bands), axis=0)
    known = (lab == 1) & foot
    lidok = np.nan_to_num(lid["valid"].astype(np.float32)) > 0.5
    lfe, lnames = LM.lidar_feature_block(lid)
    feats = ([bands[i] for i in range(bands.shape[0])] if args.arm == "both" else []) + lfe
    if args.arm == "lidar":
        del bands
    near2 = binary_dilation(known, iterations=2)
    rng = np.random.default_rng(SEED)
    dom = valid & lidok
    p = np.flatnonzero((known & dom).ravel())
    n = np.flatnonzero((dom & ~near2).ravel())
    p = rng.choice(p, min(60000, p.size), replace=False)
    n = rng.choice(n, min(180000, n.size), replace=False)
    m = train(np.r_[p, n], np.r_[np.ones(p.size), np.zeros(n.size)], feats)
    idx = np.flatnonzero(dom.ravel())
    raw = np.zeros(H * W, np.float32)
    raw[idx] = predict(m, feats, idx)
    score = percentile_rank(raw.reshape(H, W), dom)
    models = {args.arm: dict(train_pos=int(p.size), train_neg=int(n.size), scored_px=int(idx.size),
                             features=len(feats))}
    del feats, lfe, raw
    valid = dom  # emission restricted to lidar-covered valid pixels
    scored_dom = valid & ~known
    # NMS on the full model field (known pixels keep their scores), exactly as in the
    # pre-registered experiment; known pixels are dropped only afterwards. Zeroing
    # them first would turn pixels flanking every catalogue trace into artificial
    # ridge maxima (a halo), the failure mode of the worst group upload.
    ridge = EM.ridge_nms(np.where(valid, score, 0), valid) & scored_dom
    dist = distance_transform_edt(~known)
    ring1 = foot & (dist > 0) & (dist <= 1.01)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    built = []
    for f in dens:
        k = int(round(f * int(scored_dom.sum())))
        emit = EM.top_k_mask(score, ridge & scored_dom, k)
        cap = int(NEAR_FILL_CAP * ring1.sum())
        n1 = int((emit & ring1).sum())
        if n1 > cap:  # swap excess near-known pixels for the next-best far ridge pixels
            drop = EM.top_k_mask(-score, emit & ring1, n1 - cap)
            emit &= ~drop
            extra = EM.top_k_mask(score, ridge & scored_dom & ~emit & ~ring1, n1 - cap)
            emit |= extra
        arr = np.full((H, W), np.nan, np.float32)
        arr[foot] = 0.0
        arr[emit & foot] = 1.0
        tag = f"lidar-{args.arm}-ridge-f{f:.3f}".replace("0.", "p")
        tmp = out / f"{tag}.tif"
        with rasterio.open(paths.TEMPLATE_TIF) as t:
            prof = t.profile
        prof.update(dtype="float32", count=1, nodata=np.nan, compress="deflate", predictor=3)
        with rasterio.open(tmp, "w", **prof) as dst:
            dst.write(arr, 1)
        sha = hashlib.sha256(tmp.read_bytes()).hexdigest()
        final = out / f"gems7-{tag}-{sha[:12]}.tif"
        tmp.rename(final)
        fill = {b: round(float((emit & foot & (dist > lo) & (dist <= hi)).sum()) /
                         max(int((foot & (dist > lo) & (dist <= hi)).sum()), 1), 4)
                for lo, hi, b in [(0.1, 1.01, "1"), (1.01, 3.01, "1-3"), (3.01, 10.01, "3-10"),
                                  (10.01, 50.01, "10-50"), (50.01, 1e9, ">50")]}
        built.append(dict(file=final.name, sha256=sha, density=f, emitted=int(emit.sum()),
                          emitted_with_lidar=int((emit & lidok).sum()),
                          near_known_swapped=max(n1 - cap, 0), fill_by_distance_px=fill,
                          dispersion_index=round(EM.dispersion_index(emit, foot), 2)))
        print(json.dumps(built[-1]))
    rep = dict(rules=__doc__.strip().splitlines(), arm=args.arm, rho=rho, tau=TAU, density_table=table,
               chosen=best, models=models, lidar_features=lnames, candidates=built)
    (out / "candidates.json").write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    main()
