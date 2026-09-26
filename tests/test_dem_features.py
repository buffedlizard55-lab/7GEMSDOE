"""Synthetic-scarp checks for the lidar feature extractor (no network, no data)."""
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.special import erf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import dem_features as DF  # noqa: E402
import dem_merge as DM  # noqa: E402


def synthetic_scarp(n=500, res=2.0, strike_deg=30.0, height=4.0, width=6.0, fan=0.03):
    """Planar fan (gradient ``fan``) cut by an erf scarp through the centre.

    strike_deg is an azimuth clockwise from north. Returns z, distance-to-trace (m).
    """
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    east = (xx - n / 2) * res
    north = -(yy - n / 2) * res
    th = np.radians(strike_deg)
    # unit normal to the trace (pointing to the right of strike)
    nx, ny = np.cos(th), -np.sin(th)
    d = east * nx + north * ny
    z = 1500 + fan * north + 0.5 * height * erf(d / width)
    return z.astype(np.float32), np.abs(d)


def test_scarp_features_peak_on_trace():
    z, dist = synthetic_scarp()
    ch = DF.scarp_channels(z, np.ones_like(z, bool))
    ex = ch["ex_max"]
    on = np.nanmean(ex[dist < 4])
    off = np.nanmean(ex[dist > 60])
    assert on > 10 * off, (on, off)
    step = ch["step_max"]
    assert np.nanmean(step[dist < 6]) > 5 * np.nanmean(step[dist > 80])


def test_strike_recovered_through_merge_derivation():
    for strike in (0.0, 30.0, 45.0, 90.0, 135.0):
        z, dist = synthetic_scarp(strike_deg=strike)
        ch = DF.scarp_channels(z, np.ones_like(z, bool))
        near = dist < 10
        raw = {k: np.array([np.nanmean(ch[k][near])]) for k in ("jxx_m_jyy", "j2xy", "jtrace")}
        raw.update({k: np.array([1.0]) for k in ("s1_max", "ex_max", "ex_mean", "step_max",
                                                 "lapneg_max", "lappos_max", "rough", "zmax", "zmin", "valid")})
        got = DM.derive(raw)["strike"][0]
        err = min(abs(got - strike), 180 - abs(got - strike))
        assert err < 3.0, (strike, got)
        assert DM.derive(raw)["coh100"][0] > 0.8


def test_nodata_edges_do_not_create_scarps():
    n = 400
    z = np.full((n, n), 1300.0, np.float32) + np.linspace(0, 10, n)[None, :].astype(np.float32)
    valid = np.ones_like(z, bool)
    valid[:, 250:] = False  # a flat plane with a nodata half: no real scarp anywhere
    z[~valid] = -9999.0
    ch = DF.scarp_channels(z, valid)
    assert np.all(np.isnan(ch["ex_max"][:, 240:]))
    assert np.nanmax(ch["ex_max"]) < 0.01


def test_aggregate_onto_official_grid_window():
    from rasterio.transform import from_origin
    z, dist = synthetic_scarp(n=300)
    ch = DF.scarp_channels(z, np.ones_like(z, bool))
    # a 600 m square placed inside the competition grid (NAD83 UTM 11N source)
    t = from_origin(400000.0, 4200000.0, 2.0, 2.0)
    (r0, c0, h, w), arrs = DF.aggregate(ch, t, "EPSG:26911")
    a, _, c, _, e, f = DF.GRID_TRANSFORM
    assert 0 <= r0 < DF.GRID_SHAPE[0] and 0 <= c0 < DF.GRID_SHAPE[1]
    # the window's upper-left cell must contain (or border) the source origin
    assert c + c0 * a <= 400000.0 + 200 and f + r0 * e >= 4200000.0 - 200
    v = arrs["valid"]
    assert np.nanmax(v) == pytest.approx(1.0, abs=1e-6)
    assert np.isfinite(arrs["ex_max"]).sum() >= 9  # >= 3x3 fully covered 100 m cells


def test_quantise_roundtrip_monotone():
    x = np.array([np.nan, 0.0, 0.01, 0.1, 0.5, 1.0, 5.0], np.float32)
    q = DM.quantise("s1_max", x)
    assert q[0] == 0 and q[1] == 1 and np.all(np.diff(q[1:].astype(int)) >= 0)
    back = DM.dequantise("s1_max", q)
    assert np.isnan(back[0]) and back[-1] == pytest.approx(2.0)
    assert abs(back[4] - 0.5) < 0.02


def test_grid_constants_match_template_when_available():
    import os
    tpl = Path(os.environ.get("GEMS_DATA_DIR", Path.home() / "gems_data")) / "example_submission.tif"
    if not tpl.exists():
        pytest.skip("competition template not present")
    import rasterio
    with rasterio.open(tpl) as s:
        assert tuple(s.transform)[:6] == DF.GRID_TRANSFORM
        assert s.shape == DF.GRID_SHAPE
        assert s.crs.to_epsg() == 32611


def test_tilted_plane_has_no_tile_seam_artifact():
    """Regression: even-reflection padding produced ex_max ~= regional slope at edges."""
    n = 300
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    z = 1400 + 0.15 * xx * 2.0 + 0.05 * yy * 2.0  # steep range-front-like plane
    ch = DF.scarp_channels(z.astype(np.float32), np.ones((n, n), bool))
    assert np.nanmax(ch["ex_max"]) < 1e-3
    assert np.nanmax(ch["step_max"]) < 1e-3
