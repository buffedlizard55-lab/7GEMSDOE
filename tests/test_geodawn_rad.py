"""Hermetic tests for scripts/geodawn_rad.py (no network)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import geodawn_rad as GR


def listing(*names):
    return [{"name": n, "size": 10, "url": "https://example.invalid/" + n}
            for n in names]


def test_select_rad_files_happy_path():
    files = listing("GeoDAWN_K_pct.tif", "GeoDAWN_eTh.tif", "GeoDAWN_eU.tif",
                    "GeoDAWN_total_count.tif", "contractor_report.pdf",
                    "mag_TMI.grd")
    chosen = GR.select_rad_files(files)
    assert set(chosen) == {"K", "Th", "U", "TC"}
    assert chosen["K"]["name"] == "GeoDAWN_K_pct.tif"
    # non-grid extensions never match even with tempting names
    assert all(f["name"].lower().endswith((".tif", ".tiff", ".grd", ".gxf"))
               for f in chosen.values())


def test_select_rad_files_fails_closed_with_observed_list():
    files = listing("readme.txt", "mag_TMI.grd")
    with pytest.raises(ValueError, match="observed"):
        GR.select_rad_files(files)


def test_quantise_robust_and_nodata_zero():
    x = np.arange(100, dtype=np.float32).reshape(10, 10)
    mask = np.ones((10, 10), bool)
    mask[0, 0] = False
    q = GR.quantise(x, mask)
    assert q.dtype == np.uint8
    assert q[0, 0] == 0
    assert q[mask].min() >= 1 and q[mask].max() <= 255
    # constant input -> all zeros (no fake contrast)
    assert GR.quantise(np.full((4, 4), 7.0, np.float32),
                       np.ones((4, 4), bool)).sum() == 0
    # empty mask -> all zeros
    assert GR.quantise(x, np.zeros((10, 10), bool)).sum() == 0
