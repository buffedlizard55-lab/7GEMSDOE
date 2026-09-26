import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from structural_prior import structural_geometry, prior
from metric import dtvi_components


def test_straight_trace_extension_and_rotation():
    trace = np.zeros((51,51), dtype=bool)
    trace[25, 20:31] = True
    geom = structural_geometry(trace)
    p = prior(trace, geom)
    assert p[25, 36] > 0
    assert p[31, 25] == 0
    np.testing.assert_allclose(prior(trace.T, structural_geometry(trace.T)), p.T, atol=1e-6)
    assert np.isfinite(p).all() and p.min() >= 0 and p.max() <= 1


def test_no_trace():
    with pytest.raises(ValueError):
        structural_geometry(np.zeros((4,4)))


def test_custom_metric_radius():
    p = np.zeros((7,7)); g = p.copy()
    p[3, 4] = 1; g[3,3] = 1
    assert dtvi_components(p, g, r_pixels=2)['TP_w'] == .5
    assert dtvi_components(p, g, r_pixels=1)['TP_w'] == 0
