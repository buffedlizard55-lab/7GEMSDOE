"""What do the group's scored submissions say about the hidden truth?

Inputs: ``external/scored/manifest.json`` (vendored files + reported public
scores) and the competition labels/template. For each file we report layout
checks, emitted pixels, fill fraction by distance to the nearest known fault,
a dispersion index and the skill multiple over the exact random baseline.

Inference chain (model-based, stated so it can be challenged):
1. The near-uniform catalogue-gap file (37f9d5b855) is treated as zero-skill.
   Inverting DTI_random(f, rho) at its density gives the implied public truth
   density rho. If it had positive skill, the true rho is lower.
2. With rho fixed, each score maps to an effective per-truth-pixel coverage c;
   c / c_random(f) is the skill multiple at the file's own density.
3. Dispersion index = pixels within 2 px of any emitted pixel / emitted pixels.
   Thin lines ~5, random scatter ~>10, compact blobs ~<3. Blob-like emission
   covers line-like truth inefficiently.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

import paths
import random_baseline as RB

ROOT = Path(__file__).resolve().parents[1]
SCORED = ROOT / "external" / "scored"
BINS = [(-0.1, 0.1, "on"), (0.1, 1.01, "1"), (1.01, 2.01, "1-2"), (2.01, 3.01, "2-3"),
        (3.01, 5.01, "3-5"), (5.01, 10.01, "5-10"), (10.01, 20.01, "10-20"),
        (20.01, 50.01, "20-50"), (50.01, 1e9, ">50")]
ZERO_SKILL_REFERENCE = "gemsdoe3-pindrop-discovery-37f9d5b855.tif"


def analyse(out_path=ROOT / "knowledge" / "session4" / "scored_files_analysis.json"):
    import rasterio
    from scipy.ndimage import binary_dilation, distance_transform_edt
    man = json.loads((SCORED / "manifest.json").read_text())
    with rasterio.open(paths.LABELS_TIF) as s:
        known = s.read(1) == 1
    with rasterio.open(paths.TEMPLATE_TIF) as s:
        foot = np.isfinite(s.read(1))
    dist = distance_transform_edt(~known)
    scored_px = int((foot & ~known).sum())  # known pixels are masked by the scorer
    bg = {n: int((foot & (dist > lo) & (dist <= hi)).sum()) for lo, hi, n in BINS}
    rows = []
    for e in man["files"]:
        p = SCORED / e["file"]
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        with rasterio.open(p) as s:
            a = s.read(1).astype(np.float64)
            dtype = s.dtypes[0]
        fin = np.isfinite(a)
        pf = np.where(fin, a, 0.0)
        emitted = foot & (pf > 0) & ~known
        n_emit = int(emitted.sum())
        halo = binary_dilation(emitted, iterations=2) & foot
        rows.append(dict(
            file=e["file"], sha256=sha, sha_matches_manifest=sha == e["sha256"],
            account=e["account"], public_score=e["public_score"], dtype=dtype,
            nan_exactly_outside=bool(np.array_equal(~fin, ~foot)),
            values_in_01=bool(np.nanmin(a) >= 0 and np.nanmax(a) <= 1),
            unique_inside=int(np.unique(pf[foot]).size),
            emitted_off_known=n_emit, density=n_emit / scored_px,
            mass_off_known=float(pf[foot & ~known].sum()),
            fill_by_distance_px={n: round(float(pf[foot & (dist > lo) & (dist <= hi)].sum()) / max(bg[n], 1), 4)
                                 for lo, hi, n in BINS},
            dispersion_index=round(float(halo.sum()) / max(n_emit, 1), 2),
        ))
    ref = next(r for r in rows if r["file"] == ZERO_SKILL_REFERENCE)
    rho = RB.rho_from_random_score(ref["public_score"], ref["density"])
    for r in rows:
        if r["public_score"] is None:
            continue
        c = RB.coverage_from_score(r["public_score"], r["density"], rho)
        cr = RB.coverage_random(r["density"])
        r.update(coverage_implied=round(c, 4), coverage_random=round(cr, 4), skill_multiple=round(c / cr, 3))
    leader = {str(f): round(RB.coverage_from_score(0.3049, f, rho) / RB.coverage_random(f), 2)
              for f in (0.005, 0.01, 0.02, 0.03)}
    report = dict(
        method=__doc__.strip().splitlines(), scored_pixels=scored_px, background_px_by_bin=bg,
        zero_skill_reference=ZERO_SKILL_REFERENCE, implied_truth_density=round(rho, 6),
        implied_truth_pixels_if_region_wide=int(rho * scored_px),
        leader_0_3049_required_skill_multiple_by_density=leader,
        random_dti_at_implied_density={str(f): round(RB.dti_random(f, rho), 4)
                                       for f in (0.005, 0.01, 0.02, 0.03, 0.05)},
        files=rows,
        caveats=["scores are group-reported/leaderboard observations; file-account pairing is a team record",
                 "public score uses public chunks only; densities here use the whole footprint",
                 "if the reference file had positive skill, rho is lower and every multiple rises"],
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    r = analyse()
    print("implied truth density", r["implied_truth_density"], "pixels", r["implied_truth_pixels_if_region_wide"])
    for f in r["files"]:
        print(f"{f['file']:44s} score={f['public_score']} dens={f['density']:.4f} disp={f['dispersion_index']:5.2f} "
              f"skill=x{f.get('skill_multiple', float('nan'))} layout_ok={f['nan_exactly_outside'] and f['values_in_01']}")
    print("leader needs", r["leader_0_3049_required_skill_multiple_by_density"])
