"""Pre-registered H9c geographic test of official GeoDAWN extension grids.

Primary: contractor Th/K, U/K and U/Th ratio grids versus both raw K/Th/U/TC
and supplied bands19. Diagnostic only: TMI upward-continued to 150 m, alone and
with the ratios. See knowledge/session7/h9c_protocol.md for the frozen protocol
and promotion rule. No submission is generated.
"""
from __future__ import annotations

import argparse
import gc
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
import radiometric_lineament_experiment as H9B
import random_baseline as RB

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "external" / "geodawn_extensions" / "geodawn_extensions_u8.tif"
EXT_NAMES = ("ThK", "UK", "UTh", "TMI_up150")
DENSITIES = H9B.DENSITIES
SEED = H9B.SEED
PRIMARY = "ratios3"
COMPARATORS = ("bands19", "rad_raw")
ARMS = ("bands19", "rad_raw", "ratios3", "up150", "extensions4")


def load_extension(expected_grid):
    with rasterio.open(EXT) as src:
        if (src.shape, src.crs, src.transform) != expected_grid:
            raise ValueError("GeoDAWN extension product does not match the common grid")
        if tuple(src.descriptions) != EXT_NAMES:
            raise ValueError(f"unexpected extension channels: {src.descriptions}")
        array = src.read()
        if array.dtype != np.uint8:
            raise ValueError(f"expected compact uint8 extensions, found {array.dtype}")
    return array, np.all(array > 0, axis=0)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=(
        ROOT / "knowledge" / "session7" / "geodawn_extension_experiment.json"))
    parser.add_argument("--n-neg", type=int, default=120_000)
    parser.add_argument("--n-pos", type=int, default=40_000)
    parser.add_argument("--rounds", type=int, default=300)
    args = parser.parse_args(argv)
    if args.n_neg < 1 or args.n_pos < 1 or args.rounds < 1:
        parser.error("sample sizes and rounds must be positive")

    started = time.monotonic()
    labels, footprint, raw_u8, rad_valid, band_valid = H9B.load_metadata_inputs()
    with rasterio.open(paths.TEMPLATE_TIF) as template:
        expected_grid = (template.shape, template.crs, template.transform)
    extensions, extension_valid = load_extension(expected_grid)
    h, w = labels.shape
    universe = band_valid & rad_valid & extension_valid
    truth = (labels == 1) & universe
    if not universe.any() or not truth.any():
        raise ValueError("matched H9c support has no labelled pixels")

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
            "train_pos": int(pos_idx.size), "train_neg": int(neg_idx.size),
        })
    del near, folds

    random_coverage = {str(density): RB.coverage_random(density)
                       for density in DENSITIES}
    report = {
        "status": "measured_catalogue_diagnostic",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "pre_registration": __doc__.strip().splitlines(),
        "protocol_file": "knowledge/session7/h9c_protocol.md",
        "hypothesis": (
            "H9c: official contractor Th/K, U/K and U/Th ratio grids improve "
            "geographic catalogue-fault localisation over raw K/Th/U/TC and bands19."),
        "primary_arm": PRIMARY,
        "comparators": list(COMPARATORS),
        "promotion_rule": (
            "ratios3 > both bands19 and rad_raw pooled at 1% and 2%, and > "
            "the stronger comparator in >=4/5 folds at both densities"),
        "arms": {
            "bands19": "19 supplied numerical bands",
            "rad_raw": "compact K/Th/U/total-count ranks",
            "ratios3": "official contractor Th/K, U/K, U/Th ranks (primary)",
            "up150": "official TMI upward-continued to 150 m rank (diagnostic)",
            "extensions4": "three ratios plus up150 (diagnostic)",
        },
        "source": {
            "doi": "10.5066/P93LGLVQ",
            "sciencebase_item": "657e1d85d34e23d3533209f7",
            "readme": ("https://www.sciencebase.gov/catalog/file/get/"
                       "657e1d85d34e23d3533209f7?name=GeoDAWN_ReadMe.pdf"),
            "raw_product": str(H9B.RAD.relative_to(ROOT)),
            "raw_sha256": H9B.sha256_file(H9B.RAD),
            "extension_product": str(EXT.relative_to(ROOT)),
            "extension_sha256": H9B.sha256_file(EXT),
            "extension_channels": list(EXT_NAMES),
            "quantisation_note": (
                "Each compact channel is an independent robust uint8 rank; official "
                "ratio source grids were computed upstream from physical channels."),
        },
        "input_sha256": {
            "training_features": H9B.sha256_file(paths.FEATURES_TIF),
            "existing_faults": H9B.sha256_file(paths.LABELS_TIF),
            "template": H9B.sha256_file(paths.TEMPLATE_TIF),
        },
        "universe_px": int(universe.sum()),
        "positives_in_universe": int(truth.sum()),
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
        "folds": {
            str(fold): {
                "test_px": int(plan["test"].sum()),
                "test_pos": int((truth & plan["test"]).sum()),
                "train_pos": plan["train_pos"], "train_neg": plan["train_neg"],
                "arms": {},
            } for fold, plan in enumerate(plans)
        },
        "caveats": [
            "Catalogue truth is not hidden-fault truth or a leaderboard estimate.",
            "Ratios may express lithology, soil, moisture or alteration rather than faults.",
            "Upward-continued TMI is a transform of an existing sensor, not independent evidence.",
            "Area/acquisition-block transfer is not isolated and remains a required gate.",
            "Global source warping/quantisation is unsupervised but transductive.",
            "No submission was generated and H1 remains the only pending decisive upload.",
        ],
    }
    import lightgbm as lgb
    report["learner"]["version"] = lgb.__version__
    pooled = {arm: {str(d): [0.0, 0] for d in DENSITIES} for arm in ARMS}
    pooled_nms = {arm: {str(d): [0.0, 0] for d in DENSITIES} for arm in ARMS}
    exact: dict[tuple[int, str, float], float] = {}
    gains_by_arm: dict[str, dict[str, float]] = {}
    truth_i8 = truth.astype(np.int8)

    def evaluate(arm, features, names):
        gains = {name: 0.0 for name in names}
        for fold, plan in enumerate(plans):
            train_idx = plan["train_idx"]
            X = np.stack([feature.ravel()[train_idx] for feature in features], axis=1)
            model = H9B.model_for(args.rounds)
            model.fit(X, plan["y"])
            score = np.full(h * w, -np.inf, np.float32)
            test_idx = plan["test_idx"]
            for offset in range(0, test_idx.size, 400_000):
                chunk = test_idx[offset:offset + 400_000]
                X_test = np.stack([feature.ravel()[chunk] for feature in features], axis=1)
                score[chunk] = model.booster_.predict(X_test)
            score = score.reshape(h, w)
            test = plan["test"]
            auc = float(roc_auc_score(truth[test], score[test]))
            ridge = EM.ridge_nms(np.where(test, score, 0.0), test)
            arm_report = {"auc": round(auc, 6), "skill": {}, "skill_nms": {}}
            for density in DENSITIES:
                key = str(density)
                coverage, components = H9B.coverage_at_density(
                    score, truth_i8, test, density)
                multiple = coverage / random_coverage[key]
                exact[(fold, arm, density)] = multiple
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
                nms_cov, nms_components = H9B.coverage_at_density(
                    score, truth_i8, test, density, candidates=ridge)
                arm_report["skill_nms"][key] = {
                    "coverage": round(nms_cov, 6),
                    "multiple": round(nms_cov / random_coverage[key], 6),
                }
                pooled_nms[arm][key][0] += nms_components["TP_w"]
                pooled_nms[arm][key][1] += nms_components["n_truth"]
            for name, gain in zip(names, model.booster_.feature_importance("gain")):
                gains[name] += float(gain)
            report["folds"][str(fold)]["arms"][arm] = arm_report
            print(f"fold {fold} {arm:11s} auc={auc:.4f} " + " ".join(
                f"f{d:g}:x{arm_report['skill'][str(d)]['multiple']:.3f}"
                for d in DENSITIES), flush=True)
            del X, model, score, ridge
        total = sum(gains.values()) or 1.0
        gains_by_arm[arm] = dict(sorted(
            ((name, round(gain / total, 6)) for name, gain in gains.items()),
            key=lambda item: -item[1]))

    raw_features = [raw_u8[i].astype(np.float16) / np.float16(255)
                    for i in range(raw_u8.shape[0])]
    ext_features = [extensions[i].astype(np.float16) / np.float16(255)
                    for i in range(extensions.shape[0])]
    evaluate("rad_raw", raw_features, ["K", "Th", "U", "TC"])
    evaluate("ratios3", ext_features[:3], list(EXT_NAMES[:3]))
    evaluate("up150", ext_features[3:], [EXT_NAMES[3]])
    evaluate("extensions4", ext_features, list(EXT_NAMES))
    del raw_features, ext_features, extensions, raw_u8
    gc.collect()
    band_features, band_names = H9B.load_band_features()
    evaluate("bands19", band_features, band_names)
    del band_features
    gc.collect()

    def summarize(values):
        return {arm: {density: {
            "coverage": round(total / max(count, 1), 6),
            "multiple": round((total / max(count, 1)) / random_coverage[density], 6),
        } for density, (total, count) in by_density.items()}
                for arm, by_density in values.items()}

    report["pooled"] = summarize(pooled)
    report["pooled_nms"] = summarize(pooled_nms)
    report["gain_share"] = gains_by_arm
    wins = {str(density): sum(
        exact[(fold, PRIMARY, density)] > max(
            exact[(fold, comparator, density)] for comparator in COMPARATORS)
        for fold in range(5)) for density in DENSITIES}
    report["ratios_beats_stronger_comparator_folds"] = wins
    report["promotion_rule_met"] = bool(
        all(report["pooled"][PRIMARY][str(density)]["multiple"] > max(
            report["pooled"][comparator][str(density)]["multiple"]
            for comparator in COMPARATORS) for density in (0.01, 0.02))
        and wins["0.01"] >= 4 and wins["0.02"] >= 4)
    report["seconds"] = round(time.monotonic() - started, 1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, allow_nan=False) + "\n")
    print(json.dumps({
        "pooled": report["pooled"],
        "ratios_beats_stronger_comparator_folds": wins,
        "promotion_rule_met": report["promotion_rule_met"],
    }, indent=1), flush=True)
    return report


if __name__ == "__main__":
    main()
