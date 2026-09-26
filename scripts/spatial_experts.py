"""CPU discovery baseline on raw supplied bands with independent geographic folds.

No full-footprint normalization, catalogue distance, or hidden-label mining.
Two fixed experts; no tuning/calibration on diagnostic folds. Probabilities are
case-control sample confidences, not calibrated geological probabilities.
"""
import hashlib
import json
import time
from datetime import datetime, timezone
import numpy as np
import rasterio
from scipy.ndimage import label
from sklearn.ensemble import HistGradientBoostingClassifier
from paths import FEATURES_TIF, LABELS_TIF, TEMPLATE_TIF, REPO_ROOT
from spatial_validation import fold_windows, split_fold, masked_components, assert_same_grid
from metric import dtvi_closed_form


def training_mask(truth, valid, window, buffer=10):
    """Exclude geography, buffer and ALL raster traces touching that exclusion."""
    y0,y1,x0,x1=window; h,w=truth.shape
    excluded=np.zeros(truth.shape,bool)
    excluded[max(0,y0-buffer):min(h,y1+buffer), max(0,x0-buffer):min(w,x1+buffer)]=True
    components,_=label(truth & valid,structure=np.ones((3,3)))
    banned=np.unique(components[excluded & truth & valid])
    return valid & ~excluded & ~np.isin(components,banned)


def sample_training(truth, allowed, seed, max_positive=20000):
    rng=np.random.default_rng(seed)
    positive=np.flatnonzero((truth & allowed).ravel())
    unlabeled=np.flatnonzero((~truth & allowed).ravel())
    if not len(positive) or not len(unlabeled):
        raise ValueError('training fold needs positives and unlabeled pixels')
    pos=rng.choice(positive,min(max_positive,len(positive)),replace=False)
    neg=rng.choice(unlabeled,min(3*len(pos),len(unlabeled)),replace=False)
    return np.concatenate([pos,neg]), np.concatenate([np.ones(len(pos)),np.zeros(len(neg))])


def main():
    start=time.monotonic()
    with rasterio.open(LABELS_TIF) as labels, rasterio.open(TEMPLATE_TIF) as template, rasterio.open(FEATURES_TIF) as s:
        assert_same_grid(labels, template)
        assert_same_grid(s, template)
        if s.count != 19:
            raise ValueError('expected exactly 19 source bands; audit channel mapping before use')
        truth=labels.read(1,masked=True).filled(0)>0
        valid=np.isfinite(template.read(1))
        bands=s.read(masked=True).filled(np.nan).astype(np.float32)
        names=list(s.descriptions)
    bands[~np.isfinite(bands)]=np.nan
    # Use exact source band positions; retain descriptions verbatim, not endorsed semantics.
    experts={'terrain_100m':[11,18], 'geophysical':[i for i in range(19) if i not in (11,18)]}
    rows=[]; samples=[]
    for fold,window in enumerate(fold_windows(truth.shape)):
        allowed=training_mask(truth,valid,window)
        indices,y=sample_training(truth,allowed,seed=7300+fold)
        samples.append(dict(fold=fold,n_positive=int(y.sum()),n_unlabeled=int((y==0).sum())))
        _, g, footprint, score, _=split_fold(truth,valid,window)
        y0,y1,x0,x1=window; h,w=truth.shape
        region=(slice(max(0,y0-45),min(h,y1+45)),slice(max(0,x0-45),min(w,x1+45)))
        for name,channels in experts.items():
            clf=HistGradientBoostingClassifier(max_iter=80,max_leaf_nodes=15,
                    min_samples_leaf=60,learning_rate=.08,l2_regularization=1.,
                    early_stopping=False,random_state=7300+fold)
            X=np.column_stack([bands[i].ravel()[indices] for i in channels])
            clf.fit(X,y)
            p=np.zeros(g.shape,dtype=np.float32)
            coords=np.flatnonzero(footprint.ravel())
            for offset in range(0,len(coords),100000):
                ix=coords[offset:offset+100000]
                xx=np.column_stack([bands[i][region].ravel()[ix] for i in channels])
                p.ravel()[ix]=clf.predict_proba(xx)[:,1]
            row=dict(fold=fold,policy=name,**masked_components(p,g,score))
            rows.append(row); print(json.dumps(row),flush=True)
    aggregates={}
    for name in experts:
        rr=[r for r in rows if r['policy']==name]
        tp,fp,n=[sum(r[k] for r in rr) for k in ('TP_w','FP_w','n_truth')]
        aggregates[name]=dict(pooled_dti=dtvi_closed_form(tp,fp,n),
                              mean_fold_dti=float(np.mean([r['dti'] for r in rr])),
                              predicted_mass=sum(r['predicted_mass'] for r in rr))
    report=dict(protocol='raw-experts-geographic-v1',generated_utc=datetime.now(timezone.utc).isoformat(),
                elapsed_seconds=time.monotonic()-start, buffer_pixels=10, context_pixels=45, seeds=[7300,7301,7302,7303], rows=rows,aggregates=aggregates,
                samples=samples,experts={k:[dict(band=i+1,description=names[i]) for i in v] for k,v in experts.items()},
                hyperparameters=clf.get_params(),
                features_sha256=hashlib.sha256(FEATURES_TIF.read_bytes()).hexdigest(),
                caveats=['Diagnostic cross-validation, not a locked final test or leaderboard estimate.',
                         'Unlabeled pixels treated as negatives; positive-unlabeled correction remains outstanding.',
                         'No scaling/imputation fitted on test geography; histogram bins and missing-value routing fit on training only.',
                         'Supplied 100 m terrain is NOT the native 1 m DEM pilot.',
                         'Source band descriptions are inherited metadata, not independently verified band semantics.',
                         'No expert ensemble or probability threshold selected using these folds. No submission promoted.'])
    (REPO_ROOT/'knowledge/session3/expert_experiment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')

if __name__=='__main__': main()
