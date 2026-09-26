# Current status — session 4 (2026-09-26)

- Data placement re-run autonomously: 3/3 rasters PASS (Dropbox TLS failed; team git bridge OK).
- Score forensics: vendored 8 group files with provenance (`external/scored/`); exact
  random-emission baseline for the metric, verified by Monte-Carlo (`scripts/random_baseline.py`).
  Best group file ~1.9x random coverage; leader needs ~4-5x; blob-like uploads scored below random.
- Region-wide 1 m lidar on GitHub Actions: 706/716 official USGS 3DEP tiles (~167 GB) →
  12-channel uint8 product on the official grid (`external/dem/`, runs 36265492931 → v2
  36266555805). Fixed tile-seam artefact, curvature elevation bias (LoG kernel-sum
  error), fan-induced strike bias; regression tests added.
- Pre-registered 5-fold geographic test: lidar-only ridge skill x2.33/x1.81/x1.47
  (f=0.5/1/2%) vs 19 bands x1.14/x0.99/x0.87 on held-out catalogue faults. Promotion
  rule met; lidar arm chosen over the pre-written "both" arm (deviation recorded).
- New candidate `downloads/gems7-lidarscarp-ridge-top2pct-dfa04fa218b8.tif` (strict gate
  PASS). Local calibration predicts ~0.09 under a 50% transfer discount — it is a
  decisive H1 leaderboard test, not a promised gain. Nothing uploaded by the agent.
- Irregularities flagged: SDCF9 0.1563 from an unrecorded file; five accounts vs the
  per-entity submission limit; GEMSDOE2 file-score pairing unverified.
- Next: `knowledge/session4/next_session.md` (decision tree keyed on the upload score).

---

# Current status — session 3 (2026-09-26)

- Restored all three external rasters via pinned team bridge; prepare_data completed.
- Implemented/executed buffered geographic + whole connected-trace exclusion,
  three random-tangent seeds/fold, equal-mass controls, context-correct masked metric.
- H3 pooled diagnostic DTI 0.000125: no independent-discovery promotion.
- Trained/evaluated raw terrain (0.063839 pooled) and other geophysical (0.056197)
  experts on the same four diagnostic folds. No global normalization, no distance
  to catalogue, no held-out-label negative mining. No leaderboard prediction claim.
- Existing H3 rebuilt byte-identically; both TIFFs passed strict template validation.
  Found/fixed repeat packaging changing ZIP timestamps/manifests; immutable bundles
  now remain unchanged, mismatches fail closed.
- Re-read official problem, leaderboard, science abstracts/report and starts of five
  group sites. GDR 1591 retrieval now succeeds; source registry and site corrected.
- Tests and three-pass evidence: knowledge/session3/review.md. Browser install was
  blocked locally by TLS; runner results are the authority, not assumed success.
- No actual competition submission, no score above 0.3049, no discovered vent/fault.
- Next: knowledge/session3/next_session.md. Historical session notes below are retained.

---

# Current status — session 2 (2026-09-26)

Read README.md, AGENTS.md and knowledge/session2/review.md at every new session.

## Delivered and verified

- Data placement + preparation completed, CPU GBT retrained, full inference reproduced
  the control TIFF **byte-for-byte** (SHA-256 `90fb7dc0fc1f…`). Random-pixel AUC 0.9173
  is only a monitor. Correct imputation count is 58,171 band-pixels.
- New H3 tangent-continuation experimental TIFF (`2b06d45c5b57…`) with immutable unique
  name, Note, ZIP and strict local format gate. Locked component proxy 0.02825 vs
  0.02516 broad halo; not leaderboard validation or proof of geographic generalization.
- Native 1m USGS DEM pilot on runner: 4,194,304 valid native pixels, 3,873,024 safe after
  buffer, EPSG:26911. Not integrated into the submission; reproject before future use.
- Fixed exact [0,1] gate, bad shape crash, Inf-outside bug, custom metric radius, partial
  downloader files, relative data path, old holdout sampling leakage and live pagination.
- Research/source ledger, corrected rules (3/week/entity), evidence-generated seven-page
  site and daily public-release feed. Official refresh confirmed **106** ranked entries
  over three pages; all five source excerpts present. Browser suite passed at 1440/390px.
- **67 tests pass**; reproducible dependency versions in requirements-repro.txt.
- PR #3: https://github.com/buffedlizard55-lab/7GEMSDOE/pull/3 . Final merge/deployment
  state is recorded on GitHub, not predeclared here. No competition submission made.

## Still outstanding

No result above 0.3049. No verified new vents/faults. Buffered geographic validation,
region-wide calibrated DEM expert, independent geophysical features, positive-unlabeled
learning, U-Net integration, actual upload score attribution and eligibility/account
review remain. See knowledge/session2/next_session.md and requirements_matrix.md.

The first-session log below is historical and contains corrected assumptions (50 ranks,
3,073 imputed pixels, GPU readiness and provenance). Session-2 evidence supersedes it.

---

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
