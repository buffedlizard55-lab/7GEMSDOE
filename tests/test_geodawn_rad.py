"""Hermetic tests for scripts/geodawn_rad.py (no network)."""
import stat
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

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


def test_select_rad_files_matches_area_archive_member_names():
    files = listing("Area2/22103_Area2_K.tif", "Area2/22103_Area2_Th.tif",
                    "Area2/22103_Area2_U.tif", "Area2/22103_Area2_TC.tif")
    assert set(GR.select_rad_files(files)) == {"K", "Th", "U", "TC"}


def test_select_rad_files_fails_closed_with_observed_list():
    files = listing("readme.txt", "mag_TMI.grd")
    with pytest.raises(ValueError, match="observed"):
        GR.select_rad_files(files)


def test_select_rad_files_rejects_ambiguous_preferred_channel():
    files = listing("GeoDAWN_K_pct_100m.tif", "GeoDAWN_K_pct_400m.tif",
                    "GeoDAWN_eTh.tif", "GeoDAWN_eU.tif",
                    "GeoDAWN_total_count.tif")
    with pytest.raises(ValueError, match="ambiguous K candidates"):
        GR.select_rad_files(files)


def test_select_tiff_archives_requires_one_exact_area_package():
    files = listing("22103_area1_tiffs.zip", "22103_area2_tiffs.zip", "readme.pdf")
    assert set(GR.select_tiff_archives(files)) == {1, 2}
    with pytest.raises(ValueError, match="expected one 22103_area2_tiffs.zip"):
        GR.select_tiff_archives(listing("22103_area1_tiffs.zip",
                                       "22103_area1_tiffs-copy.zip"))


def test_inspect_tiff_zip_lists_only_safe_rasters(tmp_path):
    path = tmp_path / "safe.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Area1/K.tif", b"tif")
        archive.writestr("readme.txt", b"metadata")
    with zipfile.ZipFile(path) as archive:
        files = GR.inspect_tiff_zip(archive)
    assert [(f["name"], f["size"]) for f in files] == [("Area1/K.tif", 3)]


def test_inspect_tiff_zip_rejects_unsafe_duplicate_and_symlink_members(tmp_path):
    path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../escape.tif", b"unsafe")
    with zipfile.ZipFile(path) as archive:
        with pytest.raises(ValueError, match="unsafe GeoDAWN archive path"):
            GR.inspect_tiff_zip(archive)

    path = tmp_path / "symlink.zip"
    link = zipfile.ZipInfo("link.tif")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(link, "../escape.tif")
    with zipfile.ZipFile(path) as archive:
        with pytest.raises(ValueError, match="symbolic link"):
            GR.inspect_tiff_zip(archive)


def test_safe_basename_strips_windows_and_posix_paths():
    assert GR._safe_basename(r"..\\nested/path.tif") == "path.tif"


def test_warp_to_grid_preserves_source_grid_metadata(tmp_path):
    source = tmp_path / "source.tif"
    transform = Affine(100, 0, 0, 0, -100, 200)
    with rasterio.open(source, "w", driver="GTiff", width=2, height=2,
                       count=1, dtype="float32", crs="EPSG:32611",
                       transform=transform, nodata=-9999) as dst:
        dst.write(np.array([[1, 2], [3, 4]], dtype=np.float32), 1)
    values, mask, metadata = GR.warp_to_grid(
        source, (2, 2), transform, "EPSG:32611")
    assert mask.all()
    assert np.array_equal(values, [[1, 2], [3, 4]])
    assert metadata["width"] == metadata["height"] == 2
    assert metadata["crs"] == "EPSG:32611"
    assert metadata["resolution"] == [100.0, 100.0]
    assert metadata["nodata"] == -9999.0


def test_quantise_robust_and_nodata_zero():
    x = np.arange(100, dtype=np.float32).reshape(10, 10)
    mask = np.ones((10, 10), bool)
    mask[0, 0] = False
    q = GR.quantise(x, mask)
    assert q.dtype == np.uint8
    assert q[0, 0] == 0
    assert q[mask].min() >= 1 and q[mask].max() <= 255
    # Constant input -> all zeros (no fake contrast).
    assert GR.quantise(np.full((4, 4), 7.0, np.float32),
                       np.ones((4, 4), bool)).sum() == 0
    # Masked NaN/Inf cells are never encoded as data or allowed to contaminate
    # percentile bounds.
    special = np.arange(100, dtype=np.float32).reshape(10, 10)
    special[0, 0] = np.nan
    special[0, 1] = np.inf
    qs = GR.quantise(special, np.ones((10, 10), bool))
    assert qs[0, 0] == 0 and qs[0, 1] == 0
    assert qs[np.isfinite(special)].min() >= 1
    # empty mask -> all zeros
    assert GR.quantise(x, np.zeros((10, 10), bool)).sum() == 0
