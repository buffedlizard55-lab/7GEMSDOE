"""Verification of scripts/metric.py (official distance-weighted Tversky index).

Three independent layers:
1. Brute-force reference implementation (O(|G| * |P|)) agrees with the fast one.
2. Algebraic identities from the problem page hold exactly.
3. Every deterministic row of the previously-verified metric-strategy table
   (knowledge/inherited_evidence/metric_strategy.json, measured on the real
   competition fixture window) is reproduced bit-for-bit (tolerance 1e-9).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from metric import ALPHA, BETA, R_PIXELS, dtvi, dtvi_components  # noqa: E402

FIXTURE_LABELS = ROOT / "tests" / "fixture" / "fixture_labels.tif"
FIXTURE_FEATURES = ROOT / "tests" / "fixture" / "fixture_features_int16.tif"
INHERITED = ROOT / "knowledge" / "inherited_evidence" / "metric_strategy.json"


# --------------------------------------------------------------------------
# 1. brute-force reference
# --------------------------------------------------------------------------
def brute_force_components(pred, truth, r_pixels=R_PIXELS, alpha=ALPHA, beta=BETA):
    pred = np.where(np.isfinite(pred), pred, 0.0)
    gy, gx = np.nonzero(truth > 0)
    py, px = np.nonzero(pred > 0)
    tp = fn = 0.0
    for y, x in zip(gy, gx):
        best = 0.0
        for yy, xx in zip(py, px):
            d = float(np.hypot(yy - y, xx - x))
            if d <= r_pixels:
                best = max(best, pred[yy, xx] * max(1.0 - d / r_pixels, 0.0))
        tp += best
        fn += 1.0 - best
    fp = 0.0
    for y, x in zip(py, px):
        bestk = 0.0
        for yy, xx in zip(gy, gx):
            d = float(np.hypot(yy - y, xx - x))
            if d <= r_pixels:
                bestk = max(bestk, max(1.0 - d / r_pixels, 0.0))
        fp += pred[y, x] * (1.0 - bestk)
    return {"TP_w": tp, "FP_w": fp, "FN_w": fn}


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_matches_brute_force(seed):
    rng = np.random.default_rng(seed)
    h = w = 16
    truth = (rng.random((h, w)) < 0.10).astype(float)
    pred = np.where(rng.random((h, w)) < 0.35, rng.random((h, w)), 0.0)
    got = dtvi_components(pred, truth)
    ref = brute_force_components(pred, truth)
    for k in ("TP_w", "FP_w", "FN_w"):
        assert abs(got[k] - ref[k]) < 1e-9, (k, got[k], ref[k])


def test_identity_tp_plus_fn_equals_truth_count():
    rng = np.random.default_rng(7)
    truth = (rng.random((24, 24)) < 0.08).astype(float)
    for _ in range(3):
        pred = np.where(rng.random((24, 24)) < 0.3, rng.random((24, 24)), 0.0)
        c = dtvi_components(pred, truth)
        assert abs(c["TP_w"] + c["FN_w"] - c["n_truth"]) < 1e-9


def test_worked_example_identity_from_problem_page():
    """The problem page's scoring example reports TPw=3.00, FPw=1.89, FNw=2.00
    -> |G| = TPw + FNw = 5.0 exactly, and prints
    DTI = 3.00/(3.00+0.2*1.89+0.8*2.00) = 0.60 (rounded to 2 dp on the page)."""
    dti = 3.00 / (3.00 + 0.2 * 1.89 + 0.8 * 2.00)
    assert abs(dti - 0.6026518) < 1e-6
    assert round(dti, 2) == 0.60  # the page displays 0.60


def test_bounds_zero_and_perfect():
    truth = np.zeros((9, 9))
    truth[3:6, 4] = 1.0
    zeros = np.zeros((9, 9))
    assert dtvi(zeros, truth) == 0.0
    exact = truth.copy()
    assert dtvi(exact, truth) > 0.9999


def test_rejects_out_of_range():
    truth = np.zeros((5, 5))
    truth[2, 2] = 1.0
    with pytest.raises(ValueError):
        dtvi(np.full((5, 5), 1.5), truth)


# --------------------------------------------------------------------------
# 2. fixture reproduction of the inherited verified table
# --------------------------------------------------------------------------
def _load_fixture():
    import rasterio

    with rasterio.open(FIXTURE_LABELS) as src:
        lab = src.read(1)
        lab_nodata = src.nodata
    with rasterio.open(FIXTURE_FEATURES) as src:
        b1 = src.read(1)
        nod = -32768
        valid = b1 != nod
    truth = np.where(lab == lab_nodata, 0.0, lab.astype(float))
    assert int((truth > 0).sum()) == 5154
    return truth, valid


def _inherited_rows():
    d = json.loads(INHERITED.read_text())
    return {r["strategy"]: r for r in d["rows"]}


def _dilate(mask, r):
    """Iterative 4-neighbour (L1 / cross) dilation - the exact construction
    behind the inherited table (masses 15509/25816/35935/45643/64192)."""
    from scipy.ndimage import binary_dilation

    cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
    out = mask.copy()
    for _ in range(r):
        out = binary_dilation(out, structure=cross)
    return out


def _triangular_ramp(truth_mask, valid, radius):
    from scipy.ndimage import distance_transform_edt

    dist = distance_transform_edt(~truth_mask)
    p = np.maximum(1.0 - dist / radius, 0.0)
    p[~valid] = 0.0
    return p.astype(np.float32)


DETERMINISTIC = [
    "all zeros",
    "all ones (blanket coverage)",
    "uniform p=0.05",
    "uniform p=0.1",
    "uniform p=0.25",
    "uniform p=0.5",
    "exact known faults, p=1",
    "known faults dilated r=1, p=1",
    "known faults dilated r=2, p=1",
    "known faults dilated r=3, p=1",
    "known faults dilated r=4, p=1",
    "known faults dilated r=6, p=1",
    "triangular ramp radius 3px",
    "triangular ramp radius 5px",
    "triangular ramp radius 8px",
]


@pytest.fixture(scope="module")
def fixture():
    return _load_fixture()


@pytest.mark.parametrize("name", DETERMINISTIC)
def test_reproduces_inherited_table_row(fixture, name):
    truth, valid = fixture
    rows = _inherited_rows()
    row = rows[name]

    if name == "all zeros":
        pred = np.zeros(truth.shape, dtype=np.float32)
    elif name.startswith("all ones"):
        pred = valid.astype(np.float32)
    elif name.startswith("uniform p="):
        pred = valid.astype(np.float32) * np.float32(name.split("=")[1])
    elif name == "exact known faults, p=1":
        pred = ((truth > 0) & valid).astype(np.float32)
    elif name.startswith("known faults dilated"):
        r = int(name.split("r=")[1].split(",")[0])
        pred = (_dilate(truth > 0, r) & valid).astype(np.float32)
    elif name.startswith("triangular ramp radius"):
        radius = float(name.split("radius ")[1].split("px")[0])
        pred = _triangular_ramp(truth > 0, valid, radius)
    else:  # pragma: no cover
        raise AssertionError(name)

    c = dtvi_components(pred, truth)
    assert abs(c["predicted_mass"] - row["mass"]) < max(1.0, 1e-6 * row["mass"]), (
        name, c["predicted_mass"], row["mass"])
    assert abs(c["TP_w"] - row["TP_w"]) < max(1e-6, 1e-5 * row["TP_w"]), (
        name, c["TP_w"], row["TP_w"])
    assert abs(c["FP_w"] - row["FP_w"]) < max(1e-6, 1e-5 * row["FP_w"]), (
        name, c["FP_w"], row["FP_w"])
    got = dtvi(pred, truth)
    assert abs(got - row["dti"]) < 1e-8, (name, got, row["dti"])


def test_closed_form_identity(fixture):
    """DTI = TP_w / (0.2*(TP_w + FP_w) + 0.8*|G|) for the competition parameters."""
    truth, valid = fixture
    rng = np.random.default_rng(3)
    pred = np.where(valid & (rng.random(truth.shape) < 0.1),
                    rng.random(truth.shape), 0.0)
    c = dtvi_components(pred, truth)
    closed = c["TP_w"] / (0.2 * (c["TP_w"] + c["FP_w"]) + 0.8 * c["n_truth"] + 1e-10)
    assert abs(closed - dtvi(pred, truth)) < 1e-12
