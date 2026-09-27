"""The website must be able to generate the submission raster itself, offline.

`assets/geotiff_tools.js` re-implements the parts of the GeoTIFF format the
submission needs: reading GDAL's floating-point predictor, validating a file
against the competition template, and writing a single-band float32 GeoTIFF.
These tests drive that code in Node (the same file the browser loads) and then
check the result with rasterio/GDAL, which is what the submission platform uses.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "downloads/gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif"
PAYLOAD_JS = ROOT / "assets/submission_payload.js"
HARNESS = ROOT / "tests/js/geotiff_roundtrip.mjs"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required for the browser-code tests")


def _run_harness(tmp_path: Path):
    out_tif = tmp_path / "browser_built.tif"
    report = tmp_path / "report.json"
    proc = subprocess.run([shutil.which("node"), str(HARNESS), str(CANONICAL), str(PAYLOAD_JS),
                           str(out_tif), str(report)], cwd=ROOT, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return out_tif, json.loads(report.read_text())


def test_browser_roundtrip_produces_the_published_raster(tmp_path):
    out_tif, report = _run_harness(tmp_path)
    steps = {s["name"]: s for s in report["steps"]}
    assert steps["validate_canonical"]["ok"] is True
    assert steps["validate_uint8_like"]["ok"] is False, "the validator must reject out-of-[0,1] values"
    assert steps["payload_rebuild"]["pixel_sha256"] == steps["payload_rebuild"]["expected"]
    assert steps["pixels_identical_to_canonical"]["same"] is True
    assert steps["validate_built"]["ok"] is True

    rasterio = pytest.importorskip("rasterio")
    with rasterio.open(CANONICAL) as ref, rasterio.open(out_tif) as gen:
        assert (gen.width, gen.height) == (ref.width, ref.height) == (3292, 3730)
        assert gen.crs == ref.crs
        assert tuple(gen.transform)[:6] == tuple(ref.transform)[:6]
        assert gen.dtypes == ("float32",)
        a, b = ref.read(1), gen.read(1)
        assert np.array_equal(np.isnan(a), np.isnan(b))
        assert np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)])
        finite = b[np.isfinite(b)]
        assert finite.min() >= 0.0 and finite.max() <= 1.0


def test_payload_manifest_matches_the_published_artifact():
    man = json.loads((ROOT / "downloads/gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.payload.json").read_text())
    import hashlib

    assert hashlib.sha256(CANONICAL.read_bytes()).hexdigest() == man["source_artifact_sha256"]
    assert man["counts"]["one"] == 76859
    assert man["counts"]["zero"] + man["counts"]["one"] + man["counts"]["nan"] == 3292 * 3730
    # the payload must stay far smaller than the raster it rebuilds
    assert man["payload_bytes"] * 10 < man["pixel_payload_bytes"]


def test_strict_gate_accepts_the_browser_built_file(tmp_path):
    out_tif, _ = _run_harness(tmp_path)
    gate = subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py"), str(out_tif)],
                          cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert gate.returncode == 0, gate.stdout + gate.stderr
    assert "PASS" in gate.stdout
