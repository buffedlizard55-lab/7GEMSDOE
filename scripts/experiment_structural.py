"""Predeclared H3 ablation. Seeds 4242/4243 selection; 9001 locked test.

Whole connected components hidden. Component holdout is not spatially buffered
and is biased toward near-catalogue recovery. No leaderboard prediction.
"""
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import rasterio
from scipy.ndimage import label
from metric import dtvi_components, dtvi_closed_form
from paths import LABELS_TIF, TEMPLATE_TIF, REPO_ROOT
from structural_prior import structural_geometry, prior


def hide_components(truth, seed, fraction=.2):
    comps, count = label(truth, structure=np.ones((3, 3)))
    sizes = np.bincount(comps.ravel())
    chosen, total = [], 0
    for c in np.random.default_rng(seed).permutation(count) + 1:
        chosen.append(c)
        total += sizes[c]
        if total >= truth.sum() * fraction:
            break
    return np.isin(comps, chosen)


def main():
    with rasterio.open(LABELS_TIF) as src:
        truth = src.read(1, masked=True).filled(0) > 0
    with rasterio.open(TEMPLATE_TIF) as src:
        valid = np.isfinite(src.read(1))
    rows = []
    policies = [('isotropic3', 3, 3), ('isotropic15', 15, 15),
                ('strike15x3', 15, 3), ('strike30x3', 30, 3)]
    for seed in [4242, 4243, 9001]:
        hidden = hide_components(truth, seed)
        visible = truth & ~hidden
        geometry = structural_geometry(visible)
        for name, a, b in policies:
            # Isotropic control has no coherence filtering.
            if a == b:
                pred = (.6 * np.maximum(1 - geometry[0] / a, 0)).astype('float32')
                pred[visible] = .95
            else:
                pred = prior(visible, geometry, a, b)
            pred[~valid] = 0
            c = dtvi_components(pred, hidden)
            row = dict(seed=seed, split='locked_test' if seed == 9001 else 'selection',
                       policy=name, **c,
                       dti=dtvi_closed_form(c['TP_w'], c['FP_w'], c['n_truth']))
            rows.append(row)
            print(json.dumps(row), flush=True)
    means = {n: float(np.mean([r['dti'] for r in rows if r['policy'] == n and
                              r['split'] == 'selection'])) for n, _, _ in policies}
    winner = max(means, key=means.get)
    out = dict(generated_utc=datetime.now(timezone.utc).isoformat(),
               protocol='H3 connected-component ablation v1; seeds fixed before execution',
               selection_means=means, selected=winner, rows=rows,
               labels_sha256=hashlib.sha256(LABELS_TIF.read_bytes()).hexdigest(),
               caveat='Component holdout only; no buffered geographic test, no private labels. '
                      'All valid pixels charged as negatives except hidden truth. Known-fault scoring '
                      'mask on platform is not reproduced. Not sufficient to promote a submission.')
    dest = REPO_ROOT / 'knowledge/session2/structural_experiment.json'
    dest.write_text(json.dumps(out, indent=2) + '\n')

if __name__ == '__main__':
    main()
