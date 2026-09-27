"""Hermetic tests for the INGENIOUS fault-compilation product (no network)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ingenious_faults as IF  # noqa: E402


def test_link_discovery_prefers_v2_and_keeps_candidates():
    html = """
    <a href="/files/1391/paleo_geothermal_regional.zip">Paleo Geothermal Features.zip</a>
    <a href="/files/1391/faults_quaternary_INGENIOUS_regional_data.zip">Quaternary Faults v1.zip</a>
    <a href="/files/1391/qfaults_ingenious_nad83conus117_2023-06-27.zip">Quaternary Faults v2.zip</a>
    <a href="/files/1391/study_area_boundary_INGENIOUS_regional_data.zip">Study Area Boundary.zip</a>
    """
    got = IF.choose_fault_links(html)
    assert got["v1"].endswith("faults_quaternary_INGENIOUS_regional_data.zip")
    assert got["v2"].endswith("qfaults_ingenious_nad83conus117_2023-06-27.zip")
    assert len(got["candidates"]) == 4


def test_link_discovery_missing_page_is_not_fatal():
    got = IF.choose_fault_links("<html><body>no links here</body></html>")
    assert got["candidates"] == []
    assert "v1" not in got and "v2" not in got


def test_delta_bands_semantics():
    v1 = np.zeros((7, 7), bool)
    v2 = np.zeros((7, 7), bool)
    labels = np.zeros((7, 7), bool)
    v1[3, 0:3] = True           # v1 trace on row 3
    v2[3, 0:3] = True           # shared trace
    v2[3, 5] = True             # v2-only pixel, 2 px away from v1
    labels[5, 0:3] = True       # shipped labels, far from both
    bands = IF.delta_bands(v1, v2, labels)
    assert bands.shape == (5, 7, 7)
    assert bands[0].sum() == v2.sum() == 4
    assert bands[1].sum() == v1.sum() == 3
    assert bands[2].sum() == 1                      # v2_only
    assert bands[2][3, 5]
    assert bands[3].sum() == 4                      # all v2 pixels are >1 px from the labels
    assert bands[4].sum() == 3                      # labels not in v2


def test_delta_bands_handles_empty_inputs():
    z = np.zeros((4, 4), bool)
    bands = IF.delta_bands(z, z, z)
    assert bands.sum() == 0


def test_delta_radius_is_one_pixel_bridge():
    """A v2 pixel adjacent to a v1 pixel is NOT 'v2 only' at radius 1."""
    v1 = np.zeros((5, 5), bool)
    v2 = np.zeros((5, 5), bool)
    v1[2, 2] = True
    v2[2, 3] = True
    bands = IF.delta_bands(v1, v2, np.zeros((5, 5), bool))
    assert bands[2].sum() == 0
    bands2 = IF.delta_bands(v1, v2, np.zeros((5, 5), bool), radius=0)
    assert bands2[2].sum() == 1
