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

Final test counts, runner results, browser checks, PR and deployment status will be
appended after execution, not predicted in advance. All remaining untested scientific
strategies remain hypotheses. No score >0.3049, platform acceptance, field discovery,
or exhaustive “no hallucinations” certification is claimed.
