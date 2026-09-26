"""Hermetic format tests for the committed submission artifact.

These tests use only pinned constants measured from the official template
(example_submission.tif) so they run without the external data directory.
The full template comparison (exact footprint mask) happens at build time in
scripts/validate_submission.py.
"""

import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs" / "downloads" / "submission.tif"
META = ROOT / "docs" / "downloads" / "submission_meta.json"

# pinned constants from the official template (knowledge/02_data_sources.md)
EXPECTED = {
    "width": 3292,
    "height": 3730,
    "crs": "EPSG:32611",
    "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
    "footprint_px": 5167373,   # valid px of the official template
    "outside_nan_px": 7111787,
}


@pytest.fixture(scope="module")
def rasterio():
    return pytest.importorskip("rasterio")


def test_artifact_exists():
    assert ARTIFACT.exists(), "docs/downloads/submission.tif missing - run build_submission.py"
    assert META.exists()


def test_format_constants(rasterio):
    with rasterio.open(ARTIFACT) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert src.width == EXPECTED["width"]
        assert src.height == EXPECTED["height"]
        assert str(src.crs) == EXPECTED["crs"]
        assert tuple(src.transform)[:6] == EXPECTED["transform"]
        arr = src.read(1)

    finite = np.isfinite(arr)
    n_fin = int(finite.sum())
    assert n_fin == EXPECTED["footprint_px"], (
        f"{n_fin} finite px, official template has {EXPECTED['footprint_px']}")
    assert int((~finite).sum()) == EXPECTED["outside_nan_px"]

    vals = arr[finite]
    assert vals.min() >= 0.0, f"min {vals.min()} < 0 -> platform rejects"
    assert vals.max() <= 1.0, f"max {vals.max()} > 1 -> platform rejects"
    # the artifact must actually predict something
    assert float(vals.sum()) > 100_000
    assert float((vals > 0.5).sum()) > 10_000


def test_meta_consistent_with_artifact(rasterio):
    meta = json.loads(META.read_text())
    assert meta["format_gate"] == "PASS"
    assert meta["grid"]["width"] == EXPECTED["width"]
    assert meta["grid"]["height"] == EXPECTED["height"]
    assert meta["grid"]["crs"] == EXPECTED["crs"]
    assert meta["footprint_px"] == EXPECTED["footprint_px"]
    assert 0.0 <= meta["stats"]["min"] and meta["stats"]["max"] <= 1.0
    assert len(meta["sha256"]) == 64
    assert meta["suggested_submission_note"]


def test_sha256_matches_meta():
    import hashlib

    meta = json.loads(META.read_text())
    h = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    assert h == meta["sha256"], "artifact bytes changed without rebuild"
