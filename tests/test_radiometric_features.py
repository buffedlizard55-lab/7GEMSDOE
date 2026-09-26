import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import radiometric_features as RF


def test_normalized_gaussian_does_not_create_zero_boundary_edge():
    values = np.zeros((31, 31), np.float32)
    valid = np.zeros_like(values, bool)
    valid[5:26, 5:26] = True
    values[valid] = 0.7
    smoothed = RF.normalized_gaussian(values, valid, 3)
    assert np.all(smoothed[valid] == pytest.approx(0.7, abs=1e-5))
    assert np.all(smoothed[~valid] == 0)


def test_lineament_features_respond_to_internal_step_not_missing_edge():
    raw = np.zeros((4, 41, 41), np.uint8)
    valid = np.zeros((41, 41), bool)
    valid[4:37, 4:37] = True
    raw[:, valid] = 80
    raw[:, 4:37, 21:37] = 180
    features, names = RF.build_lineament_features(raw, valid)

    assert len(features) == 30
    assert len(names) == 30
    assert len(set(names)) == len(names)
    assert all(a.dtype == np.float16 and a.shape == valid.shape for a in features)
    assert all(np.isfinite(a).all() and np.all(a[~valid] == 0) for a in features)

    edge = features[names.index("edge_rss_s1")].astype(np.float32)
    # True interior transition is strong; the zero-coded survey boundary is not.
    internal = edge[8:33, 19:23].max()
    survey_edge = np.max(np.r_[edge[4, 8:33], edge[36, 8:33],
                               edge[8:33, 4], edge[8:33, 36]])
    assert internal > 0.05
    assert survey_edge < internal * 0.02


def test_uniform_field_has_zero_spatial_features():
    raw = np.full((4, 17, 19), 127, np.uint8)
    valid = np.ones((17, 19), bool)
    features, names = RF.build_lineament_features(raw, valid)
    non_orientation = [a for a, name in zip(features, names)
                       if not name.endswith(("cos2_s1", "sin2_s1",
                                             "cos2_s3", "sin2_s3"))]
    assert all(np.max(np.abs(a.astype(np.float32))) < 1e-5 for a in non_orientation)


def test_bad_inputs_fail_closed():
    with pytest.raises(ValueError, match="shape"):
        RF.build_lineament_features(np.zeros((4, 3, 3)), np.ones((2, 2), bool))
    with pytest.raises(ValueError, match="NaN"):
        bad = np.zeros((4, 3, 3), np.float32)
        bad[0, 0, 0] = np.nan
        RF.build_lineament_features(bad, np.ones((3, 3), bool))
    with pytest.raises(ValueError, match="scale"):
        RF.build_lineament_features(np.zeros((4, 3, 3)), np.ones((3, 3), bool),
                                    sigmas=(0,))
