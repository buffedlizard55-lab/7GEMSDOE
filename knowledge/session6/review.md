# Session 6 review — pipeline replay, live feed and source-ingestion safeguards

**Review date:** 2026-09-26 UTC. This is an evidence note, not a claim that the
competition score improved. The standing competition target is fault mapping,
not direct geothermal-vent classification ([official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).

## Pass 1 — implement and verify

### Current competition / team position

The automated public feed retrieved from the repository's `research-feed`
release is timestamped **2026-09-26 21:12:55 UTC**, contains **107 ranked
entries**, and records DARD at **0.3049**. It places the team's known public
bests at extradr19 **0.1563 (rank 24)**, SDCF9 **0.1563 (rank 25)**, smashi34
**0.1560 (rank 26)**, smrtdoog5 **0.1193 (rank 41)** and wbg1 **0.0830 (rank
50)**. See the saved, machine-readable snapshot `knowledge/feed.json` and the
[official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
A separate official-page retrieval later in this review still showed DARD at
0.3049 and SDCF9 at 0.1563; leaderboard scores are public bests and can change.

The current best known group public score is 0.1486 below the leader. The
SDCF9 leaderboard best is still not paired with a known file: the recorded
GEMSDOE3 dense control is 0.1152, so the file that earned 0.1563 remains an
unresolved irregularity. The file-to-score pairing for smashi34 is also not
fully authenticated. The private email addresses in the user's pasted results
are intentionally not copied into public project files.

The official problem page says new expert-labeled faults form the initial
private test truth and submissions are subsequently reviewed to expand the
fault labels for the final prize round. This validates the project's emphasis
on auditable, geologically interpretable candidate traces, but it does **not**
prove that interpretability alone increases a score or that any emitted trace
is a real fault.

### Data placement, training, and end-to-end reproduction

* `bash scripts/download_competition_data.sh` completed autonomously. Dropbox
  TLS failed; the script's public sibling-repository bridge succeeded. All
  three files passed inherited SHA-256 pins. These pins establish byte
  consistency with inherited team evidence, **not independent sponsor
  provenance**.
* `scripts/verify_data.py` passed: 3,292 x 3,730, EPSG:32611, 100 m; 19
  feature bands; 5,167,373 valid pixels; 60,988 positive known-fault pixels.
  `scripts/prepare_data.py` completed and reported 58,171 imputed band-pixels.
* CPU retraining (`scripts/train_model.py`, seed 20260926) completed in 71 s:
  304,940 sampled rows, 27 features, random-pixel holdout AUC 0.9172875 and
  Brier 0.0976630. This holdout is **not spatially independent** and is only a
  training-pipeline diagnostic; it is not a leaderboard estimate.
* `scripts/build_submission.py --no-publish` rebuilt the legacy control and
  passed its strict format gate. Its SHA-256
  `90fb7dc0fc1f6e7d3dbb20927417c6af7d110ca41167329d792c75c145f75b6a` exactly
  matched the preserved published control byte-for-byte. The replay did not
  overwrite or publish a download.
* The recommended H1 candidate (`gems7-lidarscarp-ridge-top2pct-36c3a3f341c8`)
  remains **unscored**. No file was uploaded, no new candidate was packaged,
  and no result above 0.3049 is claimed.

Machine evidence and full hashes: [`local_verification.json`](local_verification.json).

### Up-to-date feed and irregularities

* The scheduled research refresh succeeded on GitHub Actions and published a
  timestamped feed. Its latest run in this review found 107 ranks and flagged
  the official GDR 1391 source excerpt as `REVIEW_excerpt_missing`; the stale
  bundled snapshot was refreshed from the validated release-body JSON. The
  direct release-asset URL failed with EOF, so the API body was used instead.
* The direct DrivenData data tab currently resolves to login; no credentials
  were accessed. The project still does not hold an authenticated competition
  session or the official DEM-link CSV.
* Explicit `workflow_dispatch` attempts for both QFFDB and radiometric jobs
  returned HTTP 403 `Resource not accessible by integration`. No external
  product is claimed to have been downloaded by those jobs. The official source
  record for INGENIOUS GDR 1391 also remains an excerpt-review flag, not a
  verified correction.
* The current results and sources feed is machine-checked, not a substitute for
  checking scientific meaning, licenses, or file-to-score provenance.

### Hardening implemented this pass

* QFFDB ZIP ingestion now rejects absolute/traversal paths and symbolic links
  before extraction. It also refuses to rasterize a layer with a missing or
  unparseable CRS instead of silently assuming coordinates are EPSG:32611.
* GeoDAWN radiometric ingestion now fails closed when a preferred channel has
  multiple matching files, preventing results from depending on API listing
  order. Quantisation excludes NaN and infinite cells before calculating
  percentile bounds; temporary download filenames are reduced to safe
  basenames.
* New hermetic tests cover these input irregularities. See
  `scripts/qfaults_prior.py`, `scripts/geodawn_rad.py`,
  `tests/test_qfaults.py` and `tests/test_geodawn_rad.py`.

## Pass 2 — bug, assumption and edge-case review

* ZIP traversal is checked for both POSIX and Windows separators/absolute
  paths; extraction accepts ordinary nested files and rejects symlinks. No
  archive member is extracted before the full member list passes validation.
* CRS handling uses parsed CRS objects, not the previous substring test for
  `"32611"`; missing CRS now stops the job. Geometry reprojecting remains
  runner-only and still must be checked against the observed QFFDB layer schema.
* Radiometric selection reports ambiguity rather than silently selecting the
  first listing result. A listing with one unambiguous match per channel is
  still required before a data product can be built. Finite-value tests verify
  NaN/Inf never leak into byte quantisation.
* A label-derived random-pixel AUC is explicitly not treated as spatial
  discovery skill. The experimental H1 candidate remains the only decisive
  leaderboard test under the prior decision tree; a second upload would confound
  it and spend feedback budget without new evidence.
* The feed's GDR 1391 excerpt status is left flagged rather than manually
  rewritten as verified. No private credentials or email addresses were added.
* The complete hermetic suite passes (**124 passed**, 50 non-failing Rasterio
  pending-deprecation warnings); a second static audit found zero broken relative
  links across the seven generated site pages.

## Pass 3 — full-request check / outcome

* The repo's mission, sources, previous group results, official leaderboard,
  downloadable submission and submission-format guide remain in place. This
  review updated the bundled leaderboard snapshot and records the reproducible
  local train-to-control replay.
* Submission rejection guard remains exact: a single-band float32 GeoTIFF on
  the template grid, finite predictions in [0,1] inside the footprint, and
  NaN outside, as enforced by `scripts/validate_submission.py`.
* The H1 file is ready for an authorized participant to submit with the Note
  recorded in `downloads/lidar_meta.json`; this agent did not and cannot submit
  through the absent DrivenData login. No leaderboard gain is asserted.
* The code improvements are source-ingestion safety/ambiguity safeguards only;
  they do not change a prediction policy and have no claimed score effect.

## Evidence-linked source links for manual review

* [Official competition overview / rules entry](https://www.drivendata.org/competitions/306/competition-doe-gems/)
* [Official problem description and prize structure](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
* [Official About page (GeoDAWN context and fault definitions)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
* [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
* [Competition data tab (sign-in required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
* [DOE/USGS competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
* [USGS GeoDAWN ScienceBase release](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)
* [USGS GeoDAWN data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
* [USGS QFFDB download referenced by the H2 runner](https://earthquake.usgs.gov/static/lfs/nshm/qfaults/Qfaults_GIS.zip)
* [GDR INGENIOUS source record — current excerpt check needs review](https://gdr.openei.org/submissions/1391)

## Session 6 follow-up — runner products and H9 first screen (2026-09-26)

### Pass 1 — implement and verify

* Direct `workflow_dispatch` attempts had returned HTTP 403, so runner jobs were
  triggered by marker-prefixed pushes. QFFDB builds 36275308744 and 36275556486
  succeeded; GeoDAWN builds 36275561534 and 36275797099 succeeded. Push CI
  36275797108 and research refresh 36275797096 passed. Earlier failures are
  preserved below as history, not silently rewritten.
* QFFDB observed layer `Qfaults_US_Database.shp`, EPSG:4326, 112,809 features,
  fields `scale` and `certainty`. The scale values include exact denominators,
  `unspecified`, and one mixed-scale category; certainty values include Good,
  Poor, Unknown and “Mapped using Lidar.” These are recorded in
  `external/qfaults/observed_schema.json`. The three-band prior has 138,416
  coarse, 30,877 fine and 670 lower-certainty pixels; product SHA-256
  `538b45735833b341fc455dbbf06c47bc82a8bd8943c254ae6d3a5a07e72e22ca`.
  Raw ZIPs are downloaded to a temporary directory, not retained in Git.
* GeoDAWN ScienceBase Area 1/2 TIFF packages passed official listed-size and
  MD5 checks, with SHA-256 values in `external/geodawn_rad/geodawn_rad.json`.
  The archives list 13 TIFFs per area; K/Th/U/TC members were selected by
  observed names. The output is a 4-band uint8 raster, exact competition grid,
  5,166,085 nonzero pixels/channel and product SHA-256
  `c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682`.
  Source grids observed from the TIFFs are EPSG:32611 at 100 m (Area 2) and
  50 m (Area 1). Area 1 intentionally overrides Area 2 in overlap.
* **H9 raw-channel diagnostic:** `scripts/radiometric_experiment.py` uses the
  H4 5×5 geographic fold assignment, 10-pixel buffer, common support (3,891,322
  pixels, 48,376 catalogue positives), matched 40k positive/120k negative
  samples, same LightGBM 4.6.0 learner and random-coverage baseline. At 1%,
  rad skill was 0.657 vs bands19 0.635; at 2%, 0.597 vs 0.592. Rad beat
  bands19 in 4/5 folds at 1%, but 3/5 at 2%; the preregistered requirement
  (pooled improvement and ≥4/5 folds at both 1% and 2%) **failed**. Report:
  `knowledge/session6/geodawn_experiment.json`.

### Pass 2 — assumption and edge-case audit

* This is a raw-channel screen, not the planned radiometric-gradient/lineament
  arm. The small pooled difference is not sufficient to promote H9. The global
  robust percentile encoding is transductive; acquisition-block holdouts are
  not isolated by the current 5×5 geographic split. Do not describe it as
  independent validation of hidden truth or as a leaderboard estimate.
* QFFDB is an existing fault catalogue. Its rasterized traces can encode known
  labels or nearby geology and thus risk catalogue leakage; the resulting
  product is for sensitivity/catalogue-gap analysis only until spatial and
  source-independence checks are designed. `lower_certainty_trace` deliberately
  avoids calling `Poor`/`Unknown` features literally inferred.
* GeoDAWN channels are surface radiometric responses affected by lithology,
  alteration, moisture, vegetation, altitude and acquisition geometry—not fault
  detections. The USGS release describes Area 2 as geothermal-resource-focused,
  but neither product proves geothermal-resource occurrence or a new fault.
* GeoDAWN’s source listing includes other products (magnetics, profiles, maps,
  flight paths and reports); this build uses only radiometric TIFFs. Per-asset
  redistribution terms, radio-altitude masks and all Area 2 acquisition-block
  polygons remain to be independently checked.
* Raster QA compared both compact products to the locally restored official
  template: dimensions, CRS and affine transform match exactly. GeoDAWN has
  zeros outside the template and 1,288 missing-in-footprint cells per channel;
  valid channel values are 1–255. QFFDB bands are binary {0,1}. These are
  feature/prior products, not competition submission rasters.

### Pass 3 — original request and merge/readiness check

* The requested valid downloadable submission remains the H1 lidar TIFF at the
  top of the site with exact Note and guide. H1 is still unscored, so no second
  submission file is recommended or generated. The new external products are
  explicitly not submission candidates.
* At the branch review checkpoint, the bundled leaderboard snapshot had 107
  entries (21:12:55 UTC). After PR #7 merged, the main-only research refresh
  succeeded (run 36277703129) and updated the public release and bundled feed to
  109 entries at 22:53:29 UTC. DARD remains 0.3049; best group result remains
  0.1563. GDR 1391 remains `REVIEW_excerpt_missing`; this is a source-review flag,
  not a verified source correction.
* No new fault or geothermal vent has been field-verified. No score gain is
  claimed. Review and merge only after the newest branch commits and required
  checks are actually complete; `action_required` PR checks must not be mistaken
  for passing checks.

## Official-source additions for manual review

* [GeoDAWN ScienceBase item / DOI 10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)
* [GeoDAWN official USGS data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
* [GeoDAWN official ReadMe PDF (projection, grid origins/intervals, channel definitions)](https://www.sciencebase.gov/catalog/file/get/657e1d85d34e23d3533209f7?name=GeoDAWN_ReadMe.pdf)
* [USGS Qfaults GIS download](https://earthquake.usgs.gov/static/lfs/nshm/qfaults/Qfaults_GIS.zip)
* [USGS Qfaults current National Database layer schema and symbology](https://earthquake.usgs.gov/arcgis/rest/services/haz/Qfaults/MapServer/21?f=pjson)
* [USGS report example defining location reliability and compiled map scale](https://earthquake.usgs.gov/static/lfs/nshm/qfaults/Reports/1191.pdf)
