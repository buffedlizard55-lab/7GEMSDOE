"""Build H3 only when the frozen selection report selects strike30x3.

This is an EXPERIMENTAL candidate, not a promoted leaderboard winner.
"""
import json
import numpy as np
import rasterio
from paths import ARTIFACT_DIR, LABELS_TIF, TEMPLATE_TIF, REPO_ROOT
from structural_prior import structural_geometry, prior
from package_submission import package


def main():
    report_path = REPO_ROOT / 'knowledge/session2/structural_experiment.json'
    report = json.loads(report_path.read_text())
    if report['selected'] != 'strike30x3':
        raise SystemExit('Frozen selection no longer selects strike30x3; review before publishing')
    with rasterio.open(LABELS_TIF) as src:
        visible = src.read(1, masked=True).filled(0) > 0
    with rasterio.open(TEMPLATE_TIF) as src:
        meta = src.profile.copy()
        valid = np.isfinite(src.read(1))
    pred = prior(visible, structural_geometry(visible), along_radius=30, cross_radius=3)
    pred[~valid] = np.nan
    meta.update(dtype='float32', count=1, nodata=np.nan, compress='deflate')
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    dest = ARTIFACT_DIR / 'strike30x3.tif'
    with rasterio.open(dest, 'w', **meta) as dst:
        dst.write(pred, 1)
    result = package(dest, TEMPLATE_TIF, 'strike30x3-v2',
                     'H3 tangent continuation 3km x 300m h0.6; no GBT; experimental',
                     evidence='knowledge/session2/structural_experiment.json')
    (REPO_ROOT / 'downloads/structural_meta.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
