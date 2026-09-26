"""Component-level pseudo-new-fault holdout.

More realistic than whole-block holdout (tune_policy.py): the USGS catalogue
is incomplete *inside* mapped regions (hidden splays, buried strands,
stepovers), so we hide random connected COMPONENTS of the catalogue (~20% of
fault pixels) and measure how well each candidate submission recovers them
under the official DTI. This estimates performance on the "near known
structure" fraction of the platform's private new faults.

Writes DATA_DIR/artifacts/component_policy_report.json.
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, label
from sklearn.ensemble import HistGradientBoostingClassifier

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from metric import dtvi, dtvi_components  # noqa: E402
from paths import ARTIFACT_DIR, CACHE_NPZ, LABELS_TIF, ensure_data  # noqa: E402
from tune_policy import (NEG_PER_POS_BG, NEG_PER_POS_HARD,  # noqa: E402
                         model_emission, proximity_field, train_blind)

SEED = 4242
TARGET_HOLDOUT_FRACTION = 0.20


def load_truth():
    with rasterio.open(LABELS_TIF) as src:
        lab = src.read(1)
        nod = src.nodata
    return (np.where(lab == nod, 0, lab) > 0)


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

    comps, n_comp = label(truth, structure=np.ones((3, 3), dtype=bool))
    sizes = np.bincount(comps.ravel())[1:]
    rng = np.random.default_rng(SEED)
    order = rng.permutation(n_comp)
    chosen, held = set(), 0
    total = int(truth.sum())
    for c in order:
        if held >= TARGET_HOLDOUT_FRACTION * total:
            break
        chosen.add(int(c) + 1)
        held += int(sizes[c])
    hidden = np.isin(comps, sorted(chosen))
    remaining = truth & ~hidden
    print(f"components: {n_comp}; hidden: {len(chosen)} comps, {int(hidden.sum())} "
          f"px ({int(hidden.sum())/total:.1%}); median hidden comp size "
          f"{int(np.median([sizes[c-1] for c in chosen]))}", flush=True)

    clf, n_pos, n_neg = train_blind(X, valid, truth, hidden, row_of, SEED + 1)
    print(f"trained pos={n_pos} neg={n_neg}", flush=True)

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
        print(f"{name:56s} DTI={c['DTI']:.4f} mass={c['predicted_mass']:.0f}",
              flush=True)

    record("all zeros", np.zeros((H, W)))
    record("all ones (blanket)", np.ones((H, W)))
    record("remaining catalogue only (core p=1)", remaining.astype(np.float32))
    record("hidden components (oracle)", hidden.astype(np.float32))

    # proximity halos around remaining catalogue
    for r, h in [(1, 0.35), (2, 0.35), (3, 0.30), (3, 0.5), (5, 0.25), (5, 0.4)]:
        record(f"proximity r={r} h={h}", proximity_field(remaining, r, h))

    # model emission alone
    for tau, s in [(0.5, 0.6), (0.6, 0.8), (0.7, 1.0)]:
        record(f"model tau={tau} s={s}", model_emission(p_map, tau, s))

    # blends
    best = (None, -1.0)
    combos = []
    for r, h in [(1, 0.35), (2, 0.35), (3, 0.30)]:
        prox = proximity_field(remaining, r, h)
        for tau, s in [(0.5, 0.6), (0.6, 0.8), (0.7, 1.0)]:
            emis = model_emission(p_map, tau, s)
            pred = np.maximum(prox, emis)
            name = f"blend prox(r={r},h={h}) | model(tau={tau},s={s})"
            pred = np.where(valid, pred, 0.0).astype(np.float64)
            c = dtvi_components(pred, hidden_f)
            c["DTI"] = dtvi(pred, hidden_f)
            c["strategy"] = name
            rows.append(c)
            print(f"{name:56s} DTI={c['DTI']:.4f} mass={c['predicted_mass']:.0f}",
                  flush=True)
            combos.append((name, c["DTI"]))
            if c["DTI"] > best[1]:
                best = ({"prox_r": r, "prox_h": h, "tau": tau, "scale": s},
                        c["DTI"])

    # persist the holdout fields so policy sweeps can re-evaluate without
    # retraining (scripts/sweep_halos.py)
    np.savez_compressed(
        ARTIFACT_DIR / "component_holdout_fields.npz",
        p_map=p_map, remaining=remaining, hidden=hidden, valid=valid,
        shape=np.array([H, W], dtype=np.int64))

    report = {
        "seed": SEED,
        "holdout": "random connected components (~20% of fault pixels)",
        "hidden_components": len(chosen),
        "hidden_fault_px": int(hidden.sum()),
        "hidden_fraction": float(hidden.sum()) / total,
        "trained_pos": n_pos, "trained_neg": n_neg,
        "best_policy": best[0],
        "best_proxy_dti": best[1],
        "rows": rows,
        "elapsed_s": round(time.time() - t0, 1),
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "component_policy_report.json").write_text(
        json.dumps(report, indent=1))
    print("best:", json.dumps(best[0]), "proxy DTI", round(best[1], 4))
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
