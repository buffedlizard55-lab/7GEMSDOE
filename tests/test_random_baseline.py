"""The analytic random baseline must agree with the official metric by simulation."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import random_baseline as RB  # noqa: E402
from metric import dtvi_components, dtvi  # noqa: E402


def test_kernel_levels_match_metric_definition():
    lv = RB.kernel_levels()
    assert lv[0] == (1.0, 1)
    assert sum(n for _, n in lv) == 25  # offsets with d < 3 px (d = 3 has weight 0)
    assert lv[1][1] == 4 and lv[1][0] == pytest.approx(2 / 3)


@pytest.mark.parametrize("f", [0.01, 0.03, 0.1])
def test_coverage_matches_monte_carlo(f):
    rng = np.random.default_rng(1)
    h, w = 400, 400
    truth = np.zeros((h, w), np.int8)
    # line-like truth (independent of emission)
    for r in range(20, h - 20, 37):
        truth[r, 20:w - 20] = 1
    pred = (rng.random((h, w)) < f).astype(np.float64)
    c = dtvi_components(pred, truth)
    mc = c["TP_w"] / c["n_truth"]
    assert mc == pytest.approx(RB.coverage_random(f), rel=0.06)


def test_dti_random_matches_simulation():
    rng = np.random.default_rng(7)
    h, w = 600, 600
    truth = np.zeros((h, w), np.int8)
    for r in range(30, h - 30, 50):
        truth[r, 30:w - 30] = 1
    rho = truth.mean()
    f = 0.03
    sims = [dtvi((rng.random((h, w)) < f).astype(float), truth) for _ in range(3)]
    assert np.mean(sims) == pytest.approx(RB.dti_random(f, rho), rel=0.06)


def test_inversions_roundtrip():
    rho, f = 0.003, 0.03
    d = RB.dti_random(f, rho)
    assert RB.rho_from_random_score(d, f) == pytest.approx(rho, rel=1e-9)
    assert RB.coverage_from_score(d, f, rho) == pytest.approx(RB.coverage_random(f), rel=1e-9)
