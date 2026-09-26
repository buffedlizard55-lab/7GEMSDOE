"""Pseudo-new-fault holdout experiment: the only locally-honest proxy for
leaderboard performance.

Why: both prize rounds are scored against expert-labelled faults that are NOT
in the public USGS catalogue (rules §1.1/§3.3/§3.5 - see
knowledge/00_competition_facts.md). So catalog DTI is a plumbing monitor, not
a score proxy. This script simulates the real situation:

  1. Hide all catalogue faults inside a random set of spatial blocks
     ("pseudo-new faults", ~20% of fault pixels).
  2. Train the blind detector on the remaining catalogue only.
  3. Build candidate submissions from (a) a proximity prior around the
     remaining catalogue faults and (b) the detector's probabilities.
  4. Score each candidate with the official DTI against the HIDDEN faults,
     false positives counted over the whole footprint - exactly how the
     platform scores against its private new-fault set.

The winning policy (and all baselines) are written to
DATA_DIR/artifacts/policy_report.json; build_submission.py applies the same
policy using the full-catalogue production model.
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, binary_dilation
from sklearn.ensemble import HistGradientBoostingClassifier

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from metric import dtvi, dtvi_components  # noqa: E402
from paths import ARTIFACT_DIR, CACHE_NPZ, LABELS_TIF, ensure_data  # noqa: E402

SEED = 777
N_BLOCKS = 12           # 12x12 block grid over the raster
TARGET_HOLDOUT_FRACTION = 0.20
NEG_PER_POS_HARD = 2
NEG_PER_POS_BG = 2


def load_truth():
    with rasterio.open(LABELS_TIF) as src:
        lab = src.read(1)
        nod = src.nodata
    return (np.where(lab == nod, 0, lab) > 0)


def block_holdout(truth: np.ndarray, rng):
    H, W = truth.shape
    by = np.minimum((np.arange(H) * N_BLOCKS // H)[:, None] * np.ones((1, W)),
                    N_BLOCKS - 1).astype(int)
    bx = np.minimum((np.arange(W) * N_BLOCKS // W)[None, :] * np.ones((H, 1)),
                    N_BLOCKS - 1).astype(int)
    bid = by * N_BLOCKS + bx
    fault_px_per_block = np.bincount(bid[truth].ravel(), minlength=N_BLOCKS * N_BLOCKS)
    total = fault_px_per_block.sum()
    candidate_blocks = np.nonzero(fault_px_per_block > 0)[0]
    order = rng.permutation(candidate_blocks)
    chosen, held = set(), 0
    for b in order:
        if held >= TARGET_HOLDOUT_FRACTION * total:
            break
        chosen.add(int(b))
        held += fault_px_per_block[b]
    held_mask = np.isin(bid, sorted(chosen))
    return held_mask, held / total, len(chosen)


def train_blind(X, valid, truth, train_fault_mask, row_of, seed):
    H, W = truth.shape
    # Exclude held geography and a 300 m context/metric buffer from ALL samples.
    excluded = binary_dilation(train_fault_mask, iterations=3)
    eligible = valid & ~excluded
    visible_truth = truth & eligible
    flat_valid = eligible.ravel()
    pos_idx = np.flatnonzero(flat_valid & visible_truth.ravel())
    neg_pool = np.flatnonzero(flat_valid & ~visible_truth.ravel())
    # Previously used full truth here: hidden labels leaked into hard-negative sampling.
    dist_fault = distance_transform_edt(~visible_truth)
    near = (dist_fault <= 15.0).ravel()
    hard_pool = neg_pool[near[neg_pool]]
    bg_pool = neg_pool[~near[neg_pool]]
    rng = np.random.default_rng(seed)
    n_hard = min(len(hard_pool), len(pos_idx) * NEG_PER_POS_HARD)
    n_bg = min(len(bg_pool), len(pos_idx) * NEG_PER_POS_BG)
    neg_idx = np.concatenate([
        rng.choice(hard_pool, size=n_hard, replace=False),
        rng.choice(bg_pool, size=n_bg, replace=False)])
    rows = row_of[np.concatenate([pos_idx, neg_idx])]
    y = np.concatenate([np.ones(len(pos_idx)), np.zeros(len(neg_idx))]).astype(int)
    order = rng.permutation(len(rows))
    Xs = X[rows[order]]
    ys = y[order]
    clf = HistGradientBoostingClassifier(
        max_iter=350, learning_rate=0.08, max_leaf_nodes=63,
        min_samples_leaf=60, l2_regularization=1.0,
        early_stopping=False, random_state=seed)
    clf.fit(Xs, ys)
    return clf, len(pos_idx), len(neg_idx)


def proximity_field(truth_mask: np.ndarray, radius_px: float, height: float):
    if radius_px <= 0:
        return truth_mask.astype(np.float32)
    d = distance_transform_edt(~truth_mask)
    p = np.maximum(1.0 - d / radius_px, 0.0) * height
    p[truth_mask] = 1.0
    return p.astype(np.float32)


def model_emission(p_map, tau, scale):
    q = np.clip((p_map - tau) / max(1e-9, 1.0 - tau), 0.0, 1.0)
    return (q * scale).astype(np.float32)


def main():
    ensure_data()
    t0 = time.time()
    cache = np.load(CACHE_NPZ, allow_pickle=False)
    X, valid = cache["X"], cache["valid"]
    H, W = int(cache["shape"][0]), int(cache["shape"][1])
    truth = load_truth()
    idx_valid = np.flatnonzero(valid.ravel())
    row_of = np.full(H * W, -1, dtype=np.int32)
    row_of[idx_valid] = np.arange(len(idx_valid))

    rng = np.random.default_rng(SEED)
    held_mask, held_frac, n_blocks = block_holdout(truth, rng)
    hidden = truth & held_mask
    remaining = truth & ~held_mask
    n_hidden = int(hidden.sum())
    print(f"blocks held out: {n_blocks}; hidden fault px: {n_hidden} "
          f"({held_frac:.1%} of {int(truth.sum())})", flush=True)

    clf, n_pos, n_neg = train_blind(X, valid, truth, held_mask, row_of, SEED + 1)
    print(f"trained on pos={n_pos} neg={n_neg}", flush=True)

    p_full = np.zeros(len(idx_valid), dtype=np.float32)
    for i in range(0, len(X), 400_000):
        p_full[i:i + 400_000] = clf.predict_proba(X[i:i + 400_000])[:, 1]
    p_map = np.zeros((H, W), dtype=np.float32)
    p_map[valid] = p_full
    del X

    hidden_f = hidden.astype(np.float64)

    rows = []

    def record(name, pred):
        pred = np.where(valid, pred, 0.0).astype(np.float64)
        c = dtvi_components(pred, hidden_f)
        c["DTI"] = dtvi(pred, hidden_f)
        c["strategy"] = name
        rows.append(c)
        print(f"{name:52s} DTI={c['DTI']:.4f} mass={c['predicted_mass']:.0f}",
              flush=True)

    # baselines
    record("all zeros", np.zeros((H, W)))
    record("all ones (blanket)", np.ones((H, W)))
    record("remaining catalogue only", remaining.astype(np.float32))
    record("hidden faults (oracle upper bound)", hidden.astype(np.float32))

    # proximity-only
    for r, h in [(1, 0.35), (2, 0.35), (3, 0.35), (2, 0.2), (3, 0.2)]:
        record(f"proximity r={r} h={h}", proximity_field(remaining, r, h))

    # model-only emissions
    for tau, s in [(0.3, 0.5), (0.5, 0.5), (0.5, 0.8), (0.6, 0.8),
                   (0.7, 0.8), (0.7, 1.0), (0.8, 1.0)]:
        record(f"model tau={tau} s={s}", model_emission(p_map, tau, s))

    # blends: max(proximity, model emission)
    best = (None, -1.0)
    for r, h in [(0, 1.0), (1, 0.35), (2, 0.35), (3, 0.3)]:
        prox = proximity_field(remaining, r, h if r else 1.0)
        for tau, s in [(0.5, 0.5), (0.6, 0.7), (0.7, 0.8), (0.7, 1.0),
                       (0.8, 1.0)]:
            emis = model_emission(p_map, tau, s)
            name = f"blend prox(r={r},h={h}) + model(tau={tau},s={s})"
            pred = np.maximum(prox, emis)
            pred = np.where(valid, pred, 0.0).astype(np.float64)
            c = dtvi_components(pred, hidden_f)
            c["DTI"] = dtvi(pred, hidden_f)
            c["strategy"] = name
            rows.append(c)
            print(f"{name:52s} DTI={c['DTI']:.4f} mass={c['predicted_mass']:.0f}",
                  flush=True)
            if c["DTI"] > best[1]:
                best = ({"prox_r": r, "prox_h": h, "tau": tau, "scale": s},
                        c["DTI"])

    report = {
        "seed": SEED,
        "n_blocks_grid": N_BLOCKS,
        "blocks_held_out": n_blocks,
        "hidden_fault_px": n_hidden,
        "hidden_fraction": held_frac,
        "trained_pos": n_pos, "trained_neg": n_neg,
        "best_policy": best[0],
        "best_proxy_dti": best[1],
        "rows": rows,
        "elapsed_s": round(time.time() - t0, 1),
        "caveat": "proxy DTI against hidden catalogue faults; the platform's "
                  "private new faults are a different (expert-labelled) "
                  "population - treat as ranking signal, not score prediction",
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "policy_report.json").write_text(json.dumps(report, indent=1))
    print("best:", json.dumps(best[0]), "proxy DTI", round(best[1], 4))
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
