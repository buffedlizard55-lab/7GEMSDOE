"""Pre-registered H9b: GeoDAWN radiometric lineaments under geographic CV.

Primary arms on identical support, folds, samples and LightGBM settings:
* bands19: the supplied competition features;
* rad_raw: the four independently quantised K/Th/U/total-count grids;
* rad_lineament: rad_raw plus the fixed mask-safe 100/300 m derivatives in
  radiometric_features.py.

Promotion rule (frozen before measurement): rad_lineament must exceed BOTH
bands19 and rad_raw in pooled top-f coverage skill at 1% and 2%, and beat the
stronger comparator in at least 4/5 individual folds at each density. Ridge-NMS
results are secondary. No submission is generated regardless of outcome.

The labels are known catalogue faults, not hidden competition truth. This test
measures geographic localisation of catalogue-like faults and cannot estimate a
leaderboard score or verify a newly discovered fault/geothermal resource.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation
from sklearn.metrics import roc_auc_score

import emission as EM
import lidar_model as LM
import paths
import radiometric_features as RF
import random_baseline as RB
from metric import dtvi_components

ROOT = Path(__file__).resolve().parents[1]
RAD = ROOT / "external" / "geodawn_rad" / "geodawn_rad_u8.tif"
DENSITIES = (0.005, 0.01, 0.02, 0.03)
SEED = 20260926
PRIMARY = "rad_lineament"
COMPARATORS = ("bands19", "rad_raw")
ARMS = ("bands19", "rad_raw", "rad_lineament")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_metadata_inputs():
    """Load compact inputs and scan 19-band validity without retaining bands."""
    paths.ensure_data()
    with rasterio.open(paths.TEMPLATE_TIF) as template:
        footprint = np.isfinite(template.read(1))
        expected = (template.shape, template.crs, template.transform)
    with rasterio.open(paths.LABELS_TIF) as src:
        if (src.shape, src.crs, src.transform) != expected:
            raise ValueError("labels do not match the competition template grid")
        labels = src.read(1)
    band_valid = footprint.copy()
    with rasterio.open(paths.FEATURES_TIF) as src:
        if (src.shape, src.crs, src.transform) != expected:
            raise ValueError("supplied bands do not match the competition grid")
        if src.count != 19:
            raise ValueError(f"expected 19 supplied bands, found {src.count}")
        for band in range(1, src.count + 1):
            values = src.read(band)
            band_valid &= np.isfinite(values) & (values > -1e30)
    with rasterio.open(RAD) as src:
        if (src.shape, src.crs, src.transform) != expected:
            raise ValueError("GeoDAWN product does not match the competition grid")
        names = list(src.descriptions)
        if names != list(RF.CHANNELS):
            raise ValueError(f"unexpected GeoDAWN channels: {names}")
        raw_u8 = src.read()
        if raw_u8.dtype != np.uint8:
            raise ValueError(f"expected compact uint8 radiometrics, found {raw_u8.dtype}")
    rad_valid = np.all(raw_u8 > 0, axis=0)
    return labels, footprint, raw_u8, rad_valid, band_valid


def load_band_features() -> tuple[list[np.ndarray], list[str]]:
    """Load the baseline only for its arm; caller releases it before H9b."""
    with rasterio.open(paths.FEATURES_TIF) as src:
        bands = src.read(out_dtype="float32")
    bands[bands < -1e30] = np.nan
    return [bands[i] for i in range(bands.shape[0])], [
        f"b{i + 1}" for i in range(bands.shape[0])]


def coverage_at_density(score: np.ndarray, truth: np.ndarray,
                        test: np.ndarray, density: float,
                        candidates: np.ndarray | None = None):
    k = max(1, int(round(density * int(test.sum()))))
    domain = test if candidates is None else (test & candidates)
    pred = EM.top_k_mask(score, domain, k).astype(np.float64)
    components = dtvi_components(np.where(test, pred, np.nan),
                                  np.where(test, truth, 0))
    coverage = components["TP_w"] / max(components["n_truth"], 1)
    return float(coverage), components


def model_for(rounds: int):
    import lightgbm as lgb
    return lgb.LGBMClassifier(
        n_estimators=rounds, learning_rate=0.05, num_leaves=63,
        min_child_samples=100, subsample=0.8, subsample_freq=1,
        colsample_bytree=0.8, reg_lambda=5.0, random_state=SEED,
        n_jobs=2, verbose=-1)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=(
        ROOT / "knowledge" / "session7" / "radiometric_lineament_experiment.json"))
    parser.add_argument("--n-neg", type=int, default=120_000)
    parser.add_argument("--n-pos", type=int, default=40_000)
    parser.add_argument("--rounds", type=int, default=300)
    args = parser.parse_args(argv)
    if args.n_neg < 1 or args.n_pos < 1 or args.rounds < 1:
        parser.error("sample sizes and rounds must be positive")

    started = time.monotonic()
    labels, footprint, rad_u8, rad_valid, band_valid = load_metadata_inputs()
    h, w = labels.shape
    universe = band_valid & rad_valid
    truth = (labels == 1) & universe
    if not universe.any() or not truth.any():
        raise ValueError("matched radiometric/band support has no labelled pixels")

    folds = LM.block_folds((h, w), seed=SEED)
    near = binary_dilation(truth, iterations=2)
    rng = np.random.default_rng(SEED)
    plans = []
    for fold in range(5):
        test = universe & (folds == fold)
        buffer = binary_dilation(folds == fold, iterations=10)
        train = universe & ~buffer
        pos_idx = np.flatnonzero((truth & train).ravel())
        neg_idx = np.flatnonzero((train & ~near).ravel())
        pos_idx = rng.choice(pos_idx, min(args.n_pos, pos_idx.size), replace=False)
        neg_idx = rng.choice(neg_idx, min(args.n_neg, neg_idx.size), replace=False)
        plans.append({
            "test": test,
            "test_idx": np.flatnonzero(test.ravel()),
            "train_idx": np.concatenate((pos_idx, neg_idx)),
            "y": np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)],
            "train_pos": int(pos_idx.size),
            "train_neg": int(neg_idx.size),
        })
    del near, folds

    random_coverage = {str(f): RB.coverage_random(f) for f in DENSITIES}
    report = {
        "status": "measured_catalogue_diagnostic",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "pre_registration": __doc__.strip().splitlines(),
        "hypothesis": (
            "H9b: fixed mask-safe multiscale spatial boundaries in independent "
            "GeoDAWN K/Th/U/TC improve geographic fault localisation over both "
            "raw radiometrics and the supplied 19 bands."),
        "primary_arm": PRIMARY,
        "comparators": list(COMPARATORS),
        "promotion_rule": (
            "rad_lineament > both bands19 and rad_raw pooled at 1% and 2%, "
            "and > the stronger comparator in >=4/5 folds at both densities"),
        "protocol": (
            "H4 5x5 geographic blocks assigned to five folds; 10-pixel (1 km) "
            "test buffer; identical matched support/training samples/learner; "
            "top-f official-kernel coverage relative to exact random coverage"),
        "feature_policy": {
            "scales_pixels": list(RF.SIGMAS),
            "nominal_scales_m": [100, 300],
            "missing_data": (
                "normalised convolution plus a one-cell derivative-support erosion; "
                "zero-coded survey edges are not treated as geological edges"),
            "ratio_exclusion": (
                "No K/Th, K/U or Th/U ratios: each compact source channel was "
                "independently quantised, so ratios would not retain physical meaning."),
        },
        "source": {
            "doi": "10.5066/P93LGLVQ",
            "sciencebase_item": "657e1d85d34e23d3533209f7",
            "product": str(RAD.relative_to(ROOT)),
            "sha256": sha256_file(RAD),
            "channels": list(RF.CHANNELS),
            "quantisation": (
                "Per-channel 1st-99th-percentile uint8 1..255 in the runner product; "
                "0 is missing. Values are not original physical concentrations."),
        },
        "input_sha256": {
            "training_features": sha256_file(paths.FEATURES_TIF),
            "existing_faults": sha256_file(paths.LABELS_TIF),
            "template": sha256_file(paths.TEMPLATE_TIF),
        },
        "universe_px": int(universe.sum()),
        "positives_in_universe": int(truth.sum()),
        "rad_support_px": int((band_valid & rad_valid).sum()),
        "densities": list(DENSITIES),
        "random_coverage": random_coverage,
        "fold_seed": SEED,
        "sample_sizes_max": {"positive": args.n_pos, "negative": args.n_neg},
        "learner": {
            "library": "LightGBM", "version": None,
            "n_estimators": args.rounds, "learning_rate": 0.05,
            "num_leaves": 63, "min_child_samples": 100,
            "subsample": 0.8, "colsample_bytree": 0.8,
            "reg_lambda": 5.0, "random_state": SEED,
        },
        "execution_note": (
            "A pre-measurement attempt retaining the optional fused diagnostic and "
            "all arrays simultaneously was killed by the sandbox memory limit. The "
            "diagnostic-only fused arm was removed and arms are loaded sequentially; "
            "the three primary arms, samples, folds and promotion rule are unchanged."),
        "folds": {
            str(fold): {
                "test_px": int(plan["test"].sum()),
                "test_pos": int((truth & plan["test"]).sum()),
                "train_pos": plan["train_pos"],
                "train_neg": plan["train_neg"],
                "arms": {},
            }
            for fold, plan in enumerate(plans)
        },
        "caveats": [
            "Known catalogue traces are the only truth; this is not a hidden-test or leaderboard estimate.",
            "The source rasters were globally warped and quantised before folds; the transform is unsupervised but transductive.",
            "Survey acquisition blocks are not isolated by the 5x5 folds; a leave-one-block-out check remains required.",
            "Radiometric gradients can mark lithologic/soil/moisture/vegetation/acquisition boundaries rather than faults.",
            "No geochemical ratios are computed from independently quantised channels.",
            "No submission is generated; H1 remains the pending decisive upload.",
        ],
    }
    import lightgbm as lgb
    report["learner"]["version"] = lgb.__version__

    pooled = {arm: {str(f): [0.0, 0] for f in DENSITIES} for arm in ARMS}
    pooled_nms = {arm: {str(f): [0.0, 0] for f in DENSITIES} for arm in ARMS}
    exact_fold_multiple: dict[tuple[int, str, float], float] = {}
    importances: dict[str, float] = {}

    def evaluate_arm(arm: str, features: list[np.ndarray], feature_names: list[str]):
        for fold, plan in enumerate(plans):
            train_idx, y = plan["train_idx"], plan["y"]
            X = np.stack([feature.ravel()[train_idx] for feature in features], axis=1)
            model = model_for(args.rounds)
            model.fit(X, y)
            score = np.full(h * w, -np.inf, np.float32)
            test_idx = plan["test_idx"]
            for offset in range(0, test_idx.size, 400_000):
                chunk = test_idx[offset:offset + 400_000]
                X_test = np.stack(
                    [feature.ravel()[chunk] for feature in features], axis=1)
                score[chunk] = model.booster_.predict(X_test)
            score = score.reshape(h, w)
            test = plan["test"]
            auc = float(roc_auc_score(truth[test], score[test]))
            ridge = EM.ridge_nms(np.where(test, score, 0.0), test)
            arm_report = {"auc": round(auc, 6), "skill": {}, "skill_nms": {}}
            for density in DENSITIES:
                key = str(density)
                coverage, components = coverage_at_density(
                    score, truth.astype(np.int8), test, density)
                multiple = coverage / random_coverage[key]
                exact_fold_multiple[(fold, arm, density)] = multiple
                arm_report["skill"][key] = {
                    "coverage": round(coverage, 6),
                    "multiple": round(multiple, 6),
                    "dti_known": round(float(
                        components["TP_w"] /
                        (components["TP_w"] + 0.2 * components["FP_w"]
                         + 0.8 * components["FN_w"] + 1e-12)), 6),
                }
                pooled[arm][key][0] += components["TP_w"]
                pooled[arm][key][1] += components["n_truth"]
                nms_coverage, nms_components = coverage_at_density(
                    score, truth.astype(np.int8), test, density, candidates=ridge)
                arm_report["skill_nms"][key] = {
                    "coverage": round(nms_coverage, 6),
                    "multiple": round(nms_coverage / random_coverage[key], 6),
                }
                pooled_nms[arm][key][0] += nms_components["TP_w"]
                pooled_nms[arm][key][1] += nms_components["n_truth"]
            report["folds"][str(fold)]["arms"][arm] = arm_report
            if arm == PRIMARY:
                gains = model.booster_.feature_importance("gain")
                for name, gain in zip(feature_names, gains):
                    importances[name] = importances.get(name, 0.0) + float(gain)
            print(f"fold {fold} {arm:15s} auc={auc:.4f} " + " ".join(
                f"f{density:g}:x{arm_report['skill'][str(density)]['multiple']:.3f}"
                for density in DENSITIES), flush=True)
            del model, X, score, ridge

    # Sequential arm loading is scientifically equivalent and keeps peak RSS
    # below the sandbox limit. Process compact radiometrics before the 19-band
    # float32 baseline so the large arrays never coexist.
    raw_features = [(rad_u8[i].astype(np.float16) / np.float16(255.0))
                    for i in range(rad_u8.shape[0])]
    raw_names = [f"rad_{name}_rank" for name in RF.CHANNELS]
    evaluate_arm("rad_raw", raw_features, raw_names)
    derived, derived_names = RF.build_lineament_features(rad_u8, rad_valid)
    report["feature_policy"]["derived_count"] = len(derived_names)
    report["feature_policy"]["derived_names"] = derived_names
    evaluate_arm("rad_lineament", raw_features + derived, raw_names + derived_names)
    del derived, raw_features
    gc.collect()
    band_features, band_names = load_band_features()
    evaluate_arm("bands19", band_features, band_names)
    del band_features
    gc.collect()

    def pool_summary(values):
        return {
            arm: {
                density: {
                    "coverage": round(total / max(count, 1), 6),
                    "multiple": round((total / max(count, 1)) /
                                      random_coverage[density], 6),
                }
                for density, (total, count) in by_density.items()
            }
            for arm, by_density in values.items()
        }

    report["pooled"] = pool_summary(pooled)
    report["pooled_nms"] = pool_summary(pooled_nms)
    wins = {
        str(density): sum(
            exact_fold_multiple[(fold, PRIMARY, density)] > max(
                exact_fold_multiple[(fold, comparator, density)]
                for comparator in COMPARATORS)
            for fold in range(5))
        for density in DENSITIES
    }
    report["lineament_beats_stronger_comparator_folds"] = wins
    report["promotion_rule_met"] = bool(
        all(report["pooled"][PRIMARY][str(density)]["multiple"] >
            max(report["pooled"][comparator][str(density)]["multiple"]
                for comparator in COMPARATORS)
            for density in (0.01, 0.02))
        and wins["0.01"] >= 4 and wins["0.02"] >= 4)
    total_gain = sum(importances.values()) or 1.0
    report["lineament_gain_share"] = dict(sorted(
        ((name, round(gain / total_gain, 6)) for name, gain in importances.items()),
        key=lambda item: -item[1]))
    report["seconds"] = round(time.monotonic() - started, 1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, allow_nan=False) + "\n")
    print(json.dumps({
        "pooled": report["pooled"],
        "lineament_beats_stronger_comparator_folds": wins,
        "promotion_rule_met": report["promotion_rule_met"],
    }, indent=1), flush=True)
    return report


if __name__ == "__main__":
    main()
