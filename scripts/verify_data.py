"""Line-by-line verification of the official competition rasters.

Checks, for every raster in $GEMS_DATA_DIR:
  * sha256 matches the pin in knowledge/inherited_evidence/data_bridge_manifest.json
    (pins measured from the official downloads, 2026-09-17)
  * grid spec matches the competition format: EPSG:32611, 100 m, 3292x3730,
    transform (100, 0, 243350, 0, -100, 4508550)
  * band count / dtype as specified by the problem page
  * label census matches the verified summary (60,988 positive px,
    5,167,373 valid px)

Exit code 0 = every check PASS; anything else is flagged as an irregularity.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).parent))
from paths import FEATURES_TIF, LABELS_TIF, REPO_ROOT, TEMPLATE_TIF  # noqa: E402

MANIFEST = REPO_ROOT / "knowledge" / "inherited_evidence" / "data_bridge_manifest.json"

EXPECTED_GRID = {
    "width": 3292, "height": 3730, "crs": "EPSG:32611",
    "res": (100.0, 100.0),
    "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_grid(src, name, failures):
    if src.width != EXPECTED_GRID["width"] or src.height != EXPECTED_GRID["height"]:
        failures.append(f"{name}: shape {src.width}x{src.height}")
    if str(src.crs) != EXPECTED_GRID["crs"]:
        failures.append(f"{name}: crs {src.crs}")
    if tuple(src.res) != EXPECTED_GRID["res"]:
        failures.append(f"{name}: res {src.res}")
    t = tuple(src.transform)[:6]
    if t != EXPECTED_GRID["transform"]:
        failures.append(f"{name}: transform {t}")


def main() -> int:
    failures = []
    manifest = json.loads(MANIFEST.read_text())
    pins = {}
    for fe in manifest["files"]:
        pins[fe["canonical"]] = fe["sha256"]

    for path, canonical in [
        (TEMPLATE_TIF, "sample_submission.tif"),
        (LABELS_TIF, "labels.tif"),
        (FEATURES_TIF, "training_features.tif"),
    ]:
        if not path.exists():
            failures.append(f"missing {path}")
            continue
        got = sha256_of(path)
        want = pins[canonical]
        status = "PASS" if got == want else "FAIL"
        print(f"[{status}] sha256 {path.name}: {got}")
        if got != want:
            failures.append(f"{path.name}: sha256 {got} != {want}")

        with rasterio.open(path) as src:
            check_grid(src, path.name, failures)
            print(f"  grid {src.width}x{src.height} {src.crs} res={src.res} "
                  f"bands={src.count} dtype={src.dtypes[0]}")

    if failures:
        print("IRREGULARITIES:\n - " + "\n - ".join(failures))
        return 1

    with rasterio.open(FEATURES_TIF) as src:
        if src.count != 19:
            failures.append(f"features: expected 19 bands, got {src.count}")
        if any(d != "float32" for d in src.dtypes):
            failures.append("features: expected all float32")

    with rasterio.open(LABELS_TIF) as src:
        lab = src.read(1)
        nod = src.nodata
        valid = lab != nod
        pos = int((lab[valid] > 0).sum())
        n_valid = int(valid.sum())
        if pos != 60988:
            failures.append(f"labels: {pos} positive px, expected 60988")
        if n_valid != 5167373:
            failures.append(f"labels: {n_valid} valid px, expected 5167373")
        print(f"  labels census: valid={n_valid} positive={pos}")

    with rasterio.open(TEMPLATE_TIF) as src:
        t = src.read(1)
        if src.dtypes[0] != "float32":
            failures.append("template: expected float32")
        n_nan = int((~np.isfinite(t)).sum())
        if n_nan != 7111787:
            failures.append(f"template: {n_nan} NaN px, expected 7111787")
        pos = int((t[np.isfinite(t)] > 0).sum())
        if pos != 60988:
            failures.append(f"template: {pos} positive px, expected 60988 "
                            "(template is bit-identical to labels inside the "
                            "footprint - flagged irregularity from session 1)")
        print(f"  template census: nan={n_nan} positive={pos}")

    if failures:
        print("\nIRREGULARITIES:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
