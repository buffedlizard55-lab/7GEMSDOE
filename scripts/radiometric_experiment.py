"""Pre-registered H9 geographic comparison using the downloaded GeoDAWN grids.

The primary comparison is radiometric-only vs the supplied 19 bands at the
same emission densities. All four arms share exactly the same support, spatial
folds, training samples, LightGBM settings and scoring protocol as H4. The
additional lidar and combined arms are diagnostic, not alternate submission
policies. The truth is still the existing catalogue, not private test faults;
this experiment cannot estimate leaderboard score or prove fault discovery.

No submission is generated. The H1 upload remains the only pending decisive
leaderboard test; this report is a research diagnostic only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation
from sklearn.metrics import roc_auc_score

import lidar_model as LM
import paths
import random_baseline as RB
from metric import dtvi_components

ROOT = Path(__file__).resolve().parents[1]
RAD = ROOT / "external" / "geodawn_rad" / "geodawn_rad_u8.tif"
DENSITIES = (0.005, 0.01, 0.02, 0.03)
SEED = LM.SEED


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_radiometrics():
    with rasterio.open(RAD) as src:
        expected = rasterio.open(paths.TEMPLATE_TIF)
        try:
            if (src.shape != expected.shape or src.crs != expected.crs
                    or src.transform != expected.transform):
                raise ValueError("GeoDAWN product is not on the official grid")
        finally:
            expected.close()
        names = list(src.descriptions)
        if names != ["K", "Th", "U", "TC"]:
            raise ValueError(f"unexpected GeoDAWN channels: {names}")
        raw = src.read()
    valid = np.all(raw > 0, axis=0)
    features = [raw[i].astype(np.float32) for i in range(raw.shape[0])]
    return features, names, valid


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path,
                    default=ROOT / "knowledge" / "session6" / "geodawn_experiment.json")
    ap.add_argument("--n-neg", type=int, default=120000)
    ap.add_argument("--n-pos", type=int, default=40000)
    ap.add_argument("--rounds", type=int, default=300)
    args = ap.parse_args(argv)

    t0 = time.time()
    bands, lab, foot, lid = LM.load_stack()
    rad, rad_names, radok = load_radiometrics()
    H, W = lab.shape
    band_valid = foot & np.all(np.isfinite(bands), axis=0)
    lidok = np.nan_to_num(lid["valid"]) > 0.5
    # Matched coverage across every arm; avoids giving rad or lidar an easier
    # denominator merely because its source footprint differs.
    universe = band_valid & lidok & radok
    pos = (lab == 1) & universe
    if not universe.any() or not pos.any():
        raise ValueError("common GeoDAWN/lidar/bands support has no valid labelled pixels")

    lfe, lnames = LM.lidar_feature_block(lid)
    import lightgbm as lgb

    band_arm = ([bands[i] for i in range(bands.shape[0])],
                [f"b{i+1}" for i in range(bands.shape[0])])
    rad_arm = (rad, [f"rad_{name}" for name in rad_names])
    lidar_arm = (lfe, lnames)
    arms = {
        "bands19": band_arm,
        "rad": rad_arm,
        "lidar": lidar_arm,
        "all": (band_arm[0] + lidar_arm[0] + rad_arm[0],
                band_arm[1] + lidar_arm[1] + rad_arm[1]),
    }
    folds = LM.block_folds((H, W))
    near = binary_dilation(pos, iterations=2)
    rng = np.random.default_rng(SEED)
    report = {
        "status": "measured_catalogue_diagnostic",
        "hypothesis": "H9: independent GeoDAWN K/Th/U/TC grids improve spatial fault localisation beyond supplied bands19",
        "protocol": "H4 five geographic folds (5x5 blocks assigned to five folds), 10 px buffer, same LightGBM learner and matched support/samples; top-f skill at 0.5%, 1%, 2%, 3%",
        "primary_promotion_rule": "rad must exceed bands19 pooled at 1% and 2% and in at least 4/5 folds at each density",
        "source": {
            "doi": "10.5066/P93LGLVQ",
            "sciencebase_item": "657e1d85d34e23d3533209f7",
            "product": str(RAD.relative_to(ROOT)),
            "sha256": sha256_file(RAD),
            "channels": rad_names,
            "quantisation_note": "input product stores per-channel robust 1st-99th percentile ranks as uint8 1..255; zero is missing/outside",
        },
        "input_sha256": {
            "training_features": sha256_file(paths.FEATURES_TIF),
            "existing_faults": sha256_file(paths.LABELS_TIF),
            "template": sha256_file(paths.TEMPLATE_TIF),
            "lidar_features": sha256_file(LM.LIDAR),
        },
        "fold_seed": SEED,
        "sample_sizes": {"positive": args.n_pos, "negative": args.n_neg},
        "learner": {"library": "LightGBM", "version": lgb.__version__,
                    "n_estimators": args.rounds, "learning_rate": 0.05,
                    "num_leaves": 63, "min_child_samples": 100,
                    "subsample": 0.8, "colsample_bytree": 0.8,
                    "reg_lambda": 5.0, "random_state": SEED},
        "universe_px": int(universe.sum()),
        "positives_in_universe": int(pos.sum()),
        "lidar_support_px": int((band_valid & lidok).sum()),
        "rad_support_px": int((band_valid & radok).sum()),
        "densities": list(DENSITIES),
        "random_coverage": {str(f): RB.coverage_random(f) for f in DENSITIES},
        "folds": {},
        "caveats": [
            "Known catalogue traces are the only truth; this is not a private-test or leaderboard estimate.",
            "The model's spatial features remain subject to source/catalogue overlap and the metric's catalogue-offset error.",
            "The 100 m GeoDAWN grid is globally quantised before folds; no spatially held-out calibration bounds were fit.",
            "Acquisition-block holdout is still required; the current 5x5 folds are geographic but do not isolate all flight blocks.",
            "No submission file was generated and H1 remains the only pending decisive upload.",
        ],
    }
    pooled = {a: {str(f): [0.0, 0] for f in DENSITIES} for a in arms}
    importances = {}

    for k in range(5):
        test = universe & (folds == k)
        buf = binary_dilation(folds == k, iterations=10)
        train = universe & ~buf
        ptr = np.flatnonzero((pos & train).ravel())
        ntr = np.flatnonzero((train & ~near).ravel())
        ptr = rng.choice(ptr, min(args.n_pos, ptr.size), replace=False)
        ntr = rng.choice(ntr, min(args.n_neg, ntr.size), replace=False)
        idx = np.concatenate([ptr, ntr])
        y = np.r_[np.ones(ptr.size), np.zeros(ntr.size)]
        te_idx = np.flatnonzero(test.ravel())
        fold_rep = {"test_px": int(test.sum()),
                    "test_pos": int((pos & test).sum()),
                    "train_pos": int(ptr.size), "train_neg": int(ntr.size),
                    "arms": {}}
        for arm, (features, feature_names) in arms.items():
            X = np.stack([f.ravel()[idx] for f in features], axis=1)
            model = lgb.LGBMClassifier(
                n_estimators=args.rounds, learning_rate=0.05, num_leaves=63,
                min_child_samples=100, subsample=0.8, subsample_freq=1,
                colsample_bytree=0.8, reg_lambda=5.0,
                random_state=SEED, n_jobs=2, verbose=-1)
            model.fit(X, y)
            scores = np.full(H * W, -np.inf, np.float32)
            for start in range(0, te_idx.size, 400000):
                chunk = te_idx[start:start + 400000]
                X_test = np.stack([f.ravel()[chunk] for f in features], axis=1)
                scores[chunk] = model.predict_proba(X_test)[:, 1]
            scores = scores.reshape(H, W)
            auc = roc_auc_score(pos[test], scores[test])
            arm_rep = {"auc": round(float(auc), 4), "skill": {}}
            truth = pos.astype(np.int8)
            for density in DENSITIES:
                coverage, metric = LM.coverage_at_density(scores, truth, test, density)
                multiple = coverage / RB.coverage_random(density)
                arm_rep["skill"][str(density)] = {
                    "coverage": round(float(coverage), 4),
                    "multiple": round(float(multiple), 3),
                    "dti_known": round(float(
                        metric["TP_w"] / (metric["TP_w"] + .2 * metric["FP_w"]
                                          + .8 * metric["FN_w"] + 1e-9)), 4),
                }
                pooled[arm][str(density)][0] += metric["TP_w"]
                pooled[arm][str(density)][1] += metric["n_truth"]
            fold_rep["arms"][arm] = arm_rep
            if arm == "all":
                for name, value in zip(feature_names,
                                       model.booster_.feature_importance("gain")):
                    importances[name] = importances.get(name, 0.0) + float(value)
            print(f"fold {k} {arm:8s} auc={auc:.4f} " + " ".join(
                f"f{f:g}:x{arm_rep['skill'][str(f)]['multiple']}" for f in DENSITIES),
                flush=True)
            del model, X, scores
        report["folds"][str(k)] = fold_rep

    report["pooled"] = {
        arm: {
            density: {
                "coverage": round(values[0] / max(values[1], 1), 4),
                "multiple": round(values[0] / max(values[1], 1)
                                  / RB.coverage_random(float(density)), 3),
            }
            for density, values in by_density.items()
        }
        for arm, by_density in pooled.items()
    }
    wins = {
        str(f): sum(
            report["folds"][str(k)]["arms"]["rad"]["skill"][str(f)]["multiple"]
            > report["folds"][str(k)]["arms"]["bands19"]["skill"][str(f)]["multiple"]
            for k in range(5))
        for f in DENSITIES
    }
    report["rad_beats_bands19_folds"] = wins
    report["promotion_rule_met"] = bool(
        all(report["pooled"]["rad"][str(f)]["multiple"]
            > report["pooled"]["bands19"][str(f)]["multiple"]
            for f in (0.01, 0.02))
        and wins["0.01"] >= 4 and wins["0.02"] >= 4)
    total_gain = sum(importances.values()) or 1.0
    report["all_arm_gain_share_top20"] = dict(sorted(
        ((n, round(v / total_gain, 4)) for n, v in importances.items()),
        key=lambda row: -row[1])[:20])
    report["seconds"] = round(time.time() - t0, 1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"pooled": report["pooled"],
                      "rad_beats_bands19_folds": wins,
                      "promotion_rule_met": report["promotion_rule_met"]}, indent=1))


if __name__ == "__main__":
    main()
