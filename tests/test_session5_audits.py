"""Regression tests for session-5 audit outputs (run after the audits).

These guard the JSON contracts the site + next-session docs rely on.
They require GEMS_DATA_DIR rasters + the committed lidar product, so they
skip (rather than fail) when data placement has not been run -- CI stays
hermetic.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

GAPS = ROOT / "knowledge" / "session5" / "lidar_gaps.json"
FP = ROOT / "knowledge" / "session5" / "lidar_fp_audit.json"


def _load(path):
    if not path.exists():
        pytest.skip(f"{path.name} not generated (run scripts/lidar_gaps.py + lidar_fp_audit.py)")
    return json.loads(path.read_text())


def test_gaps_contract():
    g = _load(GAPS)
    assert g["footprint_px"] == 5167373
    assert g["covered_px"] + g["gap_px"] == g["footprint_px"]
    assert 0.20 < g["gap_fraction"] < 0.30
    assert g["candidate_emitted_in_gap_px"] == 0
    # catalogue census preserved across the split
    assert (g["catalogue_px_in_covered"] + g["catalogue_px_in_gap"]) == 60988
    assert set(g["quadrants"]) == {"NW", "NE", "SW", "SE"}
    assert sum(v["gap_px"] for v in g["quadrants"].values()) == g["gap_px"]
    # NE is the documented fill priority (largest gap fraction)
    fracs = {k: v["gap_fraction"] for k, v in g["quadrants"].items()}
    assert max(fracs, key=fracs.get) == "NE"


def test_fp_audit_contract():
    a = _load(FP)
    assert a["emitted_px"] == 76859
    assert 0 <= a["loop_hole_fraction_of_emitted"] < 0.05
    assert 0 <= a["emitted_cross_dominant_fraction"] <= 1
    v2 = a["v2_policy"]
    assert v2["would_keep_px"] + v2["would_drop_total_px"] == a["emitted_px"]
    assert "PRE-REGISTERED ONLY" in v2["status"]
    shares = a["relief_stratification"]
    assert abs(sum(c["emitted_share"] for c in shares.values()) - 1.0) < 0.01
