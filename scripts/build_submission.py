"""Build the competition submission GeoTIFF.

Policy v1 (adopted from the component-holdout proxy sweep - see
DATA_DIR/artifacts/component_policy_report.json):

  p(x) = max( halo(x), blind_emission(x) )

  halo(x)          triangular decay around every catalogue fault:
                   0.95 on fault pixels, h * max(1 - d(x)/r, 0) otherwise,
                   r = 15 px (1.5 km), h = 0.6
  blind_emission   scale * clip((p_model - tau)/(1 - tau), 0, 1),
                   tau = 0.5, scale = 0.6,
                   p_model = gradient-boosted blind-fault detector
                   (scripts/train_model.py; NO distance-to-fault feature)

Guarantees enforced before writing:
  * values clipped to [0, 1], float32
  * NaN exactly outside the official template footprint
  * CRS/transform/shape copied verbatim from example_submission.tif
Then scripts/validate_submission.py re-reads the written file as an
independent gate. Artifact is copied to downloads/ with sha256 and a
machine-written meta file (suggested submission Note included).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from paths import (ARTIFACT_DIR, DOCS_DOWNLOADS, LABELS_TIF, TEMPLATE_TIF,
                   ensure_data)

POLICY = {
    "name": "halo15-0.6 + blind-gbt(tau=0.5,s=0.6) v1",
    "core_p": 0.95,
    "halo_radius_px": 15,
    "halo_height": 0.6,
    "model_tau": 0.5,
    "model_scale": 0.6,
}
SUGGESTED_NOTE = "halo r15/h0.6 + blind GBT v1 (7GEMSDOE)"


def load_truth_mask():
    with rasterio.open(LABELS_TIF) as src:
        lab = src.read(1)
        nod = src.nodata
    return np.where(lab == nod, 0, lab) > 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-publish", action="store_true", help="rebuild and validate only in external artifacts directory")
    args = parser.parse_args()
    ensure_data()
    t0 = time.time()
    p = POLICY

    with rasterio.open(TEMPLATE_TIF) as src:
        meta = src.meta.copy()
        tmpl = src.read(1)
        footprint = np.isfinite(tmpl)
    print("template:", meta["width"], "x", meta["height"], meta["crs"],
          meta["transform"])

    truth = load_truth_mask()
    assert truth.shape == (meta["height"], meta["width"])

    # --- halo field -------------------------------------------------------
    d = distance_transform_edt(~truth)
    r, h = p["halo_radius_px"], p["halo_height"]
    halo = np.maximum(1.0 - d / r, 0.0) * h
    halo[truth] = p["core_p"]
    print(f"halo: mass={halo[footprint].sum():.0f} "
          f"max={halo.max():.3f}", flush=True)

    # --- blind detector emission ------------------------------------------
    p_model = np.load(ARTIFACT_DIR / "p_model.npy")
    assert p_model.shape == truth.shape
    if not np.isfinite(p_model[footprint]).all() or np.any((p_model[footprint] < 0) | (p_model[footprint] > 1)):
        raise ValueError("model probabilities must be finite and in [0,1] inside footprint")
    emis = np.clip((np.nan_to_num(p_model, nan=0.0) - p["model_tau"])
                   / (1.0 - p["model_tau"]), 0.0, 1.0) * p["model_scale"]
    emis = emis.astype(np.float32)
    print(f"emission: mass={emis[footprint].sum():.0f}", flush=True)

    pred = np.maximum(halo, emis).astype(np.float32)
    pred = np.clip(pred, 0.0, 1.0)
    pred = pred.astype(np.float32)
    pred[~footprint] = np.nan

    # sanity before writing
    fin = pred[footprint]
    assert np.isfinite(fin).all() and fin.min() >= 0.0 and fin.max() <= 1.0
    print(f"final: footprint px={int(footprint.sum())} "
          f"min={fin.min():.4f} max={fin.max():.4f} mass={fin.sum():.0f} "
          f"px>0.5: {int((fin > 0.5).sum())}", flush=True)

    out_meta = meta.copy()
    out_meta.update(dtype="float32", count=1, nodata=float("nan"),
                    compress="deflate")
    out_path = ARTIFACT_DIR / "submission.tif"
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **out_meta) as dst:
        dst.write(pred, 1)
    print("wrote", out_path, out_path.stat().st_size, "bytes")

    # independent re-read gate
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from validate_submission import validate
    errors = validate(str(out_path), str(TEMPLATE_TIF))
    if errors:
        print("FORMAT GATE FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print("format gate: PASS")

    # local monitors (NOT leaderboard predictions - see the Metric page)
    from metric import dtvi
    catalog_dti = dtvi(np.nan_to_num(pred, nan=0.0), truth.astype(np.float64))
    blanket = np.where(footprint, 1.0, 0.0)
    blanket_dti = dtvi(blanket, truth.astype(np.float64))

    sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
    DOCS_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    if not args.no_publish:
        shutil.copy(out_path, DOCS_DOWNLOADS / "submission.tif")
    report = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "policy": p,
        "suggested_submission_note": SUGGESTED_NOTE,
        "grid": {"width": meta["width"], "height": meta["height"],
                 "crs": str(meta["crs"]), "transform": list(meta["transform"])[:6],
                 "dtype": "float32", "nodata": "nan"},
        "footprint_px": int(footprint.sum()),
        "stats": {
            "min": float(fin.min()), "max": float(fin.max()),
            "mass": float(fin.sum()),
            "px_gt_0p5": int((fin > 0.5).sum()),
            "halo_mass": float(halo[footprint].sum()),
            "emission_mass": float(emis[footprint].sum()),
        },
        "monitors_NOT_leaderboard_predictions": {
            "dti_vs_existing_catalogue": catalog_dti,
            "dti_blanket_vs_existing_catalogue": blanket_dti,
            "why": "both prize rounds score NEW faults absent from this "
                   "catalogue; these are plumbing monitors only",
        },
        "sha256": sha,
        "bytes": out_path.stat().st_size,
        "format_gate": "PASS",
        "proxy_evidence": "artifacts/component_policy_report.json (sweep)",
    }
    if not args.no_publish:
        (DOCS_DOWNLOADS / "submission_meta.json").write_text(
            json.dumps(report, indent=1))
    (ARTIFACT_DIR / "submission_meta.json").write_text(
        json.dumps(report, indent=1))
    print(f"catalogue monitor DTI: {catalog_dti:.4f} "
          f"(blanket {blanket_dti:.4f})")
    print("sha256:", sha)
    print(f"done in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
