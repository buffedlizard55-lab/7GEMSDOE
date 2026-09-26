# Three-pass review — session 3, 2026-09-26

## Pass 1 — implement and measure

- Read README, AGENTS, STATUS, session2/review and next_session before modelling.
- Restored all three large rasters using the existing downloader's team git bridge;
  Dropbox TLS retrieval failed. Reverified inherited SHA-256 pins, grid and counts.
  Ran prepare_data: 27-channel cache created outside Git. Evidence:
  `data_preparation.txt`, `data_verification.txt`. This is mirror consistency,
  not independently authenticated sponsor provenance.
- Implemented four diagnostic quadrants with 1 km exclusion, whole crossing
  8-connected-trace purge, context-correct masked DTI, matched-mass isotropic
  and random-tangent controls (three seeds per fold).
- Executed structural test. Pooled H3 DTI 0.0001245984203151753. This fails to
  establish independent geographic discovery; did not promote a new TIFF.
- Trained separate terrain and other-geophysical histogram gradient boosters on
  raw supplied bands. Fixed hyperparameters, same folds/samples, no test-fitted
  normalization. Terrain pooled DTI 0.06383859378245367, geophysical
  0.05619740924759742. Four folds, all terrain wins; no private score inference.
- Rebuilt existing H3 TIFF with original hash and validated both published TIFFs
  against the restored template. Unique file names and Notes remain at site top;
  dedicated how-to-submit executive guide retained.
- Re-read official problem/metric/submission requirements, first leaderboard
  page, relevant OSTI/USGS/GDR text and beginnings of all five team sites.
  Source status and science/hypothesis distinctions recorded in research.md.

## Pass 2 — bugs, wrong assumptions and edges

- Found that 'immutable' package regeneration rewrote manifest timestamps and ZIP
  container bytes. Fixed idempotence: existing complete bundles must agree with
  recomputed metadata and contents; no timestamp changes; newly created ZIPs use
  fixed timestamps. Metadata mutation/corrupt ZIP tests now fail closed. Original
  published bytes preserved (including original ZIP timestamps).
- Fixed initial experiment aggregation using fold-specific null names: stable
  policy IDs now ensure every null is aggregated across all four folds. Tests
  assert four rows per policy and mass matching per pair/fold.
- Added grid/CRS/transform assertions and feature-band-count checks before training.
- Added tests for whole crossing-trace exclusion, geographic buffer, edge erosion,
  deterministic sampling/nulls, empty visible catalogue, empty/invalid predictions,
  score masks retaining external kernel context, metric agreement, and immutable
  package rebuilds. An explicit counterexample rejects arbitrary FP hardening.
- Corrections retained: connected raster components are not geological fault
  systems; these quadrants are diagnostics, not a pristine final test; 100 m
  terrain features are not native 1 m DEM features; sample-confidences are not
  calibrated probabilities. No new external model data was ingested.
- Corrected old GDR 1591 failure claim using a successful page-tool retrieval.
  Python HTTPS still failed; team_site_review.json records network failures,
  while research.md separately records successful page-tool observations.
- A conversational summary initially transcribed incorrect expert pooled values;
  corrected immediately against JSON. All new site score tables render from
  machine reports, not those mistaken numbers.

## Pass 3 — original-request and end-to-end recheck

- Re-ran both complete experiments after code review. Scientific rows reproduced;
  timestamps/runtime differ by execution. Evidence includes parameters, sampling,
  weighted TP/FP/FN, prediction mass, fold and input hashes.
- **83 tests passed locally**, including previous metric/format tests, publication
  links, strict finite [0,1], and new spatial/reproducibility checks. Rasterio emits
  49 upstream PendingDeprecationWarnings; no failing tests.
- Rebuilt site from machine reports. Download-first layout and short Notes remain;
  new evidence warns that H3 is not a validated discovery upgrade.
- Local Playwright package installed; Chromium download failed due TLS. Do not
  claim a local visual/browser pass. Existing GitHub research workflow executes
  desktop/mobile downloads, SHA checks, Notes and page checks on a runner.
- Mission/core values and original normalized brief retained in README; latest
  results, reproducible commands and future-session reading order updated.
- Large rasters/features stay outside Git. No private emails added to public UI,
  credentials requested, new accounts created or competition uploads made.
- PR/CI/merge/deployment outcomes must be read from GitHub after execution, not
  predeclared here. Merge is conditional on successful checks and permission.

## Requirements still not satisfied (not hidden by a green test suite)

1. Winning score/top prize: unproven. No score estimate or guarantee above 0.3049.
2. Region-wide native DEM discovery, survey-block validation, real geological
   system IDs, positive-unlabeled correction and independent locked evaluation:
   next-session work, not implemented by these two diagnostic baselines.
3. Fully autonomous upload/final selection: requires authorized DrivenData session
   and participant eligibility/actions. We do not bypass these restrictions.
4. Official-byte authentication and complete external license audit: incomplete.
   Inherited mirror hashes and a landing-page license are narrower evidence.
5. Exhaustive source verification/full geothermal resource list: not achieved.
   This is an auditable research base, not a complete inventory of vents/resources.
6. Automatic fresh feed: existing daily scheduled source/leaderboard workflow,
   with stale fallback. Scheduling/network failure remains possible; matching
   source excerpts does not scientifically verify a model or recover file scores.

See `next_session.md` for the ordered continuation plan. The highest-value next
work is native terrain evidence and acquisition-aware generalization, not another
untested union or wider halo.
