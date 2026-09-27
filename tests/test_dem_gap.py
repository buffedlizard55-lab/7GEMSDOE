"""Hermetic tests for the lidar gap-enumeration and gap-only merge tools.

No network and no real rasters: the S3 listing helpers are exercised through
their pure parts (tile-id parsing, tile -> grid window mapping) and the merge is
checked on a synthetic base product plus synthetic shard archives in the exact
format ``scripts/dem_features.py`` writes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dem_enumerate as DE  # noqa: E402
import dem_features as DF  # noqa: E402
import dem_merge as DM  # noqa: E402
import dem_merge_gap as DG  # noqa: E402


def test_parse_tile_ids():
    got = DE.parse_tile("USGS_1M_11_x45y443_NV_EastCentral_2021_D21")
    assert got == (11, 45, 443, "NV_EastCentral_2021_D21")
    assert DE.parse_tile("not-a-tile") is None
    assert DE.parse_tile("USGS_1M_99_x1y2_weird") is None
    crs, left, bottom, right, top = DE.tile_bounds_utm("USGS_1M_11_x45y443_NV_EastCentral_2021_D21")
    assert (crs, left, bottom, right, top) == ("EPSG:26911", 450000.0, 4420000.0, 460000.0, 4430000.0)


def test_tile_window_matches_every_recorded_window():
    """The tile -> official-grid mapping is pinned against all 706 runner-measured windows.

    This is the regression that caught a full-10-km mis-indexing of the tile id.
    """
    log = json.loads((Path(__file__).resolve().parents[1] / "external/dem/lidar_tile_log.json").read_text())
    checked = 0
    for entry in log:
        if entry.get("status") != "ok" or not entry.get("window"):
            continue
        # one cell of slack: the rasterised bounds round by at most a cell
        win = DE.tile_window(entry["tile"], margin_cells=1)
        if win is None:
            continue
        r0, c0, h, w = win
        wr, wc, wh, ww = entry["window"]
        # dem_features pads its destination window by one cell on each side.
        assert r0 <= wr and c0 <= wc, entry["tile"]
        assert r0 + h >= wr + wh and c0 + w >= wc + ww, entry["tile"]
        checked += 1
    assert checked >= 600, f"expected to check every recorded tile, checked {checked}"


def _write_base(path: Path, gap_value=0):
    import rasterio
    from rasterio.transform import Affine

    H, W = DE.DF.GRID_SHAPE
    n = len(DM.BANDS)
    arr = np.zeros((n, 64, 64), dtype=np.uint8)  # small synthetic tile, not the real grid
    arr[DM.BANDS.index("valid")][:16, :16] = gap_value
    arr[DM.BANDS.index("ex_max")][:16, :16] = 40
    arr[DM.BANDS.index("valid")][16:, :] = 200
    arr[DM.BANDS.index("ex_max")][16:, :] = 60
    prof = dict(driver="GTiff", height=64, width=64, count=n, dtype="uint8",
                crs="EPSG:32611", transform=Affine(100.0, 0, 243350.0, 0, -100.0, 4508550.0),
                compress="deflate")
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(arr)
        for i, name in enumerate(DM.BANDS):
            dst.set_band_description(i + 1, name)
    return prof


def _fake_mosaic(value=0.4, shape=(64, 64)):
    """Stand-in for dem_merge.mosaic (its own behaviour is covered by test_dem_features)."""
    raw = {n: np.full(shape, np.nan, np.float32) for n, _, _ in DF.CHANNELS}
    for n in ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
              "upface_max", "cross_max", "jtrace"):
        raw[n] = np.full(shape, value, np.float32)
    raw["jxx_m_jyy"] = np.zeros(shape, np.float32)
    raw["j2xy"] = np.zeros(shape, np.float32)
    raw["zmax"] = np.full(shape, 1500.0, np.float32)
    raw["zmin"] = np.full(shape, 1400.0, np.float32)
    raw["valid"] = np.ones(shape, np.float32)
    return raw


def test_merge_gap_only_touches_empty_cells(tmp_path, monkeypatch):
    base = tmp_path / "base.tif"
    _write_base(base)
    import rasterio

    with rasterio.open(base) as s:
        before = s.read()
    monkeypatch.setattr(DG.DM, "mosaic", lambda files: _fake_mosaic(0.4))
    shard = tmp_path / "shard.npz"
    np.savez_compressed(shard, window=np.array([0, 0, 64, 64]), **{n: np.ones((64, 64), np.float32)
                                                                  for n, _, _ in DF.CHANNELS})

    man = DG.merge_gap(str(base), str(tmp_path / "*.npz"), str(base), str(tmp_path / "man.json"))
    assert man["cells_changed_outside_previous_gap"] == 0
    assert man["cells_with_lidar_after"] > man["cells_with_lidar_before"]
    with rasterio.open(base) as s:
        after = s.read()
    vi = DM.BANDS.index("valid")
    assert np.array_equal(after[:, 16:, :], before[:, 16:, :]), "cells with data must not move"
    assert np.all(after[vi][:16, :16] > 0), "empty cells should now have lidar"
    # A cell that starts as 0 lidar cannot be a partially covered cell, so the
    # old ex_max quantisation there must have been overwritten by the new value.
    ei = DM.BANDS.index("ex_max")
    assert after[ei][0, 0] != before[ei][0, 0]


def test_merge_gap_refuses_shape_mismatch(tmp_path, monkeypatch):
    """A mosaic on a different grid must fail closed, never be written."""
    base = tmp_path / "base.tif"
    _write_base(base)
    np.savez_compressed(tmp_path / "s.npz", window=np.array([0, 0, 8, 8]),
                        **{n: np.ones((8, 8), np.float32) for n, _, _ in DF.CHANNELS})
    monkeypatch.setattr(DG.DM, "mosaic", lambda files: _fake_mosaic(0.4, shape=(8, 8)))
    with pytest.raises(SystemExit):
        DG.merge_gap(str(base), str(tmp_path / "*.npz"), str(base), str(tmp_path / "man.json"))
    assert not (tmp_path / "man.json").exists()
    with pytest.raises(SystemExit):
        DG.merge_gap(str(base), str(tmp_path / "no-such-*.npz"), str(base), None)


def test_gap_mask_is_footprint_minus_valid(tmp_path):
    import rasterio
    from rasterio.transform import Affine

    fp = tmp_path / "fp.tif"
    base = tmp_path / "base.tif"
    with rasterio.open(fp, "w", driver="GTiff", height=8, width=8, count=1, dtype="int8",
                       crs="EPSG:32611", transform=Affine(100.0, 0, 0, 0, -100.0, 800)) as dst:
        a = np.full((8, 8), 0, np.int8)
        a[:, :2] = -1
        dst.write(a, 1)
    with rasterio.open(base, "w", driver="GTiff", height=8, width=8, count=len(DM.BANDS),
                       dtype="uint8", crs="EPSG:32611", transform=Affine(100.0, 0, 0, 0, -100.0, 800)) as dst:
        b = np.zeros((len(DM.BANDS), 8, 8), np.uint8)
        b[DM.BANDS.index("valid")][:, 4:] = 200
        dst.write(b)
        for i, n in enumerate(DM.BANDS):
            dst.set_band_description(i + 1, n)
    gap = DE.gap_mask(str(base), str(fp))
    assert gap.shape == (8, 8)
    assert gap.sum() == 2 * 8  # columns 2-3 are inside the footprint and have no lidar
    assert not gap[:, 6:].any()  # outside the footprint


def test_merge_gap_hashes_prove_the_gap_only_fold(tmp_path, monkeypatch):
    """Regression for run 36282096826: sha256_before was hashed after the in-place
    write, so the manifest claimed identical before/after bytes for a fold that
    changed 1.29 M cells. The hash must now be taken from the pre-write file."""
    import hashlib

    base = tmp_path / "base.tif"
    _write_base(base)
    pre = hashlib.sha256(base.read_bytes()).hexdigest()
    monkeypatch.setattr(DG.DM, "mosaic", lambda files: _fake_mosaic(0.4))
    np.savez_compressed(tmp_path / "shard.npz", window=np.array([0, 0, 64, 64]),
                        **{n: np.ones((64, 64), np.float32) for n, _, _ in DF.CHANNELS})
    man = DG.merge_gap(str(base), str(tmp_path / "*.npz"), str(base), str(tmp_path / "man.json"))
    assert man["sha256_before"] == pre
    assert man["sha256_after"] != man["sha256_before"]
    assert man["sha256_after"] == hashlib.sha256(base.read_bytes()).hexdigest()
    assert man["cells_changed_outside_previous_gap"] == 0
    assert not list(tmp_path.glob("*.tmp*")), "temporary product must not be left behind"


def test_merge_gap_leaves_base_untouched_when_readback_fails(tmp_path):
    """The base product must survive a write that cannot be read back."""
    base = tmp_path / "base.tif"
    _write_base(base)
    good = base.read_bytes()
    tmp_product = tmp_path / "base.tif.tmp999"
    tmp_product.write_bytes(b"partial bytes that failed the read-back check")
    with pytest.raises(SystemExit):
        DG.publish_or_raise(reread=np.ones((2, 2)), out=np.zeros((2, 2)),
                            tmp_path=str(tmp_product), out_path=str(base))
    assert base.read_bytes() == good, "failed fold must not corrupt the published product"
    assert not tmp_product.exists(), "temporary product must be removed"
    tmp_product.write_bytes(b"partial bytes that failed the read-back check")
    DG.publish_or_raise(reread=np.ones((2, 2)), out=np.ones((2, 2)),
                        tmp_path=str(tmp_product), out_path=str(base))
    assert base.read_bytes().startswith(b"partial"), "a verified product is published"
