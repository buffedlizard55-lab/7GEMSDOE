import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import random_baseline as RB  # noqa: E402


def test_choose_density_prefers_skill_and_applies_discount():
    import lidar_candidates as LC
    exp = {"pooled_nms": {"lidar": {"0.005": {"multiple": 1.0}, "0.01": {"multiple": 1.0},
                                    "0.02": {"multiple": 1.0}, "0.03": {"multiple": 1.0}}}}
    rho = 0.00314
    best, rows = LC.choose_density(exp, rho)
    # zero skill -> expected DTI equals the random baseline at each density (kappa aside)
    for r in rows:
        assert r["assumed_multiple"] == pytest.approx(1.0)
        assert r["expected_dti"] == pytest.approx(RB.dti_random(r["f"], rho, kappa=0.0), abs=2e-4)
    exp["pooled_nms"]["lidar"]["0.005"]["multiple"] = 9.0  # strong low-density skill
    best2, rows2 = LC.choose_density(exp, rho)
    assert best2["f"] == 0.005 and best2["assumed_multiple"] == pytest.approx(1 + LC.TAU * 8.0)


def test_percentile_rank_is_monotone_and_masked():
    import lidar_candidates as LC
    x = np.array([[0.3, 0.1], [0.9, 0.5]], np.float32)
    m = np.array([[True, True], [False, True]])
    r = LC.percentile_rank(x, m)
    assert r[1, 0] == 0.0  # outside mask
    assert r[0, 1] < r[0, 0] < r[1, 1] and r[1, 1] == pytest.approx(1.0)


def test_scored_file_manifest_hashes_and_forensics():
    man = json.loads((ROOT / "external" / "scored" / "manifest.json").read_text())
    import hashlib
    for e in man["files"]:
        f = ROOT / "external" / "scored" / e["file"]
        assert hashlib.sha256(f.read_bytes()).hexdigest() == e["sha256"], e["file"]
    rep = json.loads((ROOT / "knowledge" / "session4" / "scored_files_analysis.json").read_text())
    assert all(r["nan_exactly_outside"] and r["values_in_01"] for r in rep["files"])
    ref = next(r for r in rep["files"] if r["file"] == rep["zero_skill_reference"])
    assert ref["skill_multiple"] == pytest.approx(1.0, abs=1e-3)
    assert 0.001 < rep["implied_truth_density"] < 0.01


def test_lidar_product_manifest_consistent():
    rep = json.loads((ROOT / "external" / "dem" / "lidar_scarp_features.json").read_text())
    import dem_merge as DM
    assert rep["bands"] == DM.BANDS
    assert rep["tile_status"].get("ok", 0) >= 700
    log = json.loads((ROOT / "external" / "dem" / "lidar_tile_log.json").read_text())
    assert len(log) == rep["tiles_total"]
    assert all(len(e["sha256"]) == 64 for e in log if e["status"] == "ok")
