"""Hermetic tests for scripts/qfaults_prior.py (no network, no fiona)."""
import stat
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
from rasterio.transform import Affine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import qfaults_prior as QP


def test_parse_scale_denominator():
    assert QP.parse_scale_denominator("1:250,000") == 250000
    assert QP.parse_scale_denominator("1:24000") == 24000
    assert QP.parse_scale_denominator(100000) == 100000
    assert QP.parse_scale_denominator("250k") == 250000
    assert QP.parse_scale_denominator(None) is None
    assert QP.parse_scale_denominator("unknown") is None


def test_find_field_matches_observed_legacy_names_case_insensitively():
    assert QP.find_field(["scale", "certainty"], QP.SCALE_FIELDS) == "scale"
    assert QP.find_field(["scale", "certainty"], QP.CERTAINTY_FIELDS) == "certainty"
    assert QP.find_field(["Mapped_Scale"], QP.SCALE_FIELDS) == "Mapped_Scale"
    assert QP.find_field(["unrelated"], QP.CERTAINTY_FIELDS) is None


def test_classify_trace_coarse_and_inferred():
    c = QP.classify_trace({"MAPPEDSCALE": "1:500,000", "CERTAINTY": "inferred"},
                          "MAPPEDSCALE", "CERTAINTY")
    assert c["coarse"] and not c["fine"] and c["inferred"]
    assert c["scale_denom"] == 500000


def test_classify_trace_fine_well_constrained():
    c = QP.classify_trace({"MAPPEDSCALE": "1:24,000", "CERTAINTY": "well constrained"},
                          "MAPPEDSCALE", "CERTAINTY")
    assert c["fine"] and not c["coarse"] and not c["inferred"]


def test_classify_trace_unknown_scale_is_coarse():
    # Unknown scale must not silently join the "fine" arm of an H2 test.
    c = QP.classify_trace({}, "MAPPEDSCALE", "CERTAINTY")
    assert c["coarse"] and not c["fine"]


def test_classify_trace_missing_fields():
    c = QP.classify_trace({}, None, None)
    assert c["coarse"] and not c["inferred"]
    assert c["scale_denom"] is None


def test_rasterize_prior_band_assignment():
    tr = Affine(100, 0, 0, 0, -100, 1000)
    line = {"type": "LineString", "coordinates": [(50, 950), (50, 150)]}
    coarse = {"coarse": True, "fine": False, "inferred": True,
              "scale_denom": 500000, "certainty_raw": "inferred"}
    fine = {"coarse": False, "fine": True, "inferred": False,
              "scale_denom": 24000, "certainty_raw": "well constrained"}
    arr = QP.rasterize_prior([(line, coarse)], (10, 10), tr)
    assert arr.shape == (3, 10, 10) and arr.dtype == np.uint8
    assert arr[0].sum() > 0 and arr[1].sum() == 0 and arr[2].sum() > 0
    arr2 = QP.rasterize_prior([(line, fine)], (10, 10), tr)
    assert arr2[0].sum() == 0 and arr2[1].sum() > 0 and arr2[2].sum() == 0
    # empty input -> zeros, never a crash
    arr3 = QP.rasterize_prior([], (10, 10), tr)
    assert arr3.sum() == 0


def test_parse_layer_crs_accepts_mapping_and_rejects_missing():
    from rasterio.crs import CRS

    assert QP.parse_layer_crs({"init": "epsg:4326"}) == CRS.from_epsg(4326)
    with pytest.raises(ValueError, match="missing CRS"):
        QP.parse_layer_crs(None)


def test_safe_extract_rejects_traversal(tmp_path):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escaped.txt", "unsafe")
    destination = tmp_path / "extract"
    destination.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(ValueError, match="unsafe archive path"):
            QP.safe_extract_zip(archive, destination)
    assert not (tmp_path / "escaped.txt").exists()


def test_safe_extract_rejects_absolute_and_windows_paths(tmp_path):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("C:/escaped.txt", "unsafe")
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(ValueError, match="unsafe archive path"):
            QP.safe_extract_zip(archive, tmp_path / "extract")


def test_safe_extract_allows_nested_regular_files(tmp_path):
    archive_path = tmp_path / "safe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("Qfaults/trace.shp", "test")
    destination = tmp_path / "extract"
    destination.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        QP.safe_extract_zip(archive, destination)
    assert (destination / "Qfaults/trace.shp").read_text() == "test"


def test_safe_extract_rejects_duplicate_normalized_targets(tmp_path):
    archive_path = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("Qfaults/trace.shp", "first")
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("Qfaults/trace.shp", "second")
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(ValueError, match="duplicate archive path"):
            QP.safe_extract_zip(archive, tmp_path / "extract")


def test_safe_extract_rejects_symbolic_links(tmp_path):
    archive_path = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("Qfaults/link.shp")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(info, "../outside.shp")
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(ValueError, match="symbolic link"):
            QP.safe_extract_zip(archive, tmp_path / "extract")
