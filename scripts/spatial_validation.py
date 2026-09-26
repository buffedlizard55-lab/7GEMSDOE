"""Fixed geographic stress test, not a reproduction of private competition masks.

Four raster quadrants; 1 km label exclusion; remove whole 8-connected traces
intersecting the exclusion zone. Connected traces are NOT geological fault IDs.
Score only a 300 m interior of the valid footprint, retaining context for kernels.
Policies frozen before execution. No parameters selected on these diagnostic folds.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import rasterio
from scipy.ndimage import label, distance_transform_edt
from metric import _kernel_offsets, _shift, dtvi_closed_form
from paths import LABELS_TIF, TEMPLATE_TIF, REPO_ROOT
from structural_prior import structural_geometry, prior


def assert_same_grid(source, reference):
    if (source.shape != reference.shape or source.crs != reference.crs
            or source.transform != reference.transform):
        raise ValueError('raster grid mismatch: shape, CRS and transform must agree')


def fold_windows(shape):
    h, w = shape
    return [(0, h//2, 0, w//2), (0, h//2, w//2, w),
            (h//2, h, 0, w//2), (h//2, h, w//2, w)]


def split_fold(truth, valid, window, buffer=10, context=45):
    if truth.shape != valid.shape or truth.ndim != 2:
        raise ValueError('aligned 2D truth and valid required')
    if buffer < 3 or context <= buffer + 30:
        raise ValueError('buffer >=3 and context > buffer+30 required')
    y0, y1, x0, x1 = window
    h, w = truth.shape
    if not (0 <= y0 < y1 <= h and 0 <= x0 < x1 <= w):
        raise ValueError('invalid window')
    exclusion = np.zeros(truth.shape, bool)
    exclusion[max(0,y0-buffer):min(h,y1+buffer), max(0,x0-buffer):min(w,x1+buffer)] = True
    comps, _ = label(truth & valid, structure=np.ones((3,3)))
    banned = np.unique(comps[exclusion & truth & valid])
    visible = truth & valid & ~exclusion & ~np.isin(comps, banned)
    region = (slice(max(0,y0-context), min(h,y1+context)),
              slice(max(0,x0-context), min(w,x1+context)))
    score = np.zeros(truth.shape, bool)
    score[y0:y1,x0:x1] = True
    # Padding makes the raster edge itself invalid context too.
    interior = distance_transform_edt(np.pad(valid, 1))[1:-1,1:-1] > 3
    score &= interior
    return (visible[region], (truth & valid)[region], valid[region], score[region],
            dict(window=list(window), excluded_components=int(len(banned)),
                 visible_pixels=int(visible.sum()), score_pixels=int(score.sum())))


def masked_components(pred, truth, score):
    """Charge TP/FN truth and FP predictions only within score, using full context."""
    p = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth, bool)
    score = np.asarray(score, bool)
    if p.ndim != 2 or not (p.shape == truth.shape == score.shape):
        raise ValueError('aligned 2D arrays required')
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('finite predictions in [0,1] required')
    contrib = np.zeros_like(p)
    for dy, dx, _, weight in _kernel_offsets():
        if weight:
            np.maximum(contrib, _shift(p, dy, dx) * weight, out=contrib)
    kernel = (np.maximum(1-distance_transform_edt(~truth)/3, 0)
              if truth.any() else np.zeros_like(p))
    n = int((truth & score).sum())
    tp = float(contrib[truth & score].sum())
    fp = float((p[score] * (1-kernel[score])).sum())
    return dict(TP_w=tp, FP_w=fp, FN_w=n-tp, n_truth=n,
                predicted_mass=float(p[score].sum()),
                dti=dtvi_closed_form(tp, fp, n) if n else None)


def match_mass(field, reference, score):
    """Downscale only: match candidate/control to their smaller mass, not labels.

    Returns both arrays, keeping their complete metric context scaled together.
    """
    a, b = float(field[score].sum(dtype=np.float64)), float(reference[score].sum(dtype=np.float64))
    target = min(a, b)
    return (field * (target/a if a else 0), reference * (target/b if b else 0))


def policies(visible, valid, seed):
    if not visible.any():
        z = np.zeros(visible.shape, np.float32)
        return {name: z.copy() for name in ('strike30x3','isotropic15','random_tangent')}
    geometry = structural_geometry(visible)
    directional = prior(visible, geometry, 30, 3)
    isotropic = (.6 * np.maximum(1-geometry[0]/15,0)).astype('float32')
    isotropic[visible] = .95
    randomized = prior(visible, structural_geometry(visible, random_seed=seed), 30, 3)
    result = dict(strike30x3=directional, isotropic15=isotropic, random_tangent=randomized)
    for p in result.values():
        p[~valid] = 0
    return result


def main():
    with rasterio.open(LABELS_TIF) as src, rasterio.open(TEMPLATE_TIF) as template:
        assert_same_grid(src, template)
        truth = src.read(1, masked=True).filled(0) > 0
        valid = np.isfinite(template.read(1))
    rows, folds = [], []
    for fold, window in enumerate(fold_windows(truth.shape)):
        visible, hidden, footprint, score, meta = split_fold(truth, valid, window)
        folds.append(dict(fold=fold, **meta))
        ps = policies(visible, footprint, seed=7100+fold)
        # Repeat null seeds to show orientation variability, not a significance test.
        for null_name, seed in (("random_tangent_2",8100+fold), ("random_tangent_3",9100+fold)):
            ps[null_name] = (prior(visible, structural_geometry(visible, random_seed=seed),30,3)
                                              if visible.any() else np.zeros_like(hidden,dtype=np.float32))
            ps[null_name][~footprint] = 0
        for control in ['isotropic15','random_tangent', 'random_tangent_2', 'random_tangent_3']:
            a,b = match_mass(ps['strike30x3'], ps[control], score)
            ps['strike_matched_to_'+control] = a
            ps[control+'_matched'] = b
        for name, p in ps.items():
            row = dict(fold=fold, policy=name, **masked_components(p, hidden, score))
            rows.append(row)
            print(json.dumps(row), flush=True)
    aggregates = {}
    for name in ps:
        rr = [r for r in rows if r['policy']==name and r['n_truth']]
        tp, fp, n = [sum(r[k] for r in rr) for k in ('TP_w','FP_w','n_truth')]
        aggregates[name] = dict(pooled_dti=dtvi_closed_form(tp,fp,n) if n else None,
                                mean_fold_dti=float(np.mean([r['dti'] for r in rr])) if rr else None,
                                scored_folds=len(rr), predicted_mass=sum(r['predicted_mass'] for r in rr))
    report = dict(generated_utc=datetime.now(timezone.utc).isoformat(),
                  protocol='geographic-stress-v1', buffer_pixels=10, context_pixels=45,
                  null_seeds=[7100,8100,9100], folds=folds, rows=rows, aggregates=aggregates,
                  labels_sha256=hashlib.sha256(LABELS_TIF.read_bytes()).hexdigest(),
                  caveats=['Diagnostic only: no selection or submission promotion.',
                           'Connected raster traces are not geological fault-system identifiers.',
                           'Quadrants are not organizer public/private blocks; missing faults count as negatives.',
                           'A near-catalogue prior cannot discover isolated interior faults.',
                           'Mass matching uses prediction sums only, never truth labels.'])
    dest = REPO_ROOT/'knowledge/session3/spatial_experiment.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')

if __name__ == '__main__':
    main()
