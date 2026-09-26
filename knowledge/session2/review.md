# Three-pass review and irregularity register

## Pass 1 — implementation and direct checks

- Read repo, previous-session notes, all five supplied sites, official problem/About,
  leaderboard, rules PDF §3.3–3.6 and scientific sources.
- Downloaded three rasters through inherited git bridge after Dropbox TLS failure.
  Hashes/grid/counts re-measured: `data_verification.txt`.
- Added working `prepare_data.py`; executed CPU extraction and launched CPU training.
- Implemented H3 with held-component experiment and separate immutable candidate.
- Added H4 native-1m pilot, official-source monitor, daily workflow and feed UI.
- Rebuilt site with download-first executive summary and short unique Notes.

## Pass 2 — bugs and incorrect assumptions

- Strict [0,1] gate now rejects tiny negative/positive overflow, infinities outside,
  internal masks and missing nodata. Wrong shapes and corrupt files return errors.
- Metric's optional radius previously changed FP but not TP; both now use same radius.
- Downloader no longer preserves failed partial downloads with `cp -n`; bounded HTTP
  timeout and temporary bridge cleanup added.
- Old documentation's 3,073 imputed band-pixels contradicted actual re-run: **58,171**.
  The 27-channel feature extraction is transductively normalized; pixel AUC is not
  spatially independent. Need training-only normalization for rigorous next protocol.
- Prior pipeline did not implement GPU/U-Net training. Removed claim that data was its
  only blocker. Organizer reference supports CPU too; a GPU is a speed/resource need,
  not a universal logical requirement.
- Team-wide weekly budget is three, not five accounts × three. Official rules §3.4
  expressly forbid separate final submissions by team members. Account status flagged;
  no account actions or competition uploads were performed.
- Scores of 0.0286 and 0.0343 not attributable to a named public account. Public best
  rows cannot establish which uploaded bytes received any individual score.
- The past rejection's exact cause is unknown without the rejected file; eliminated
  unsupported claim that that error always means NaN inside the footprint.
- GitHub Pages configuration update returned HTTP 403. Existing root/main legacy
  Pages stays in place. Daily feed uses a public GitHub release + browser fetch; it
  requires no automatic Git commits or forbidden branch changes.

- Legacy proxy training leaked held truth into negative sampling and included held-block
  negatives. Sampling now excludes held geography plus a 300 m buffer and computes
  distance only to visible training faults. A regression test proves changing hidden
  labels cannot alter training samples. Old proxy scores are historical and require
  re-running before reuse. Full-footprint normalization remains transductive.

## Pass 3 — final verification

Final execution evidence follows below; statuses are recorded after execution, not predicted in advance. All remaining untested scientific
strategies remain hypotheses. No score >0.3049, platform acceptance, field discovery,
or exhaustive “no hallucinations” certification is claimed.

### Final execution evidence so far

- CPU extraction/training/inference completed in this sandbox. Fresh GBT AUC 0.9172875
  is a random-pixel monitor only. Rebuilt control SHA-256 exactly matches the existing
  published control (`90fb7dc0fc1f…`); see `rebuilt_control_meta.json` and `train_report.json`.
- GitHub runner [36261339061](https://github.com/buffedlizard55-lab/7GEMSDOE/actions/runs/36261339061)
  passed desktop 1440 px/mobile 390 px browser checks for all seven pages, no viewport
  overflow, clipboard Note, real TIFF byte hash and intentional mismatch blocking.
  Live-release response was mocked; it does not establish real release availability.
- Same runner completed the native **1 m** DEM pilot: 4,194,304 valid crop pixels,
  3,873,024 after a 40 m safety buffer. Source CRS is **EPSG:26911 (NAD83)**, not the
  competition's EPSG:32611 (WGS84); reproject before any integration. This pilot is NOT
  in either submission. Earlier central crop was entirely nodata; overview-based
  valid-interior selection fixed it. Full-grid extrapolation is not justified.
- Direct downloads in this sandbox serve HTTP 200 and hash-match both manifests.
- Local browser installation and Actions artifact-download endpoints were egress-blocked;
  runner evidence was recovered via its PR comment, not fabricated from job status.
- Source monitor on runner found all five cited excerpts. Leaderboard requests returned
  no HTML table; parser adjustment is in progress and last-good snapshots remain flagged.

### Pass 3 completed — 2026-09-26

- Live leaderboard verification succeeded on runner
  [36261708965](https://github.com/buffedlizard55-lab/7GEMSDOE/actions/runs/36261708965):
  **106 ranks, three explicitly linked official HTMX pages**, five source excerpts
  found, native DEM pilot complete and desktop/mobile browser checks PASS. The
  per-page URLs and response hashes are in `knowledge/feed.json`.
- Corrected the initial 50-participant assumption: it was pagination, not a full list.
  Leader remains 0.3049. At 18:12 UTC SDCF9's current account best is 0.1563;
  its earlier reported 0.1152 file result stays historical/unattributed to the new best.
- No current public-best row at 0.0343 or 0.0286 was found in this snapshot. This does
  NOT invalidate earlier individual submissions: account bests can improve and the
  accounts were not supplied. Keep both records group-reported.
- **67 local tests pass** (`tests.txt`), covering formula, custom radii, raster corruption,
  wrong grid/shape/dtype, exact bounds, NaN/Inf/masks, ZIP member bytes, page links,
  held-label isolation, nodata-safe DEM features, feed failure preservation and pagination.
- Python compilation, JavaScript syntax check, shell syntax check and served-file
  HTTP/hash checks pass. Library-level Affine deprecation warnings remain; no test errors.
- H3 publication now additionally refuses changed label hashes or mismatched label grids.
- Public score >0.3049, validated new fault/vent discoveries, region-wide DEM inference,
  GPU modelling, competition upload and authenticated sponsor-byte provenance are **not
  achieved**. The requirement matrix records these explicitly rather than certifying
  full scientific completion.
- PR: https://github.com/buffedlizard55-lab/7GEMSDOE/pull/3 . Merge is performed only
  after checks; GitHub's PR/Actions records carry the final merge/deployment status.
