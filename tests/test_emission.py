import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import emission as EM  # noqa: E402


def _blob_line(angle_deg, n=120, width=4.0):
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    th = np.radians(angle_deg)
    # distance to a line through the centre with direction (cos, sin) in array axes
    d = np.abs(-(xx - n / 2) * np.sin(th) + (yy - n / 2) * np.cos(th))
    return np.exp(-(d / width) ** 2), d


def test_ridge_nms_thins_wide_ridges_to_about_one_pixel():
    for ang in (0, 30, 45, 90, 120):
        s, d = _blob_line(ang)
        keep = EM.ridge_nms(s, np.ones_like(s, bool), sigma=1.0)
        inner = (np.abs(np.mgrid[0:120, 0:120][0] - 60) < 40) & (np.abs(np.mgrid[0:120, 0:120][1] - 60) < 40)
        kept = keep & inner & (s > 0.5)
        assert kept.sum() > 0
        assert np.all(d[kept] <= 1.5), ang  # every kept pixel lies on the ridge axis
        # roughly one pixel per unit length (diagonals up to sqrt(2))
        length = 80 / max(abs(np.cos(np.radians(ang))), abs(np.sin(np.radians(ang))))
        assert kept.sum() <= 2.2 * length, (ang, kept.sum(), length)


def test_top_k_and_dispersion():
    rng = np.random.default_rng(0)
    s = rng.random((50, 50))
    cand = np.ones_like(s, bool)
    m = EM.top_k_mask(s, cand, 10)
    assert m.sum() == 10 and s[m].min() >= np.sort(s.ravel())[-10]
    line = np.zeros((50, 50), bool); line[25, 5:45] = True
    blob = np.zeros((50, 50), bool); blob[20:27, 20:26] = True  # ~ same count
    v = np.ones_like(line)
    assert EM.dispersion_index(line, v) > 2 * EM.dispersion_index(blob, v)
