"""Train the blind-fault detector: a gradient-boosted classifier that learns
the geophysical signature of catalogued faults from the GeoDAWN bands ONLY.

Deliberate design choice (documented in strategy.html): the model gets
NO distance-to-known-fault feature. It must generalise the fault signature to
places the catalogue does not cover - that is the scored population (the
private expert-labelled "new faults" absent from the USGS database).

Negative sampling mixes
  * hard negatives: valid non-fault pixels within 1.5 km of a known fault
    (places where experts mapped around but did NOT map a fault), and
  * background negatives: uniform valid non-fault pixels.

Outputs (DATA_DIR/artifacts):
  blind_model.pkl          fitted HistGradientBoostingClassifier
  train_report.json        sampling, fit params, pixel-holdout AUC/brier
  p_model.npy              (H, W) float32 probability over full footprint
"""

from __future__ import annotations

import json
import pickle
import sys
import time

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from paths import ARTIFACT_DIR, CACHE_NPZ, LABELS_TIF, ensure_data

NEG_PER_POS_HARD = 2
NEG_PER_POS_BG = 2
SEED = 20260926


def load_labels() -> np.ndarray:
    with rasterio.open(LABELS_TIF) as src:
        lab = src.read(1)
        nod = src.nodata
    truth = np.where(lab == nod, 0, lab).astype(np.int8)
    return truth


def main() -> None:
    ensure_data()
    t0 = time.time()
    cache = np.load(CACHE_NPZ, allow_pickle=False)
    X, valid = cache["X"], cache["valid"]
    names = list(cache["names"])
    H, W = int(cache["shape"][0]), int(cache["shape"][1])
    truth = load_labels()
    assert truth.shape == (H, W)

    flat_valid = valid.ravel()
    flat_fault = (truth > 0).ravel()
    idx_valid = np.flatnonzero(flat_valid)
    # X rows are ordered by grid-flat index of valid pixels; map grid -> row
    row_of = np.full(H * W, -1, dtype=np.int64)
    row_of[idx_valid] = np.arange(len(idx_valid))
    pos_idx = np.flatnonzero(flat_valid & flat_fault)
    neg_pool = np.flatnonzero(flat_valid & ~flat_fault)
    print(f"valid={len(idx_valid)} pos={len(pos_idx)} neg_pool={len(neg_pool)}")

    # hard negatives: within 15 px (1.5 km) of any fault, inside footprint
    dist_fault = distance_transform_edt(~flat_fault.reshape(H, W))
    near = (dist_fault <= 15.0).ravel()
    hard_pool = neg_pool[near.ravel()[neg_pool]]
    rng = np.random.default_rng(SEED)
    n_hard = len(pos_idx) * NEG_PER_POS_HARD
    n_bg = len(pos_idx) * NEG_PER_POS_BG
    hard_sel = rng.choice(hard_pool, size=n_hard, replace=False)
    bg_pool = neg_pool[~near.ravel()[neg_pool]]
    bg_sel = rng.choice(bg_pool, size=n_bg, replace=False)
    neg_idx = np.concatenate([hard_sel, bg_sel])
    rng.shuffle(neg_idx)

    rows = row_of[np.concatenate([pos_idx, neg_idx])]
    y = np.concatenate([np.ones(len(pos_idx)), np.zeros(len(neg_idx))]).astype(int)
    order = rng.permutation(len(rows))
    rows, y = rows[order], y[order]
    Xs = X[rows]
    print(f"training set: {len(rows)} rows x {Xs.shape[1]} cols "
          f"(pos {int(y.sum())})", flush=True)

    # pixel-level holdout for a sanity AUC (NOT spatial - see tune_policy.py
    # for the spatially-honest evaluation)
    from sklearn.metrics import roc_auc_score, brier_score_loss
    from sklearn.ensemble import HistGradientBoostingClassifier

    n_hold = len(rows) // 5
    Xtr, ytr = Xs[n_hold:], y[n_hold:]
    Xho, yho = Xs[:n_hold], y[:n_hold]

    clf = HistGradientBoostingClassifier(
        max_iter=350, learning_rate=0.08, max_leaf_nodes=63,
        min_samples_leaf=60, l2_regularization=1.0,
        early_stopping=False, random_state=SEED)
    clf.fit(Xtr, ytr)
    p_ho = clf.predict_proba(Xho)[:, 1]
    report = {
        "seed": SEED,
        "n_features": len(names),
        "feature_names": names,
        "n_train": int(len(Xtr)), "n_holdout": int(len(Xho)),
        "holdout_auc": float(roc_auc_score(yho, p_ho)),
        "holdout_brier": float(brier_score_loss(yho, p_ho)),
        "neg_per_pos_hard": NEG_PER_POS_HARD,
        "neg_per_pos_bg": NEG_PER_POS_BG,
        "note": "holdout is random pixels, not spatial blocks; spatial "
                "generalisation is measured by tune_policy.py",
    }
    print(json.dumps({k: v for k, v in report.items()
                      if k != "feature_names"}, indent=1))

    # refit on everything, then predict the full grid
    clf.fit(Xs, y)
    del Xs
    p_full = np.zeros(int(flat_valid.sum()), dtype=np.float32)
    chunk = 400_000
    for i in range(0, len(X), chunk):
        p_full[i:i + chunk] = clf.predict_proba(X[i:i + chunk])[:, 1].astype(np.float32)
    p_map = np.full((H, W), np.nan, dtype=np.float32)
    p_map[valid] = p_full

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "blind_model.pkl").write_bytes(pickle.dumps(clf))
    (ARTIFACT_DIR / "train_report.json").write_text(json.dumps(report, indent=1))
    np.save(ARTIFACT_DIR / "p_model.npy", p_map)
    print("holdout AUC:", round(report["holdout_auc"], 4))
    print("p_model stats: p50", float(np.nanpercentile(p_map, 50)),
          "p99", float(np.nanpercentile(p_map, 99)),
          "p99.9", float(np.nanpercentile(p_map, 99.9)))
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
