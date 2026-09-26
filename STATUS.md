# STATUS log

## 2026-09-26 — session 1 of 7GEMSDOE (this repo)

Repo started from an empty initial commit; everything below built this session.

### Done
1. **Competition facts verified line-by-line** from the problem page, About page,
   leaderboard and the sha256-pinned rules PDF extraction → `knowledge/00`,
   `research.html`. Irregularities flagged (sample-submission == labels;
   GDR submission 1391 dead link; DEM PDF is a scan).
2. **Data placement without manual steps**: the three official rasters were pulled
   from the sibling repo's hash-pinned git bridge (Dropbox is egress-blocked in
   this sandbox), every part sha256-verified, feature stack reassembled
   (`4371c82e…` match) → `scripts/download_competition_data.sh`,
   `scripts/verify_data.py` (ALL CHECKS PASS). Grid: 3,292 × 3,730, EPSG:32611,
   100 m; labels 60,988 positive / 5,167,373 valid px.
3. **Official metric implemented and proven**: `scripts/metric.py` + 24 tests in
   `tests/test_metric.py` — brute-force cross-check, identities, and bit-level
   reproduction of all 15 deterministic rows of the inherited verified strategy
   table on the real competition fixture (blanket DTI 0.0956 etc.).
4. **Feature extraction**: 19 official bands + 6 Sobel edge channels + 2 local-σ
   channels, robust-normalised; footprint asserted equal to the official template
   (3,073 in-footprint band-holes imputed with band medians, counted).
5. **Blind-fault detector v1**: HistGradientBoosting on 304,940 pixels × 27
   features, deliberately NO distance-to-fault feature; holdout AUC 0.917;
   full-grid probability map cached.
6. **Pseudo-new-fault proxies** (the only locally-honest evaluation): block
   holdout (pessimistic; nothing recovers distant hidden faults) and component
   holdout (658 comps, 12,198 px hidden). Sweep result: DTI rises with halo width
   to r=15/h=0.6 (proxy 0.0249 vs catalogue-only 0.0090 vs blanket 0.0118).
   Contrarian, measured, documented.
7. **Submission v1 built and format-gated**: `halo15-0.6 + blind-gbt(τ=0.5,
   s=0.6)` → `downloads/submission.tif` (2.9 MB, sha256
   `90fb7dc0fc1f…`), PASS on every requirement including values-in-[0,1] and
   NaN-outside-footprint — the exact failure mode that rejected an earlier team
   download is gated out by tests.
8. **GitHub Pages site** (served from the repo root — the Pages source is
   legacy "/" on main and the token cannot change it): executive summary with
   one-click download, how-to-submit subpage, strategy/research/data/results/
   metric pages, all machine-measured.
9. **CI**: hermetic test workflow (no external data needed).

### Blocked / limitations
* No GPU in sandbox → deep-model training deferred to a runner.
* No DrivenData credentials → `1m_DEM_links.csv` not mirrored.
* Dropbox egress-blocked here → git-bridge fallback is the default route.

### Next (see README checklist)
H3 along-strike extrapolation · H4 1 m DEM scarp detection · H5 external priors ·
H7 GPU U-Net · submit v1 on one account with a control.
