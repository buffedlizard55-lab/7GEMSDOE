"""The public site must be able to generate and check the submission raster itself.

``assets/geotiff_tools.js`` re-implements the parts of the GeoTIFF format the
competition needs: reading GDAL's floating-point predictor (the published artifact
is DEFLATE + predictor 3), validating a file against the template rules, and
writing a single-band float32 GeoTIFF from the compact site payload.

These tests drive that file through Node -- the same code path the browser runs --
and then re-check the produced file with rasterio/GDAL, which is what the
submission platform uses. No network access is required; the only data used are
committed artifacts under ``downloads/``.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = "gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif"
CANONICAL = ROOT / "downloads" / ARTIFACT
PAYLOAD_JS = ROOT / "assets" / "submission_payload.js"
MANIFEST = ROOT / "downloads" / "gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.payload.json"
HARNESS = ROOT / "tests/js/roundtrip.mjs"


def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def data_dir() -> Path | None:
    for candidate in (ROOT / "data", Path.home() / "gems_data"):
        if (candidate / "example_submission.tif").exists():
            return candidate
    configured = os.environ.get("GEMS_DATA_DIR")
    if configured and (Path(configured) / "example_submission.tif").exists():
        return Path(configured)
    return None


requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is required for the browser-code tests")


def _run_harness(tmp_path: Path):
    out_tif = tmp_path / "browser_built.tif"
    report = tmp_path / "report.json"
    proc = subprocess.run([shutil.which("node"), str(HARNESS), str(CANONICAL), str(PAYLOAD_JS),
                           str(out_tif), str(report)], cwd=ROOT, capture_output=True, text=True, timeout=900)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return out_tif, json.loads(report.read_text())


@pytest.fixture(scope="module")
def browser_built(tmp_path_factory):
    """Build the submission raster once through the browser code path."""
    if shutil.which("node") is None:
        pytest.skip("node is required for the browser-code tests")
    return _run_harness(tmp_path_factory.mktemp("browser"))


@requires_node
def test_browser_roundtrip_reproduces_the_published_raster(browser_built):
    out_tif, report = browser_built
    assert report["ok"] is True
    steps = {s["name"]: s for s in report["steps"]}

    # the published artifact really is GDAL's DEFLATE + floating-point predictor
    assert steps["read_template"]["compression"] == 8
    assert steps["read_template"]["predictor"] == 3
    assert (steps["read_template"]["width"], steps["read_template"]["height"]) == (3292, 3730)

    man = manifest()
    assert steps["template_class_counts"]["one"] == man["counts"]["one"]
    assert steps["template_class_counts"]["zero"] == man["counts"]["zero"]
    assert steps["template_class_counts"]["nan"] == man["counts"]["nan"]
    assert steps["validate_template"]["ok"] is True

    assert steps["rebuild_from_payload"]["pixel_sha256"] == man["pixel_payload_sha256"]
    assert steps["build_and_reread"]["ok"] is True
    assert steps["build_and_reread"]["crsEpsg"] == 32611
    assert steps["negative_controls"]["wrong_shape_rejected"] is True
    assert steps["negative_controls"]["nan_inside_rejected"] is True
    assert steps["negative_controls"]["above_one_rejected"] is True

    rasterio = pytest.importorskip("rasterio")
    with rasterio.open(CANONICAL) as ref, rasterio.open(out_tif) as gen:
        assert (gen.width, gen.height) == (ref.width, ref.height) == (3292, 3730)
        assert gen.crs == ref.crs
        assert tuple(gen.transform)[:6] == tuple(ref.transform)[:6]
        assert gen.dtypes == ("float32",)
        assert np.isnan(gen.nodata)
        a, b = ref.read(1), gen.read(1)
        assert np.array_equal(np.isnan(a), np.isnan(b))
        assert np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)])
        finite = b[np.isfinite(b)]
        assert finite.min() >= 0.0 and finite.max() <= 1.0
        assert int((b == 1).sum()) == manifest()["counts"]["one"]


def test_payload_manifest_matches_the_published_artifact():
    man = manifest()
    assert hashlib.sha256(CANONICAL.read_bytes()).hexdigest() == man["source_artifact_sha256"]
    assert man["counts"]["one"] == 76859
    assert man["counts"]["zero"] + man["counts"]["one"] + man["counts"]["nan"] == 3292 * 3730
    # the payload must stay far smaller than the raster it rebuilds
    assert man["pixel_payload_bytes"] / man["payload_base64_bytes"] > 50
    assert man["output_name"] == ARTIFACT
    assert man["format"].startswith("G7PL1")


@requires_node
def test_strict_gate_accepts_the_browser_built_file(browser_built):
    pytest.importorskip("rasterio")
    source = data_dir()
    if source is None:
        pytest.skip("competition template not placed (run scripts/download_competition_data.sh)")
    out_tif, _ = browser_built
    env = dict(os.environ, GEMS_DATA_DIR=str(source))
    gate = subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py"), str(out_tif)],
                          cwd=ROOT, capture_output=True, text=True, timeout=300, env=env)
    assert gate.returncode == 0, gate.stdout + gate.stderr
    assert "PASS" in gate.stdout
